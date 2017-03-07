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
import re
import json
from django.test.testcases import TestCase
from osis_common.models.exception import MultipleModelsSerializationException
from osis_common.models.serializable_model import serialize_objects, format_data_for_migration, SerializableModel
from osis_common.tests.models_for_tests.serializable_tests_models import ModelWithoutUser, \
    ModelWithUser, ModelNotSerializable


class TestSerializeObject(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.model_with_user = ModelWithUser(user='user1', name='With User')
        cls.model_without_user = ModelWithoutUser(name='Without User')

    def test_serialization_with_objecst_none(self):
        serializabled_object = serialize_objects(None)
        self.assertIsNone(serializabled_object)

    def test_serialization_with_multiple_models(self):
        objects_to_serialize = [self.model_with_user, self.model_without_user]
        self.assertRaises(MultipleModelsSerializationException, serialize_objects, objects=objects_to_serialize)

    def test_serialization_with_user(self):
        objects_to_serialize = [self.model_with_user]
        serialized_object = json.loads(serialize_objects(objects_to_serialize))
        # [{'fields': {'name': 'With User'}, 'pk': None, 'model': 'tests.modelwithuser'}]
        serialized_fields = serialized_object[0].get('fields')
        serialized_model = serialized_object[0].get('model')
        self.assertIsNone(serialized_fields.get('user'))
        self.assertEqual('With User', serialized_fields.get('name'))
        self.assertEqual('tests.modelwithuser', serialized_model)

    def test_serialization_without_user(self):
        objects_to_serialize = [self.model_without_user]
        serialized_object = json.loads(serialize_objects(objects_to_serialize))
        # [{'fields': {'name': 'Without User'}, 'pk': None, 'model': 'tests.modelwithoutuser'}]
        serialized_fields = serialized_object[0].get('fields')
        serialized_model = serialized_object[0].get('model')
        self.assertEqual('Without User', serialized_fields.get('name'))
        self.assertEqual('tests.modelwithoutuser', serialized_model)

    def test_contains_uuid_field(self):
        self.assertTrue(getattr(self.model_with_user, 'uuid'))
        obj = ModelNotSerializable()
        self.assertRaises(AttributeError, getattr, obj, 'uuid')

    def test__str__uuid(self):
        serializable_model = SerializableModel()
        # serializable_model.save()
        result = re.match('[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}', '{}'.format(serializable_model))
        self.assertIsNotNone(result)


class TestFormatDataForMigration(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.model_with_user = ModelWithUser(user='user1', name='With User')
        cls.model_without_user = ModelWithoutUser(name='Without User')

    def test_format_with_delete(self):
        object_to_format = [self.model_without_user]
        formated_objects = format_data_for_migration(object_to_format, to_delete=True)
        self.assertTrue(formated_objects.get('to_delete'))

    def test_format_without_delete(self):
        object_to_format = [self.model_with_user]
        formated_objects = format_data_for_migration(object_to_format, to_delete=False)
        self.assertFalse(formated_objects.get('to_delete'))
