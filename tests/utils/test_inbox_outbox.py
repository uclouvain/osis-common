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


class InboxConsumerDefaultStrategyTestCase(TestCase):
    def setUp(self):
        self.context_name = 'deliberation'
        self.consumer_id = 0
        self.strategy_name = DEFAULT_ROUTING_STRATEGY_NAME

        self._mock_handlers_per_context()
        self._mock_routing_strategy_factory()

        self.event = Inbox.objects.create(
            transaction_id=uuid.uuid4(),
            consumer=self.context_name,
            event_name="DummyEvent",
            payload={
                "entity_id": None,
                "noma": "12345678"
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
        self.mock_get_routing.return_value = InboxConsumerRoutingStrategy(context_name=self.context_name)

    def test_consume_all_pending_events_strategy(self):
        consumer = InboxConsumer(
            message_bus_instance=message_bus_instance,
            context_name=self.context_name,
            consumer_id=self.consumer_id,
            strategy_name=self.strategy_name,
        )

        consumer.consume_all_unprocessed_events(batch_size=10)

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Inbox.PROCESSED)

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
