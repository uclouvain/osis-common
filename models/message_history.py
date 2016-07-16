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
from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.utils.safestring import mark_safe


class MessageHistoryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(MessageHistoryAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    date_hierarchy = 'created'
    list_display = ('receiver_id', 'reference', 'subject', 'sent', 'created')
    fieldsets = ((None, {'fields': ('receiver_id', 'reference',
                                    'subject', ('sent', 'created'), 'content_html_safe', 'content_txt')}),)
    readonly_fields = ('receiver_id', 'reference', 'subject', 'sent', 'created', 'content_html_safe', 'content_txt')
    ordering = ['-created']
    search_fields = ['receiver_id', 'reference', 'subject']


class MessageHistory(models.Model):
    subject = models.CharField(max_length=255)
    content_txt = models.TextField()
    content_html = models.TextField()
    receiver_id = models.IntegerField()
    created = models.DateTimeField(editable=False)
    sent = models.DateTimeField(null=True)
    reference = models.CharField(max_length=100, null=True, db_index=True)
    show_to_user = models.BooleanField(default=True)
    read_by_user = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        return super(MessageHistory, self).save(*args, **kwargs)

    def __str__(self):
        return self.subject

    def content_html_safe(self):
        return mark_safe(self.content_html)


def find_by_id(message_history_id):
    message_history = MessageHistory.objects.get(id=message_history_id)
    return message_history


def find_my_messages(person):
    """
    Get the messages for a user to show in my osis.
    :param person: The related person
    :return: The list of messages for this person
    """
    return MessageHistory.objects.filter(person=person).filter(show_to_user=True).order_by('sent')


def delete_my_messages(messages_ids):
    """
    Delete messages from my osis (but not from history)
    :param messages_ids: The ids list of messages to delete from my osis
    """
    MessageHistory.objects.filter(id__in=messages_ids).update(show_to_user=False)


def read_my_message(message_id):
    """
    Get a message from message history and set it as read in my osis
    :param message_id: The id of the message
    :return : The message
    """
    message = MessageHistory.objects.get(id=message_id)
    message.read_by_user = True
    message.save()
    return message


def mark_as_read(messages_ids):
    """
    Mark a list of messages as read in my osis
    :param messages_ids: The ids list of messages
    """
    MessageHistory.objects.filter(id__in=messages_ids).update(read_by_user=True)
