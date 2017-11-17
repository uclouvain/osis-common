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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from osis_common.models.auditable_model import auditable_model_flag_delete
from osis_common.models.auditable_serializable_model import AuditableSerializableModel

from django.db import models


class TestAuditableSerializableModel1(AuditableSerializableModel):
    name = models.CharField(max_length=100, blank=True, null=True)


class TestAuditableSerializableModel2(AuditableSerializableModel):
    name = models.CharField(max_length=100, blank=True, null=True)
    parent = models.ForeignKey(TestAuditableSerializableModel1)


class TestAuditableSerializableModel3(AuditableSerializableModel):
    name = models.CharField(max_length=100, blank=True, null=True)
    parent = models.ForeignKey(TestAuditableSerializableModel2)


class TestAuditableSerializableModel4(AuditableSerializableModel):
    name = models.CharField(max_length=100, blank=True, null=True)
    parent = models.ForeignKey(TestAuditableSerializableModel1)


class AuditableSerializableModelTest(TestCase):
    def setUp(self):
        pass

    def test_auditable_serializable_model_post_delete(self):
        i = 1
        parent = TestAuditableSerializableModel1.objects.create(name=str(i))
        subparent_1 = TestAuditableSerializableModel2.objects.create(parent=parent, name=str(i))
        subparent_2 = TestAuditableSerializableModel3.objects.create(parent=subparent_1, name=str(i))
        subparent_3 = TestAuditableSerializableModel4.objects.create(parent=parent, name=str(i))

        result = auditable_model_flag_delete(parent)

        self.assertTrue(result)

        self.is_not_existing_for_orm(parent)
        self.is_not_existing_for_orm(subparent_1)
        self.is_not_existing_for_orm(subparent_2)
        self.is_not_existing_for_orm(subparent_3)

    def is_not_existing_for_orm(self, obj):
        with self.assertRaises(ObjectDoesNotExist):
            obj.__class__.objects.get(id=obj.id)
