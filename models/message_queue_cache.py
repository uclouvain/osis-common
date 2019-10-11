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
from django.contrib.postgres.fields import JSONField
from django.db import models

from osis_common.models import osis_model_admin
from osis_common.queue import queue_sender


class MessageQueueCacheAdmin(osis_model_admin.OsisModelAdmin):
    list_display = ('queue', 'data', 'changed')


class MessageQueueCache(models.Model):
    queue = models.CharField(max_length=255)
    data = JSONField()
    changed = models.DateTimeField(auto_now_add=True)  # Insert date

    def __str__(self):
        return "{} - {}".format(self.queue, self.changed)


def get_messages_to_retry():
    return MessageQueueCache.objects.order_by('changed')


def retry_all_cached_messages():
    messages_to_retry = get_messages_to_retry()
    for message in messages_to_retry:
        queue_sender.send_message(message.queue, message.data)
        message.delete()
