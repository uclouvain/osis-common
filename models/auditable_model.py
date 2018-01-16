##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2017 Université catholique de Louvain (http://www.uclouvain.be)
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
from django.contrib import admin
from django.contrib.admin.utils import NestedObjects
from django.db import models, transaction
from django.db.utils import DEFAULT_DB_ALIAS, DatabaseError
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(settings.DEFAULT_LOGGER)


class AuditableQuerySet(models.QuerySet):
    # Called in case of bulk delete
    # Override this function is important to force to call the delete() function of a model's instance
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()


class AuditableModelManager(models.Manager):
    def get_queryset(self):
        return AuditableQuerySet(self.model, using=self._db).filter(deleted__isnull=True)


class AuditableModelAdmin(admin.ModelAdmin):
    actions = ['resend_messages_to_queue']


class AuditableModel(models.Model):
    objects = AuditableModelManager()

    deleted = models.DateTimeField(null=True, blank=True, default=None, db_index=True)

    def save(self, *args, **kwargs):
        super(AuditableModel, self).save(*args, **kwargs)
        auditable_model_post_save(self)

    def delete(self, *args, **kwargs):
        # Return the list of deleted objects
        return auditable_model_flag_delete(self)

    class Meta:
        abstract = True


def auditable_model_post_save(instance):
    # This function is called in the save() method of AuditableModel and AuditableSerializableModel
    # Any change made here will be applied to all models inheriting AuditableModel or AuditableSerializableModel
    pass


def auditable_model_flag_delete(instance):
    # This function is called in the delete() method of AuditableModel and AuditableSerializableModel
    # Any change made here will be applied to all models inheriting AuditableModel or AuditableSerializableModel
    collector = NestedObjects(using=DEFAULT_DB_ALIAS)
    collector.collect([instance])

    nested_objects = collector.nested()
    deleted_datetime = timezone.now()
    try:
        with transaction.atomic():
            _update_deleted_flag_in_tree(nested_objects, deleted_datetime)

    except DatabaseError as e:
        logging.exception(str(e))
        raise e
    return nested_objects


def _update_deleted_flag_in_tree(node, deleted_datetime):
    if isinstance(node, list):
        for subnode in node:
            _update_deleted_flag_in_tree(subnode, deleted_datetime)
    else:
        _update_deleted_flag(node, deleted_datetime)


def _update_deleted_flag(node, deleted_datetime):
    if hasattr(node, 'deleted'):
        node.deleted = deleted_datetime
        node.save()

