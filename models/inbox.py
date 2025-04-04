##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2023 Université catholique de Louvain (http://www.uclouvain.be)
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

from django.contrib import admin
from django.db import models
from django_admin_listfilter_dropdown.filters import DropdownFilter

from osis_common.models import osis_model_admin
from osis_common.utils.inbox_outbox import HandlersPerContextFactory, InboxConsumer


class InboxAdmin(osis_model_admin.OsisModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = (
        'transaction_id', 'consumer', 'event_name',  'payload', 'creation_date', 'status', 'last_execution_date',
    )
    readonly_fields = (
        'transaction_id', 'consumer', 'event_name', 'payload', 'creation_date', 'status', 'last_execution_date',
    )
    ordering = ['-creation_date']
    search_fields = ['consumer', 'payload']
    list_filter = ['status', 'consumer', ('event_name', DropdownFilter),]
    actions = [
        'consommer_evenement',
    ]

    @admin.action(
        description="Consomme les événements sélectionnés (déclenche les réactions immédiatement - en synchrone) "
                    "/!\ Non respect de l'ordre peut mener à des inconsistances"
    )
    def consommer_evenement(self, request, queryset):
        from infrastructure.messages_bus import message_bus_instance
        handlers = HandlersPerContextFactory.get()
        for unprocessed_event in queryset:
            context_name = unprocessed_event.consumer
            inbox_consumer = InboxConsumer(
                message_bus_instance=message_bus_instance,
                context_name=context_name,
                event_handlers=handlers[context_name],
            )
            inbox_consumer.consume(unprocessed_event)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class InboxAbstractModel(models.Model):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"
    DEAD_LETTER = "DEAD_LETTER"

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSED, 'Done'),
        (ERROR, 'Error'),
        (DEAD_LETTER, 'Dead letter')
    ]
    consumer = models.CharField(max_length=255)
    event_name = models.CharField(max_length=255)
    transaction_id = models.UUIDField()
    payload = models.JSONField(default=dict, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    last_execution_date = models.DateTimeField(null=True, blank=True)
    traceback = models.TextField(null=True, blank=True)
    attempts_number = models.IntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True


class Inbox(InboxAbstractModel):
    class Meta:
        verbose_name_plural = "inbox"
        unique_together = (
            'consumer', 'transaction_id',
        )

    def mark_as_processed(self):
        self.status = self.PROCESSED
        self.last_execution_date = datetime.datetime.now()
        self.attempts_number += 1
        self.save()

    def mark_as_error(self, error_description: str = None):
        self.status = self.ERROR
        self.last_execution_date = datetime.datetime.now()
        self.traceback = error_description
        self.attempts_number += 1
        self.save()

    def mark_as_dead_letter(self, error_description: str = None):
        self.status = self.DEAD_LETTER
        self.last_execution_date = datetime.datetime.now()
        if error_description is not None:
            self.traceback = error_description
        self.attempts_number += 1
        self.save()

    def is_successfully_processed(self) -> bool:
        return self.status == self.PROCESSED


class InboxArchived(InboxAbstractModel):
    creation_date = models.DateTimeField()

    class Meta:
        verbose_name_plural = "inbox archived"
