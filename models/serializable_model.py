##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2019 Université catholique de Louvain (http://www.uclouvain.be)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
import datetime
import json
import logging
import time
import uuid

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import DateTimeField, DateField
from django.utils.encoding import force_str
from pika.exceptions import ChannelClosed, ConnectionClosed

from osis_common.models import message_queue_cache, osis_model_admin
from osis_common.models.exception import MigrationPersistanceError
from osis_common.models.message_queue_cache import MessageQueueCache
from osis_common.queue import queue_sender

LOGGER = logging.getLogger(settings.DEFAULT_LOGGER)


class SerializableQuerySet(models.QuerySet):
    # Called in case of bulk delete
    # Override this function is important to force to call the delete() function of a model's instance
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()


class SerializableModelManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)

    def get_queryset(self):
        return SerializableQuerySet(self.model, using=self._db)


class SerializableModelAdmin(osis_model_admin.OsisModelAdmin):
    actions = ['resend_messages_to_queue']

    def resend_messages_to_queue(self, request, queryset):
        serializable_model_resend_messages_to_queue(self, request, queryset)


def serializable_model_resend_messages_to_queue(self, request, queryset):
    if hasattr(settings, 'QUEUES') and settings.QUEUES:
        counter = 0
        queue_name = settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_PRODUCE')
        for record in queryset:
            try:
                ser_obj = serialize(record, False)
                queue_sender.send_message(queue_name,
                                          wrap_serialization(ser_obj))
                counter += 1
            except (ChannelClosed, ConnectionClosed):
                self.message_user(request,
                                  'Message %s not sent to %s.' % (record.pk, queue_name),
                                  level=messages.ERROR)
        self.message_user(request, "{} message(s) sent.".format(counter), level=messages.SUCCESS)
    else:
        self.message_user(request,
                          'No messages sent. No queues defined',
                          level=messages.ERROR)


class SerializableModel(models.Model):
    objects = SerializableModelManager()

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    def save(self, *args, **kwargs):
        super(SerializableModel, self).save(*args, **kwargs)
        # Send message to queue only when transaction is commited
        transaction.on_commit(lambda: serializable_model_post_save(self))

    def delete(self, *args, **kwargs):
        result = super(SerializableModel, self).delete(*args, **kwargs)
        # Send message to queue only when transaction is commited
        transaction.on_commit(lambda: serializable_model_post_delete(self, to_delete=True))
        return result

    def natural_key(self):
        return [self.uuid]

    def __str__(self):
        return "{}".format(self.uuid)

    class Meta:
        abstract = True

    @classmethod
    def find_by_uuid(cls, uuid):
        try:
            return cls.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            return None


def serializable_model_post_save(instance):
    # This function is called in the save() method of SerializableModel and AuditableSerializableModel
    # Any change made here will be applied to all models inheriting SerializableModel or AuditableSerializableModel
    serializable_model_post_change(instance)


def serializable_model_post_delete(instance, to_delete=False):
    # This function is called in the delete() method of SerializableModel and AuditableSerializableModel
    # Any change made here will be applied to all models inheriting SerializableModel or AuditableSerializableModel
    serializable_model_post_change(instance, to_delete)


def serializable_model_post_change(instance, to_delete=False):
    # This function is called in the save() and delete() methods of SerializableModel and AuditableSerializableModel
    # Any change made here will be applied to all models inheriting SerializableModel or AuditableSerializableModel
    if hasattr(settings, 'QUEUES') and settings.QUEUES:
        send_to_queue(instance, to_delete)


def send_to_queue(instance, to_delete=False):
    queue_name = settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_PRODUCE')
    serialized_instance = wrap_serialization(serialize(instance, to_delete), to_delete)

    try:
        # Try to resend message present in cache
        message_queue_cache.retry_all_cached_messages()
        # Send current message
        queue_sender.send_message(queue_name, serialized_instance)
    except (ChannelClosed, ConnectionClosed):
        # Save current message queue cache database for retry later
        MessageQueueCache.objects.create(queue=queue_name, data=serialized_instance)
        LOGGER.exception('QueueServer is not installed or not launched')


# TODO :: If record is to delete, we don't need to send the entire object, only the UUID is necessary to send.
# TODO :: This need to correct the algorithm to consume messages.
def serialize(obj, to_delete, last_syncs=None):
    if obj:
        fields = {}
        for f in obj.__class__._meta.fields:
            if f.is_relation and to_delete:
                # If record is to delete, it's not necessary to find trough fk field values
                # (cf. todo above to clean this code)
                attribute = None
            else:
                attribute = getattr(obj, f.name)
            if f.is_relation and not to_delete:
                try:
                    if attribute and getattr(attribute, 'uuid'):
                        fields[f.name] = serialize(attribute, to_delete, last_syncs=last_syncs)
                except AttributeError:
                    pass
            else:
                try:
                    json.dumps(attribute)
                    fields[f.name] = attribute
                except TypeError:
                    if isinstance(f, (DateTimeField, DateField)):
                        dt = attribute
                        fields[f.name] = _convert_datetime_to_long(dt)
                    else:
                        fields[f.name] = force_str(attribute)
        class_label = obj.__class__._meta.label
        last_sync = None
        if last_syncs:
            last_sync = _convert_datetime_to_long(last_syncs.get(class_label))
        return {"model": class_label, "fields": fields, 'last_sync': last_sync}
    else:
        return None


def wrap_serialization(body, to_delete=False):
    wrapped_body = {"body": body}

    if to_delete:
        wrapped_body["to_delete"] = True

    return wrapped_body


def unwrap_serialization(wrapped_serialization):
    if wrapped_serialization.get("to_delete"):
        body = wrapped_serialization.get('body')
        model_class = apps.get_model(body.get('model'))
        fields = body.get('fields')
        model_class.objects.filter(uuid=fields.get('uuid')).delete()
        return None
    else:
        return wrapped_serialization.get("body")


def persist(structure):
    try:
        model_class = apps.get_model(structure.get('model'))
    except LookupError:
        return
    if structure:
        fields = structure.get('fields')
        for field_name, value in fields.items():
            if isinstance(value, dict):
                fields[field_name] = persist(value)

        lookup_kwargs = {}
        if structure.get('model') == "base.Person":
            lookup_kwargs['global_id'] = fields.get('global_id')
        else:
            lookup_kwargs['uuid'] = fields.get('uuid')

        query_set = model_class.objects.filter(**lookup_kwargs)
        persisted_obj = query_set.first()
        super_class = model_class.__bases__[0]
        if not persisted_obj:
            obj_id = _make_upsert(fields, super_class, model_class)
            if obj_id:
                return obj_id
            raise MigrationPersistanceError
        elif _changed_since_last_synchronization(fields, structure):
            return _make_upsert(fields, super_class, model_class, instance=persisted_obj)
        else:
            return persisted_obj.id
    return None


def _convert_datetime_to_long(dtime):
    return time.mktime(dtime.timetuple()) if dtime else None


def _get_value(fields, field):
    attribute = fields.get(field.name)
    if isinstance(field, (DateTimeField, DateField)):
        return _convert_long_to_datetime(attribute)
    return attribute


def _convert_long_to_datetime(date_as_long):
    return datetime.datetime.fromtimestamp(date_as_long) if date_as_long else None


def _get_field_name(field):
    if field.is_relation:
        return '{}_id'.format(field.name)
    return field.name


def _make_upsert(fields, super_class, model_class, instance=None):
    kwargs = _build_kwargs(fields, model_class)
    del kwargs['id']
    if instance:
        # Fields can contain only partial update of models, so we need to setattr on instance found in DB
        for field_name, value in kwargs.items():
            setattr(instance, field_name, value)
        super(super_class, instance).save(force_update=True)
    else:
        instance = model_class(**kwargs)
        super(super_class, instance).save(force_insert=True)
    return instance.id


def _build_kwargs(fields, model_class):
    return {_get_field_name(f): _get_value(fields, f) for f in model_class._meta.fields if f.name in fields.keys()}


def _changed_since_last_synchronization(fields, structure):
    last_sync = _convert_long_to_datetime(structure.get('last_sync'))
    changed = _convert_long_to_datetime(fields.get('changed'))
    return not last_sync or not changed or changed > last_sync
