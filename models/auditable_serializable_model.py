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
import uuid

from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from osis_common.models.auditable_model import auditable_model_post_save, auditable_model_post_delete
from osis_common.models.serializable_model import serialize, serializable_model_post_save, \
    serializable_model_post_delete, serializable_model_resend_messages_to_queue, wrap_serialization


class AuditableSerializableQuerySet(models.QuerySet):
    # Called in case of bulk delete
    # Override this function is important to force to call the delete() function of a model's instance
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()


class AuditableSerializableModelManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)

    def get_queryset(self):
        return AuditableSerializableQuerySet(self.model, using=self._db).exclude(deleted=True)


class AuditableSerializableModelAdmin(admin.ModelAdmin):
    actions = ['resend_messages_to_queue']

    def resend_messages_to_queue(self, request, queryset):
        serializable_model_resend_messages_to_queue(self, request, queryset)


class AuditableSerializableModel(models.Model):
    objects = AuditableSerializableModelManager()

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    deleted = models.BooleanField(null=False, blank=False, default=False)

    def save(self, *args, **kwargs):
        if self.deleted is True:
            # For now, the only way to set deleted = True is to do it on the database.
            # The ORM will receive this responsibility ONLY when the cascade delete can handle the deleted field.
            raise AttributeError('The ORM cannot set `deleted` to True')
        else:
            super(AuditableSerializableModel, self).save(*args, **kwargs)
            auditable_model_post_save(self)
            serializable_model_post_save(self)

    def delete(self, *args, **kwargs):
        super(AuditableSerializableModel, self).delete(*args, **kwargs)
        auditable_model_post_delete(self)
        serializable_model_post_delete(self)

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
