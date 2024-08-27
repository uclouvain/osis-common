##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2023 Université catholique de Louvain (http://www.uclouvain.be)
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
import logging
import traceback
import uuid
from decimal import Decimal
from time import sleep

import cattr
from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction

from infrastructure.messages_bus import message_bus_instance
from osis_common.utils.thread import ConsumerThreadWorkerStrategy, OneThreadPerBoundedContextRunner

logger = logging.getLogger(settings.DEFAULT_LOGGER)


cattr.register_structure_hook(uuid.UUID, lambda d, t: d)
cattr.register_structure_hook(Decimal, lambda d, t: d)


class EventClassNotFound(Exception):
    def __init__(self, event_name: str, **kwargs):
        self.message = f"Cannot process {event_name} events because not found in handlers definition..."
        super().__init__(self.message)


class InboxThreadWorker(ConsumerThreadWorkerStrategy):

    def run(self):
        while True:
            self._execute_unprocessed_events()
            sleep(5)

    def _execute_unprocessed_events(self):
        with transaction.atomic():
            unprocessed_events = self.inbox_model.objects.select_for_update().filter(
                consumer=self.bounded_context_name,
                status=self.inbox_model.PENDING
            ).order_by('creation_date')
            if unprocessed_events:
                logger.info(f"{self._logger_prefix_message()}: Process {len(unprocessed_events)} events...")

            for unprocessed_event in unprocessed_events:
                event_instance = None
                event_name = unprocessed_event.event_name
                try:
                    event_instance = self._build_event_instance(unprocessed_event)
                    for function in self.event_handlers[event_instance.__class__]:
                        function(message_bus_instance, event_instance)
                    unprocessed_event.mark_as_processed()
                except EventClassNotFound as e:
                    logger.warning(e.message)
                    unprocessed_event.mark_as_error(e.message)
                    continue
                except Exception:
                    logger.error(
                        f"{self._logger_prefix_message()}: Cannot process {event_name} event ({event_instance})",
                        exc_info=True
                    )
                    unprocessed_event.mark_as_error(traceback.format_exc())
                    continue

    def _build_event_instance(self, unprocessed_event):
        try:
            event_cls = next(
                event_cls for event_cls, fn_list in self.event_handlers.items()
                if event_cls.__name__ == unprocessed_event.event_name
            )
            return cattr.structure({
                'transaction_id': unprocessed_event.transaction_id,
                **unprocessed_event.payload,
            }, event_cls)
        except StopIteration:
            raise EventClassNotFound(unprocessed_event.event_name)

    def _logger_prefix_message(self) -> str:
        return f"[Inbox Worker - {self.bounded_context_name} - Thread: {self.ident}]"


class Command(BaseCommand):
    help = """
    Command to start 1 thread/bounded context in order to processing reaction according to event
    Script must be run in the root of the project
    """

    def handle(self, *args, **options):
        OneThreadPerBoundedContextRunner(InboxThreadWorker).run()
