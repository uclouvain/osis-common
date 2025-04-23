##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2025 Université catholique de Louvain (http://www.uclouvain.be)
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
import uuid
from unittest.mock import patch

import attr
from django.test import TestCase

from osis_common.ddd.interface import Event
from osis_common.models.inbox import Inbox
from osis_common.utils.inbox_outbox import InboxConsumer, DEFAULT_ROUTING_STRATEGY_NAME, InboxConsumerRoutingStrategy
from infrastructure.messages_bus import message_bus_instance


@attr.dataclass(slots=True, frozen=True, kw_only=True)
class DummyEvent(Event):
    entity_id = None
    noma: str


@attr.dataclass(slots=True, frozen=True, kw_only=True)
class AnotherDummyEvent(Event):
    entity_id = None
    sigle_formation: str


class InboxConsumerTestCaseMixin(TestCase):
    def setUp(self):
        self.context_name = 'deliberation'
        self.consumer_id = 0
        self.strategy_name = DEFAULT_ROUTING_STRATEGY_NAME

        self._mock_handlers_per_context()
        self._mock_routing_strategy_factory()

        self.event_A = Inbox.objects.create(
            transaction_id=uuid.uuid4(),
            consumer=self.context_name,
            event_name="DummyEvent",
            payload={
                "entity_id": None,
                "noma": "54545454"
            },
            status=Inbox.PENDING,
        )
        self.event_B = Inbox.objects.create(
            transaction_id=uuid.uuid4(),
            consumer=self.context_name,
            event_name="DummyEvent",
            payload={
                "entity_id": None,
                "noma": "15454545454"
            },
            status=Inbox.PENDING,
        )

    def _mock_handlers_per_context(self):
        patcher_handlers = patch(
            'osis_common.utils.inbox_outbox.HandlersPerContextFactory.get',
            return_value={
                self.context_name: {
                    DummyEvent: [
                        lambda *args, **kwargs: None,
                    ],
                    AnotherDummyEvent : [
                        lambda *args, **kwargs: None,
                    ]
                }
            }
        )
        self.mock_get_handlers = patcher_handlers.start()
        self.addCleanup(patcher_handlers.stop)

    def _mock_routing_strategy_factory(self):
        patcher_routing = patch(
            'osis_common.utils.inbox_outbox.InboxConsumerRoutingStrategyFactory.get'
        )
        self.mock_get_routing = patcher_routing.start()
        self.addCleanup(patcher_routing.stop)


class InboxConsumerDefaultStrategyTestCase(InboxConsumerTestCaseMixin):
    def setUp(self):
        super().setUp()
        # Setup default routing strategy
        self.mock_get_routing.return_value = InboxConsumerRoutingStrategy(context_name=self.context_name)

    def test_consume_all_pending_events_strategy(self):
        consumer = InboxConsumer(
            message_bus_instance=message_bus_instance,
            context_name=self.context_name,
            consumer_id=self.consumer_id,
            strategy_name=self.strategy_name,
        )

        consumer.consume_all_unprocessed_events(batch_size=10)

        self.event_A.refresh_from_db()
        self.assertEqual(self.event_A.status, Inbox.PROCESSED)

        self.event_B.refresh_from_db()
        self.assertEqual(self.event_B.status, Inbox.PROCESSED)

    def test_consume_pending_events_according_to_batch_size(self):
        consumer = InboxConsumer(
            message_bus_instance=message_bus_instance,
            context_name=self.context_name,
            consumer_id=self.consumer_id,
            strategy_name=self.strategy_name,
        )

        consumer.consume_all_unprocessed_events(batch_size=1)

        self.event_A.refresh_from_db()
        self.assertEqual(self.event_A.status, Inbox.PROCESSED)

        self.event_B.refresh_from_db()
        self.assertEqual(self.event_B.status, Inbox.PENDING)

    def test_consumer_all_unprocessed_events_raise_error_if_consumer_id_is_greater_than_0(self):
        with self.assertRaises(ValueError):
            InboxConsumer(
                message_bus_instance=message_bus_instance,
                context_name=self.context_name,
                consumer_id=1,
                strategy_name=self.strategy_name,
            )

    def test_consumer_all_unprocessed_events_raise_error_if_consumer_id_is_less_than_0(self):
        with self.assertRaises(ValueError):
            InboxConsumer(
                message_bus_instance=message_bus_instance,
                context_name=self.context_name,
                consumer_id=-1,
                strategy_name=self.strategy_name,
            )

    def test_consumer_all_unprocessed_events_raise_error_if_start_with_unexisting_strategy_name(self):
        with self.assertRaises(ValueError):
            InboxConsumer(
                message_bus_instance=message_bus_instance,
                context_name=self.context_name,
                consumer_id=self.consumer_id,
                strategy_name='not_existing_strategy_name',
            )


class InboxConsumerCustomStrategyTestCase(InboxConsumerTestCaseMixin):
    def setUp(self):
        super().setUp()
        # Setup custom routing strategy
        self.custom_routing_strategy = InboxConsumerRoutingStrategy(context_name=self.context_name)

        # DummyEvent is managed by a custom routing strategy
        self.custom_routing_strategy.register_strategy(
            strategy_name='noma',
            events_cls=[
                DummyEvent
            ],
            routing_fn=lambda event: event.noma,
            total_consumers=2
        )
        self.mock_get_routing.return_value = self.custom_routing_strategy

        self.event_C = Inbox.objects.create(
            transaction_id=uuid.uuid4(),
            consumer=self.context_name,
            event_name="AnotherDummyEvent",
            payload={
                "entity_id": None,
                "sigle_formation": "DROI1BA"
            },
            status=Inbox.PENDING,
        )
        self.event_D = Inbox.objects.create(
            transaction_id=uuid.uuid4(),
            consumer=self.context_name,
            event_name="AnotherDummyEvent",
            payload={
                "entity_id": None,
                "sigle_formation": "BIR1BA"
            },
            status=Inbox.PENDING,
        )


    def test_default_strategy_must_not_consume_events_outside_his_strategy(self):
        consumer = InboxConsumer(
            message_bus_instance=message_bus_instance,
            context_name=self.context_name,
            consumer_id=self.consumer_id,
            strategy_name=self.strategy_name,
        )

        consumer.consume_all_unprocessed_events(batch_size=10)

        self.event_A.refresh_from_db()
        self.assertEqual(self.event_A.status, Inbox.PENDING, msg="Managed by custom strategy - no consumption")
        self.event_B.refresh_from_db()
        self.assertEqual(self.event_B.status, Inbox.PENDING, msg="Managed by custom strategy - no consumption")

        self.event_C.refresh_from_db()
        self.assertEqual(self.event_C.status, Inbox.PROCESSED, msg="Managed by default strategy - consumption")
        self.event_D.refresh_from_db()
        self.assertEqual(self.event_D.status, Inbox.PROCESSED, msg="Managed by default strategy - consumption")


    def test_custom_strategy_must_consume_events_of_consumer_0(self):
        consumer = InboxConsumer(
            message_bus_instance=message_bus_instance,
            context_name=self.context_name,
            consumer_id=0,  # Consumer 1 of 2
            strategy_name='noma',
        )

        consumer.consume_all_unprocessed_events(batch_size=10)

        self.event_A.refresh_from_db()
        self.assertEqual(
            self.event_A.status,
            Inbox.PENDING,
            msg="Managed by custom strategy but routing_key redirect to consumer 1 - no consumption"
        )
        self.event_B.refresh_from_db()
        self.assertEqual(
            self.event_B.status,
            Inbox.PROCESSED,
            msg="Managed by custom strategy and routing_key redirect to consumer 0 - consumption"
        )

        self.event_C.refresh_from_db()
        self.assertEqual(self.event_C.status, Inbox.PENDING, msg="Managed by default strategy - no consumption")
        self.event_D.refresh_from_db()
        self.assertEqual(self.event_D.status, Inbox.PENDING, msg="Managed by default strategy - no consumption")

    def test_custom_strategy_must_consume_event_of_consumer_1(self):
        consumer = InboxConsumer(
            message_bus_instance=message_bus_instance,
            context_name=self.context_name,
            consumer_id=1,  # Consumer 2 of 2
            strategy_name='noma',
        )

        consumer.consume_all_unprocessed_events(batch_size=10)

        self.event_A.refresh_from_db()
        self.assertEqual(
            self.event_A.status,
            Inbox.PROCESSED,
            msg="Managed by custom strategy and routing_key redirect to consumer 1 - consumption"
        )

        self.event_B.refresh_from_db()
        self.assertEqual(
            self.event_B.status,
            Inbox.PENDING,
            msg="Managed by custom strategy but routing_key redirect to consumer 0 - no consumption"
        )

        self.event_C.refresh_from_db()
        self.assertEqual(self.event_C.status, Inbox.PENDING, msg="Managed by default strategy - no consumption")
        self.event_D.refresh_from_db()
        self.assertEqual(self.event_D.status, Inbox.PENDING, msg="Managed by default strategy - no consumption")

    def test_consumer_all_unprocessed_events_raise_error_if_consumer_id_is_greater_than_total_consumer(self):
        with self.assertRaises(ValueError):
            InboxConsumer(
                message_bus_instance=message_bus_instance,
                context_name=self.context_name,
                consumer_id=10,
                strategy_name='noma',
            )
