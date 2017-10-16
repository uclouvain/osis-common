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
from django.contrib import admin
from django.db import models


class AuditableQuerySet(models.QuerySet):
    # Called in case of bulk delete
    # Override this function is important to force to call the delete() function of a model's instance
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()


class AuditableModelManager(models.Manager):
    def get_queryset(self):
        return AuditableQuerySet(self.model, using=self._db).exclude(deleted=True)


class AuditableModelAdmin(admin.ModelAdmin):
    actions = ['resend_messages_to_queue']


class AuditableModel(models.Model):
    objects = AuditableModelManager()

    deleted = models.BooleanField(null=False, blank=False, default=False)

    def save(self, *args, **kwargs):
        if self.deleted is True:
            # For now, the only way to set deleted = True is to do it on the database.
            # The ORM will receive this responsibility ONLY when the cascade delete can handle the deleted field.
            raise AttributeError('The ORM cannot set `deleted` to True')
        else:
            super(AuditableModel, self).save(*args, **kwargs)
            auditable_model_post_save(self)

    def delete(self, *args, **kwargs):
        super(AuditableModel, self).delete(*args, **kwargs)
        auditable_model_post_delete(self)

    def __str__(self):
        return "{}".format(self)

    class Meta:
        abstract = True


def auditable_model_post_save(instance):
    # This function is called in the save() method of AuditableModel and AuditableSerializableModel
    # Any change made here will be applied to all models inheriting AuditableModel or AuditableSerializableModel
    pass


def auditable_model_post_delete(instance):
    # This function is called in the delete() method of AuditableModel and AuditableSerializableModel
    # Any change made here will be applied to all models inheriting AuditableModel or AuditableSerializableModel
    pass