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
from django.db import models

from osis_common.models import osis_model_admin


class OutboxAdmin(osis_model_admin.OsisModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('transaction_id', 'event_name',  'payload', 'creation_date', 'sent', 'sent_date',)
    readonly_fields = ('transaction_id', 'event_name', 'payload', 'creation_date', 'sent', 'sent_date',)
    ordering = ['-creation_date']
    list_filter = ['event_name']
    search_fields = ['payload']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class OutboxAbstractModel(models.Model):
    event_name = models.CharField(max_length=255)
    transaction_id = models.UUIDField(unique=True)
    payload = models.JSONField(default=dict, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    sent_date = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True


class Outbox(OutboxAbstractModel):
    class Meta:
        verbose_name_plural = "outbox"


class OutboxArchived(OutboxAbstractModel):
    creation_date = models.DateTimeField()

    class Meta:
        verbose_name_plural = "Outbox archived"
