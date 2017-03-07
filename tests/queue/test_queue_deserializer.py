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
import datetime
import time
from django.test import TestCase
from osis_common.tests.models_for_tests.serializable_tests_models import ModelWithUser, ModelWithDate, ModelWithDateTime
from osis_common.queue import queue_deserializer

class TestQueueDeserializer(TestCase):
    def test_deserialize_with_bad_value(self):
        with self.assertRaises(TypeError):
            queue_deserializer.deserialize(serialized_data="BAD VALUE")

    def test_deserialize_model_with_user(self):
        queue_deserializer.deserialize(serialized_data={
            'to_delete' : False,
            'last_sync' : None,
            'body' : {
                'model' : 'tests.ModelWithUser',
                'fields' : {
                    'user' : 'paulb',
                    'name' : 'paul brullard'
                }
            }
        })
        instance = ModelWithUser.objects.all().first()
        self.assertEqual(1, ModelWithUser.objects.count())
        self.assertEqual(instance.user, "paulb")
        self.assertEqual(instance.name, "paul brullard")

    def test_deserialize_model_with_updated_user(self):
        instance = ModelWithUser.objects.create(user="amard", name="Armar Duilard")
        queue_deserializer.deserialize(serialized_data={
            'to_delete': False,
            'last_sync': None,
            'body': {
                'model': 'tests.ModelWithUser',
                'fields': {
                    'uuid': instance.uuid,
                    'user': 'tarmard',
                    'name': 'Tamard Duilard'
                }
            }
        })
        instance_updated = ModelWithUser.objects.all().first()
        self.assertEqual(1, ModelWithUser.objects.count())
        self.assertEqual(instance_updated.user, "tarmard")
        self.assertEqual(instance_updated.name, "Tamard Duilard")

    def test_deserialize_model_delete_user(self):
        instance = ModelWithUser.objects.create(user="amard", name="Armar Duilard")
        queue_deserializer.deserialize(serialized_data={
            'to_delete': True,
            'last_sync': None,
            'body': {
                'model': 'tests.ModelWithUser',
                'fields': {
                    'uuid': instance.uuid
                }
            }
        })
        self.assertEqual(0, ModelWithUser.objects.count())

    def test_deserialize_model_not_changed_since_last_sync(self):
        instance = ModelWithUser.objects.create(user="amard", name="Armar Duilard")
        queue_deserializer.deserialize(serialized_data={
            'to_delete': False,
            'last_sync': time.mktime(datetime.datetime(2016,1,2).timetuple()),
            'body': {
                'model': 'tests.ModelWithUser',
                'fields': {
                    'uuid': instance.uuid,
                    'user': 'tarmard',
                    'name': 'Tamard Duilard',
                    'changed': time.mktime(datetime.datetime(2016,1,1).timetuple())
                }
            }
        })
        instance_updated = ModelWithUser.objects.all().first()
        self.assertEqual(1, ModelWithUser.objects.count())
        self.assertEqual(instance_updated.user, "amard")
        self.assertEqual(instance_updated.name, "Armar Duilard")