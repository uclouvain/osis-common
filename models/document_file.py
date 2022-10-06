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

from osis_common.models import serializable_model, osis_model_admin


class DocumentFileAdmin(osis_model_admin.OsisModelAdmin):
    list_display = ('uuid', 'file_name', 'content_type', 'description', 'update_by', 'creation_date', 'size')
    readonly_fields = ('creation_date',)
    search_fields = ('file_name', 'update_by')


CONTENT_TYPE_CHOICES = (('application/csv', 'application/csv'),
                        ('application/doc', 'application/doc'),
                        ('application/pdf', 'application/pdf'),
                        ('application/xls', 'application/xls'),
                        ('application/xlsx', 'application/xlsx'),
                        ('application/xml', 'application/xml'),
                        ('application/zip', 'application/zip'),
                        ('image/jpeg', 'image/jpeg'),
                        ('image/gif', 'image/gif'),
                        ('image/png', 'image/png'),
                        ('text/html', 'text/html'),
                        ('text/plain', 'text/plain'),)


class DocumentFile(serializable_model.SerializableModel):
    file_name = models.CharField(max_length=100)
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES, default='application/csv')
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)
    storage_duration = models.IntegerField()
    file = models.FileField(upload_to='')
    description = models.CharField(max_length=50)
    update_by = models.CharField(max_length=254, default='system', db_index=True)
    application_name = models.CharField(max_length=100, null=True, blank=True)
    size = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.file.name = str(self.uuid)
        super(DocumentFile, self).save(*args, **kwargs)

    def __str__(self):
        return self.file_name

    def is_image_content(self):
        if self.content_type and self.content_type.startswith('image'):
            return True
        return False


def find_by_id(document_file_id):
    return DocumentFile.objects.get(pk=document_file_id)
