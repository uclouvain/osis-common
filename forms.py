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
from ckeditor.widgets import CKEditorWidget
from django import forms
from django.conf import settings
from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _
from osis_common.models import message_template
from osis_common.models.document_file import DocumentFile


class MessageTemplateForm(ModelForm):
    template = forms.CharField(widget=CKEditorWidget)

    class Meta:
        model = message_template.MessageTemplate
        fields = ['reference', 'subject', 'template', 'format', 'language']


class UploadDocumentFileForm(ModelForm):
    file_name = forms.CharField(required=False)

    class Meta:
        model = DocumentFile
        fields = ('content_type', 'storage_duration', 'file', 'description', 'user',
                  'application_name', 'size')
        widgets = {'storage_duration': forms.HiddenInput(), 'user': forms.HiddenInput(),
                   'content_type': forms.HiddenInput(), 'size': forms.HiddenInput(),
                   'application_name': forms.HiddenInput()}

    def clean(self):
        cleaned_data = super(UploadDocumentFileForm, self).clean()
        file = cleaned_data.get("file")
        if file:
            if file.size > settings.MAX_UPLOAD_SIZE:
                self.errors['file'] = _('MAX_UPLOAD_SIZE')
            if file.content_type not in settings.CONTENT_TYPES:
                self.errors['content_type'] = _(' title')
        return cleaned_data
