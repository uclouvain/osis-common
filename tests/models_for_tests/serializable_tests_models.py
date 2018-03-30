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
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import CharField

from osis_common.models.serializable_model import SerializableModel
from django.db import models


class ModelWithUser(SerializableModel):
    user = CharField(max_length=30, null=True)
    name = CharField(max_length=30, unique=True)

    def __str__(self):
        return '{} - {} - {}'.format(self.name, self.user, self.uuid)

    @classmethod
    def find_by_name(cls,name):
        try:
            return ModelWithUser.objects.get(name=name)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def find_by_id(cls, id):
        try:
            return ModelWithUser.objects.get(id=id)
        except ObjectDoesNotExist:
            return None


class ModelWithoutUser(SerializableModel):
    name = CharField(max_length=30, unique=True)

    def __str__(self):
        return '{} - {}'.format(self.name, self.uuid)

    @classmethod
    def find_by_name(self,name):
        try:
            return ModelWithoutUser.objects.get(name=name)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def find_by_id(cls, id):
        try:
            return ModelWithoutUser.objects.get(id=id)
        except ObjectDoesNotExist:
            return None


class ModelNotSerializable(models.Model):
    pass
