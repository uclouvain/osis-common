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
from django.contrib import messages
from django.contrib.postgres.fields import JSONField
from django.db import models

from osis_common.models import osis_model_admin
from osis_common.queue import queue_sender


class QueueExceptionAdmin(osis_model_admin.OsisModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('queue_name', 'exception_title', 'creation_date')
    readonly_fields = ('queue_name', 'exception_title', 'creation_date', 'message', 'exception', )
    ordering = ['-creation_date']
    search_fields = ['queue_name', 'exception_title']
    actions = ['resend_messages_to_queue']

    def resend_messages_to_queue(self, request, queryset):
        for q_exception in queryset:
            try:
                queue_sender.send_message(q_exception.queue_name, q_exception.message)
                q_exception.delete()
            except Exception:
                self.message_user(request,
                                  'Message %s not sent to %s.' % (q_exception.pk, q_exception.queue_name),
                                  level=messages.ERROR)
        self.message_user(request, "Messages sent.", level=messages.SUCCESS)


class QueueException(models.Model):
    queue_name = models.CharField(max_length=255)
    creation_date = models.DateTimeField(auto_now_add=True)
    message = JSONField(null=True)
    exception_title = models.CharField(max_length=255)
    exception = models.TextField()

    def __str__(self):
        return self.exception_title

    def to_exception_log(self):
        return 'QName: {}\n\nDate: {}\n\nExceptionTitle: {}\n\nException: {}\n\nMessage: {}\n\n'.format(
            str(self.queue_name),
            str(self.creation_date),
            str(self.exception_title),
            str(self.exception),
            str(self.message)
        )
