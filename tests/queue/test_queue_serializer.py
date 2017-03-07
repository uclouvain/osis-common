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

from osis_common.queue import queue_serializer

class TestQueueSerializer(TestCase):
    def test_serialize_model_with_user(self):
        instance = ModelWithUser.objects.create(user="test", name="test model")
        instance_serialized = queue_serializer.serialize(instance)
        self.assertIsInstance(instance_serialized, dict)
        self.assertEqual(instance_serialized['model'], 'tests.ModelWithUser')
        self.assertIsInstance(instance_serialized['fields'], dict)
        self.assertEqual(instance_serialized['fields']['user'], instance.user)
        self.assertEqual(instance_serialized['fields']['name'], instance.name)
        self.assertIsNotNone(instance_serialized['fields']['uuid'])
        self.assertIsNotNone(instance_serialized['fields']['id'])

    def test_serialize_model_with_date(self):
        instance = ModelWithDate.objects.create(name="test with date", date=datetime.datetime(2015,1,1))
        instance_serialized = queue_serializer.serialize(instance)
        self.assertIsInstance(instance_serialized, dict)
        self.assertEqual(instance_serialized['model'], 'tests.ModelWithDate')
        self.assertIsInstance(instance_serialized['fields'], dict)
        self.assertEqual(instance_serialized['fields']['name'], instance.name)
        self.assertIsInstance(instance_serialized['fields']['date'], float)
        self.assertEqual(instance_serialized['fields']['date'], time.mktime(datetime.datetime(2015,1,1).timetuple()))
        self.assertIsNotNone(instance_serialized['fields']['uuid'])
        self.assertIsNotNone(instance_serialized['fields']['id'])

    def test_serialize_model_with_date_time(self):
        instance = ModelWithDateTime.objects.create(name="test with date", date=datetime.datetime(2015, 1, 1, 5, 5,5))
        instance_serialized = queue_serializer.serialize(instance)
        self.assertIsInstance(instance_serialized, dict)
        self.assertEqual(instance_serialized['model'], 'tests.ModelWithDateTime')
        self.assertIsInstance(instance_serialized['fields'], dict)
        self.assertEqual(instance_serialized['fields']['name'], instance.name)
        self.assertIsInstance(instance_serialized['fields']['date'], float)
        self.assertEqual(instance_serialized['fields']['date'], time.mktime(datetime.datetime(2015, 1, 1, 5, 5, 5)
                                                                                .timetuple()))
        self.assertIsNotNone(instance_serialized['fields']['uuid'])
        self.assertIsNotNone(instance_serialized['fields']['id'])