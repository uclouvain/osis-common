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
from copy import deepcopy
from unittest.mock import patch

from django.conf import settings
from django.test.testcases import TestCase, override_settings, TransactionTestCase

from osis_common.models import message_queue_cache
from osis_common.models.serializable_model import SerializableModel, serialize, persist, _make_upsert
from osis_common.tests.models_for_tests.serializable_tests_models import ModelWithoutUser, ModelWithUser


class TestSerializeObjectOnCommit(TransactionTestCase):
    def setUp(self):
        self.model_with_user = ModelWithUser(user='user1', name='With User')

    @patch("osis_common.models.serializable_model.serializable_model_post_save", side_effect=None)
    def test_save(self, mock_post_save):
        self.model_with_user.save()
        self.assertTrue(mock_post_save.called)
        mock_post_save.assert_called_once_with(self.model_with_user)

    @patch("osis_common.models.serializable_model.serializable_model_post_delete", side_effect=None)
    def test_delete(self, mock_post_delete):
        self.model_with_user.save()
        self.model_with_user.delete()
        self.assertTrue(mock_post_delete.called)
        mock_post_delete.assert_called_once_with(self.model_with_user, to_delete=True)


if hasattr(settings, 'QUEUES') and settings.QUEUES:
    class TestMessageQueueCache(TransactionTestCase):
        def test_message_queue_cache_no_insert(self):
            ModelWithoutUser.objects.create(name='Dummy')
            message_queued = message_queue_cache.get_messages_to_retry()
            self.assertEqual(0, message_queued.count())

        def test_message_queue_cache_insert(self):
            queue_settings = deepcopy(settings.QUEUES)
            queue_settings['QUEUE_URL'] = "dummy-url"
            with override_settings(QUEUES=queue_settings):
                ModelWithoutUser.objects.create(name='Dummy')
                message_queued = message_queue_cache.get_messages_to_retry()
                self.assertEqual(1, message_queued.count())

        def test_message_queue_cache_order(self):
            queue_settings = deepcopy(settings.QUEUES)
            queue_settings['QUEUE_URL'] = "dummy-url"
            with override_settings(QUEUES=queue_settings):
                user_1 = ModelWithoutUser.objects.create(name='user_1')
                ModelWithoutUser.objects.create(name='user_2')
                user_3 = ModelWithoutUser.objects.create(name='user_3')
                message_queued = message_queue_cache.get_messages_to_retry()
                self.assertEqual(3, message_queued.count())
                first_message = message_queued.first().data['body']['fields']
                latest_message = message_queued.last().data['body']['fields']
                self.assertEqual(user_1.id, first_message.get('id'))
                self.assertEqual(str(user_1.uuid), first_message.get('uuid'))
                self.assertEqual(user_3.id, latest_message.get('id'))
                self.assertEqual(str(user_3.uuid), latest_message.get('uuid'))

        def test_save_after_send_message_queue_cache(self):
            queue_name = settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_PRODUCE')
            queue_settings = deepcopy(settings.QUEUES)
            queue_settings['QUEUE_URL'] = "dummy-url"
            with override_settings(QUEUES=queue_settings):
                # Seed message queue cache database
                message_queue_cache.MessageQueueCache.objects.create(queue=queue_name, data={'test': True})
                message_queue_cache.MessageQueueCache.objects.create(queue=queue_name, data={'test_2': True})
                message_queue_cache.MessageQueueCache.objects.create(queue=queue_name, data={'test_3': True})
                # Create Model
                ModelWithoutUser.objects.create(name='Dummy')
                self.assertEqual(4, message_queue_cache.get_messages_to_retry().count())

        def test_save_after_send_message_queue_cache_with_body(self):
            queue_name = settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_PRODUCE')
            # Seed message queue cache database
            message_queue_cache.MessageQueueCache.objects.create(queue=queue_name, data={'body':{'model': 'test_1', 'fields': {'test': True}}})
            message_queue_cache.MessageQueueCache.objects.create(queue=queue_name, data={'body':{'model': 'test_2', 'fields': {'test': True}}})
            message_queue_cache.MessageQueueCache.objects.create(queue=queue_name, data={'body':{'model': 'test_3', 'fields': {'test': True}}})
            self.assertEqual(3, message_queue_cache.get_messages_to_retry().count())
            # Create Model
            ModelWithoutUser.objects.create(name='Dummy')
            self.assertEqual(0, message_queue_cache.get_messages_to_retry().count())


class TestPersist(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.model_with_user = ModelWithUser(user='user1', name='With User')

    @patch("osis_common.models.serializable_model._make_upsert", side_effect=None)
    def test_persist_case_insert_new_one(self, mock_make_upsert):
        structure_serialized = serialize(self.model_with_user, to_delete=False)
        persist(structure_serialized)
        mock_make_upsert.assert_called_once_with(
            structure_serialized['fields'],
            SerializableModel,
            ModelWithUser
        )

    @patch("osis_common.models.serializable_model._make_upsert", side_effect=None)
    def test_persist_case_update_existing(self, mock_make_upsert):
        # Save instance in order to have UUID on database
        self.model_with_user.save()

        structure_serialized = serialize(self.model_with_user, to_delete=False)
        persist(structure_serialized)
        mock_make_upsert.assert_called_once_with(
            structure_serialized['fields'],
            SerializableModel,
            ModelWithUser,
            instance=self.model_with_user
        )


class TestMakeUpsert(TestCase):
    def test_make_upsert_case_insert(self):
        obj = ModelWithUser(user='user1', name='With User')

        structure_serialized = serialize(obj, to_delete=False)
        pk = _make_upsert(
            structure_serialized['fields'],
            SerializableModel,
            ModelWithUser
        )
        self.assertTrue(pk)
        self.assertTrue(
            ModelWithUser.objects.filter(pk=pk, user='user1', name='With User').exists()
        )

    def test_make_upsert_case_update(self):
        obj = ModelWithUser(user='user1', name='With User')
        obj.save()

        structure_serialized = serialize(obj, to_delete=False)
        structure_serialized['fields']['name'] = "Update name"
        _make_upsert(
            structure_serialized['fields'],
            SerializableModel,
            ModelWithUser,
            instance=obj
        )

        obj.refresh_from_db()
        self.assertTrue(obj.pk)
        self.assertEqual(obj.name, "Update name")
