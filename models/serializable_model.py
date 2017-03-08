##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2016 Université catholique de Louvain (http://www.uclouvain.be)
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
import logging
import uuid
import datetime
import time
import json
from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.core import serializers
from django.utils.encoding import force_text
from pika.exceptions import ChannelClosed, ConnectionClosed
from osis_common.models.exception import MultipleModelsSerializationException, MigrationPersistanceError
from osis_common.queue import queue_sender
from osis_common import signals

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


class SerializableModelAdmin(admin.ModelAdmin):
    actions = ['resend_messages_to_queue']

    def resend_messages_to_queue(self, request, queryset):
        counter = 0
        for record in queryset:
            try:
                instance_serialized = serialize(record)
                queue_sender.send_message(settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_PRODUCE'),
                                          {'body': instance_serialized})
                counter += 1
            except (ChannelClosed, ConnectionClosed):
                self.message_user(request,
                                  'Message %s not sent to %s.' % (record.pk, record.queue_name),
                                  level=messages.ERROR)
        self.message_user(request, "{} message(s) sent.".format(counter), level=messages.SUCCESS)


class SerializableModel(models.Model):
    objects = SerializableModelManager()

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    def natural_key(self):
        return [self.uuid]

    def __str__(self):
        return self.uuid

    class Meta:
        abstract = True

    @classmethod
    def find_by_uuid(cls,uuid):
        try:
            return cls.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        super(SerializableModel, self).save(*args, **kwargs)
        signals.send_to_queue.send(sender=self.__class__, instance=self, to_delete=False)


    def delete(self, *args, **kwargs):
        super(SerializableModel, self).delete(*args, **kwargs)
        signals.send_to_queue.send(sender=self.__class__, instance=self, to_delete=True)


# To be deleted
def format_data_for_migration(objects, to_delete=False):
    """
    Format data to fit to a specific structure.
    :param objects: A list of model instances.
    :param to_delete: True if these records are to be deleted on the Osis-portal side.
                      False if these records are to insert or update on the OPsis-portal side.
    :return: A structured dictionary containing the necessary data to migrate from Osis to Osis-portal.
    """
    return {'serialized_objects': serialize_objects(objects), 'to_delete': to_delete}


# To be deleted
def serialize_objects(objects, format='json'):
    """
    Serialize all objects given by parameter.
    All objects must come from the same model. Otherwise, an exception will be thrown.
    If the object contains a FK 'user', this field will be ignored for the serialization.
    :param objects: List of objects to serialize.
    :return: Json data containing serializable objects.
    """
    if not objects:
        return None
    if len({obj.__class__ for obj in objects}) > 1:
        raise MultipleModelsSerializationException
    model_class = objects[0].__class__
    return serializers.serialize(format,
                                 objects,
                                 # indent=2,
                                 fields=[field.name for field in model_class._meta.fields if field.name != 'user'],
                                 use_natural_foreign_keys=True,
                                 use_natural_primary_keys=True)



##################################
##### QUEUE  DESERIALIZER ########
##################################


def deserialize(serialized_data):
    if isinstance(serialized_data, dict):
        _deserialize(serialized_data)
    else:
        raise TypeError('Serialized data must be a dict')


def _deserialize(dict):
    body = dict.get('body')
    model_class = apps.get_model(body.get('model'))
    fields = body.get('fields')

    if dict.get('to_delete'):
        _delete_instance_by_uuid(model_class, fields.get('uuid'))
    else:
        _persist(model_class, fields, dict.get('last_sync'))


def _delete_instance_by_uuid(cls, uuid):
    cls.objects.filter(uuid=uuid).delete()


def _persist(cls, data_to_persist, last_sync=None):
    for field_name, value in data_to_persist.items():
        if isinstance(value, dict):
            data_to_persist[field_name] = _persist(value.get('model'), value)

    query_set = cls.objects.filter(uuid=data_to_persist.get('uuid'))
    if query_set.count() == 0:
        return _make_insert(cls, data_to_persist)
    else:
        instance = query_set.first()
        if _changed_since_last_synchronization(data_to_persist, {'last_sync': last_sync}):
            return _make_update(cls, data_to_persist, instance, query_set)
        return instance.id


def _make_update(model_class, fields, persisted_obj, query_set):
    kwargs = _build_kwargs(fields, model_class)
    kwargs['id'] = persisted_obj.id
    query_set.update(**kwargs)
    return persisted_obj.id


def _make_insert(model_class, fields):
    kwargs = _build_kwargs(fields, model_class)
    if 'id' in kwargs:
        del kwargs['id']
    obj = model_class(**kwargs)
    super(SerializableModel, obj).save(force_insert=True)
    if obj.id:
        return obj.id
    else:
        raise MigrationPersistanceError


def _build_kwargs(fields, model_class):
    return {_get_field_name(f): _get_value(fields, f) for f in model_class._meta.fields if f.name in fields.keys()}


def _changed_since_last_synchronization(fields, structure):
    last_sync = _convert_long_to_datetime(structure.get('last_sync'))
    changed = _convert_long_to_datetime(fields.get('changed'))
    return not last_sync or not changed or changed > last_sync


def _get_field_name(field):
    if field.is_relation:
        return '{}_id'.format(field.name)
    return field.name


def _get_value(fields, field):
    attribute = fields.get(field.name)
    if isinstance(field, models.DateTimeField) or isinstance(field, models.DateField):
        return _convert_long_to_datetime(attribute)
    return attribute


def _convert_long_to_datetime(date_as_long):
    return datetime.datetime.fromtimestamp(date_as_long) if date_as_long else None


##################################
####### QUEUE SERIALIZER #########
##################################


def serialize(obj, last_syncs=None):
    if obj:
        dict = {}
        for f in obj.__class__._meta.fields:
            attribute = getattr(obj, f.name)
            if f.is_relation:
                try:
                    if attribute and getattr(attribute, 'uuid'):
                        dict[f.name] = serialize(attribute, last_syncs=last_syncs)
                except AttributeError:
                    pass
            else:
                try:
                    json.dumps(attribute)
                    dict[f.name] = attribute
                except TypeError:
                    if isinstance(f, models.DateTimeField) or isinstance(f, models.DateField):
                        dt = attribute
                        dict[f.name] = _convert_datetime_to_long(dt)
                    else:
                        dict[f.name] = force_text(attribute)
        class_label = obj.__class__._meta.label
        last_sync = None
        if last_syncs:
            last_sync = _convert_datetime_to_long(last_syncs.get(class_label))
        return {"model": class_label, "fields": dict, 'last_sync': last_sync}
    else:
        return None


def _convert_datetime_to_long(dtime):
    return time.mktime(dtime.timetuple()) if dtime else None