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
import json
import logging

from django.conf import settings
from django.test import TestCase

from osis_common.queue.callbacks import process_message
from osis_common.tests.models_for_tests.serializable_tests_models import ModelWithUser, ModelWithoutUser

logger = logging.getLogger(settings.DEFAULT_LOGGER)


def get_object_json(model_name='modelwithuser', to_delete=False):
    data_json = json.dumps(
        {
            'to_delete': to_delete,
            'body': __get_serialized_objects(model_name)
        }
    )
    return bytearray(data_json, "utf-8")


def __get_serialized_objects(model_name):
    if 'modelwithuser' == model_name:
        return __get_serialized_objects_with_user()
    elif 'modelwithoutuser' == model_name:
        return __get_serialized_objects_without_user()
    return None


def __get_serialized_objects_with_user():
    return {
        "model": "tests.modelwithuser",
        "fields":
            {
                "id": 1,
                "uuid": "c03a1839-6eb3-4565-b256-e0aea5ec8437",
                "name": "With User"
            }
    }


def __get_serialized_objects_without_user():
    return {
        "model": "tests.modelwithoutuser",
        "fields":
            {
                "id": 2,
                "uuid": "daf86b06-b784-4e02-9131-3098da60506c",
                "name": "Without User"
            }
    }


def get_object(model_name, name, uuid, user=None):
    if 'modelwithuser' == model_name:
        return ModelWithUser(name=name, uuid=uuid, user=user)
    elif 'modelwithoutuser' == model_name:
        return ModelWithoutUser(name=name, uuid=uuid)
    return None


class ProcessMessage(TestCase):

    def test_insert_model(self):
        model = ModelWithUser.find_by_name('With User')
        self.assertIsNone(model)
        process_message(get_object_json())
        model = ModelWithUser.find_by_name('With User')
        self.assertIsNotNone(model)
        self.assertIsNone(model.user)

    def test_delete_model(self):
        model = ModelWithUser(name='With User', uuid='c03a1839-6eb3-4565-b256-e0aea5ec8437')
        model.save()
        model = ModelWithUser.find_by_name('With User')
        self.assertIsNotNone(model)
        process_message(get_object_json(to_delete=True))
        model = ModelWithUser.find_by_name('With User')
        self.assertIsNone(model)

    def test_update_without_user(self):
        model_without_user = get_object(model_name='modelwithoutuser',
                                        name='Without User Before Update',
                                        uuid='daf86b06-b784-4e02-9131-3098da60506c')
        model_without_user.save()
        model_id = model_without_user.id
        model_without_user = ModelWithoutUser.find_by_id(id=model_id)
        self.assertEqual(model_without_user.name, 'Without User Before Update')
        process_message(get_object_json(model_name='modelwithoutuser'))
        model_without_user = ModelWithoutUser.find_by_id(id=model_id)
        self.assertEqual(model_without_user.name, 'Without User')

    def test_update_with_user_object_user_defined(self):
        model_with_user = get_object(model_name='modelwithuser',
                                     name='With User Undefined',
                                     uuid='c03a1839-6eb3-4565-b256-e0aea5ec8437',
                                     user='user1')
        model_with_user.save()
        model_id = model_with_user.id
        model_with_user = ModelWithUser.find_by_id(id=model_id)
        self.assertEqual(model_with_user.name, 'With User Undefined')
        self.assertEqual(model_with_user.user, 'user1')
        process_message(get_object_json(model_name='modelwithuser'))
        model_with_user = ModelWithUser.find_by_id(id=model_id)
        self.assertEqual(model_with_user.name, 'With User')
        self.assertEqual(model_with_user.user, 'user1')

    def test_update_with_user_object_user_undefined(self):
        model_with_user = get_object(model_name='modelwithuser',
                                     name='With User Undefined',
                                     uuid='c03a1839-6eb3-4565-b256-e0aea5ec8437')
        model_with_user.save()
        model_id = model_with_user.id
        model_with_user = ModelWithUser.find_by_id(id=model_id)
        self.assertEqual(model_with_user.name, 'With User Undefined')
        self.assertIsNone(model_with_user.user)
        process_message(get_object_json(model_name='modelwithuser'))
        model_with_user = ModelWithUser.find_by_id(id=model_id)
        self.assertEqual(model_with_user.name, 'With User')
        self.assertIsNone(model_with_user.user)




