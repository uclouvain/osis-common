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
from django.test import TestCase
from osis_common.queue.callbacks import insert_or_update
from osis_common.tests.models_for_tests.serializable_tests_models import ModelWithUser


def model_with_user_json():
    return """{"to_delete": 'False', "serialized_objects": '[{"model": "tests.modelwithuser",
    "fields": {"uuid": "3ca878cf-9391-49cf-8e4e-3909111f74ed", "name": "With User"}}]'}"""


def model_withour_user_json():
    return """{'to_delete': True, 'serialized_objects': '[{"model": "tests.modelwithoutuser",
    "fields": {"uuid": "daf86b06-b784-4e02-9131-3098da60506c", "name": "Without User"}}]'}"""


class TestInsertOrUpdate(TestCase):

    def test_insert_model_with_user(self):
        model_with_user = ModelWithUser.find_by_name('With User')
        self.assertIsNone(model_with_user)
        insert_or_update(model_with_user_json())
        model_with_user = ModelWithUser.find_by_name('With User')
        self.assertIsNotNone(model_with_user)
        self.assertIsNone(model_with_user.user)


