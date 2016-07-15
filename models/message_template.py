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
from ckeditor.fields import RichTextField
from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.conf import settings


class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('reference', 'subject', 'format', 'language')
    fieldsets = ((None, {'fields': ('reference', 'subject', 'template', 'format', 'language')}),)

    def get_actions(self, request):
        actions = super(MessageTemplateAdmin, self).get_actions(request)
        if not self.has_delete_permission(request) and 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class MessageTemplate(models.Model):
    FORMAT_CHOICES = (('PLAIN', _('plain')),
                      ('HTML', 'HTML'),
                      ('PLAIN_HTML', _('plain_and_html')))

    reference = models.CharField(max_length=50)
    subject = models.CharField(max_length=255)
    template = RichTextField()
    format = models.CharField(max_length=15, choices=FORMAT_CHOICES)
    language = models.CharField(max_length=30, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)

    def __str__(self):
        return self.subject

    class Meta:
        unique_together = ('reference', 'language')


def find_by_reference(reference):
    message_template = MessageTemplate.objects.filter(reference=reference)
    return message_template


def find_by_reference_and_language(reference, language=settings.LANGUAGE_CODE):
    message_template = MessageTemplate.objects.get(reference=reference, language=language)
    return message_template
