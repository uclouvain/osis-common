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
from unittest.mock import patch

from django.test.testcases import TestCase
from django.db.models.fields import CharField

from osis_common.models.auditable_serializable_model import AuditableSerializableModel


class AuditableModelWithUser(AuditableSerializableModel):
    user = CharField(max_length=30, null=True)
    name = CharField(max_length=30, unique=True)

    def __str__(self):
        return '{} - {} - {}'.format(self.name, self.user, self.uuid)


class TestAuditableSerializableObject(TestCase):
    def setUp(self):
        self.auditable_instance = AuditableModelWithUser(user="User", name="Name")

    @patch("osis_common.models.auditable_serializable_model.serializable_model_post_save", side_effect=None)
    def test_save(self, mock_post_save):
        self.auditable_instance.save()
        self.assertTrue(mock_post_save.called)

    @patch("osis_common.models.auditable_serializable_model.serializable_model_post_delete", side_effect=None)
    def test_delete(self, mock_post_delete):
        self.auditable_instance.save()
        self.auditable_instance.delete()
        self.assertTrue(mock_post_delete.called)
        mock_post_delete.assert_called_once_with(self.auditable_instance, to_delete=True)
        self.assertTrue(self.auditable_instance.deleted)
