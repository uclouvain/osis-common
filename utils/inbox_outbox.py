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
import contextlib
import glob
import logging
import os
import threading
import traceback
import uuid
from decimal import Decimal
from importlib import util
from time import sleep
from typing import List, Dict, Type

import cattr
from django.conf import settings
from django.db import transaction
from django.db.models import Model
from django.utils.module_loading import import_string

from osis_common.ddd.interface.domain_models import EventHandlers

logger = logging.getLogger(settings.ASYNC_WORKERS_LOGGER)

# Converters to serialize / deserialize events payload
cattr.register_structure_hook(uuid.UUID, lambda d, t: d)
cattr.register_structure_hook(Decimal, lambda d, t: d)

MAX_ATTEMPS_BEFORE_DEAD_LETTER = 15
INBOX_BATCH_EVENTS = 5


def _load_inbox_model() -> Model:
    inbox_model_path = settings.MESSAGE_BUS['INBOX_MODEL']
    return import_string(inbox_model_path)


def _load_outbox_model() -> Model:
    inbox_model_path = settings.MESSAGE_BUS['OUTBOX_MODEL']
    return import_string(inbox_model_path)


class ConsumerThreadWorkerStrategy(threading.Thread):
    def __init__(self, bounded_context_name: str, event_handlers: 'EventHandlers'):
        super().__init__()
        self.bounded_context_name = bounded_context_name
        self.event_handlers = event_handlers
        self.inbox_model = _load_inbox_model()
        self.outbox_model = _load_outbox_model()

    def get_interested_events(self) -> List[str]:
        return [event.__name__ for event in self.event_handlers.keys()]

    def _logger_prefix_message(self) -> str:
        return f"[Consumer Worker - {self.bounded_context_name} - Thread: {self.ident}]"


class EventClassNotFound(Exception):
    def __init__(self, event_name: str, **kwargs):
        self.message = f"Cannot process {event_name} events because not found in handlers definition..."
        super().__init__(self.message)


class HandlersPerContextFactory:
    @staticmethod
    def get() -> Dict[str, EventHandlers]:
        consumers_list = {}
        handlers_path = glob.glob("infrastructure/*/handlers.py", recursive=True)
        for handler_path in handlers_path:
            if 'deliberation' in handler_path and 'deliberation' not in settings.INSTALLED_APPS:
                continue
            if (
                'gestion_des_recommandations' in handler_path
                and 'gestion_des_recommandations' not in settings.INSTALLED_APPS
            ):
                continue
            with contextlib.suppress(AttributeError):
                handler_module = HandlersPerContextFactory.__import_file('handler_module', handler_path)
                if handler_module.EVENT_HANDLERS:
                    bounded_context = os.path.dirname(handler_path).split(os.sep)[-1]
                    consumers_list[bounded_context] = handler_module.EVENT_HANDLERS
        return consumers_list

    @staticmethod
    def __import_file(full_name, path):
        spec = util.spec_from_file_location(full_name, path)
        mod = util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


class InboxConsumer:
    def __init__(self, message_bus_instance, context_name: str, event_handlers: 'EventHandlers', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_bus_instance = message_bus_instance
        self.context_name = context_name
        self.event_handlers = event_handlers
        self.inbox_model = _load_inbox_model()

    def consume_all_unprocessed_events(self, batch_size: int = None):
        if batch_size is None:
            batch_size = INBOX_BATCH_EVENTS

        unprocessed_events_qs = self.inbox_model.objects.filter(
            consumer=self.context_name,
        ).exclude(
            status__in=[self.inbox_model.PROCESSED, self.inbox_model.DEAD_LETTER]
        ).order_by('creation_date')

        unprocessed_events_count = unprocessed_events_qs.count()
        if unprocessed_events_count:
            logger.info(f"{self._logger_prefix_message()}: Remaining {unprocessed_events_count} unprocess events...")

            with transaction.atomic():
                unprocessed_events_in_batch = self.inbox_model.objects.select_for_update().filter(
                    pk__in=unprocessed_events_qs.values_list('pk', flat=True)[:batch_size]
                )
                logger.info(f"{self._logger_prefix_message()}: Process {len(unprocessed_events_in_batch)} events...")
                for unprocessed_event in unprocessed_events_in_batch:
                    processed_event = self.consume(unprocessed_event)
                    if not processed_event.is_successfully_processed():
                        if processed_event.attempts_number >= MAX_ATTEMPS_BEFORE_DEAD_LETTER:
                            logger.error(
                                f"{self._logger_prefix_message()}: Mark event as dead letter because max attemps reached "
                                f"(ID: {processed_event.id} - Name {processed_event.event_name})"
                            )
                            processed_event.mark_as_dead_letter()
                        else:
                            logger.warning(
                                f"{self._logger_prefix_message()}: Stop events processing because "
                                f"current event (ID: {processed_event.id} - Name {processed_event.event_name}) "
                                f"not correctly processed..."
                            )
                            break

    def consume(self, unprocessed_event):
        event_instance = None
        event_name = unprocessed_event.event_name
        try:
            event_instance = self.__build_event_instance(unprocessed_event)
            for function in self.event_handlers[event_instance.__class__]:
                function(self.message_bus_instance, event_instance)
            unprocessed_event.mark_as_processed()
        except EventClassNotFound as e:
            logger.warning(e.message)
            unprocessed_event.mark_as_error(e.message)
        except Exception:
            logger.exception(
                f"{self._logger_prefix_message()}: Cannot process {event_name} event ({event_instance})",
                exc_info=True
            )
            unprocessed_event.mark_as_error(traceback.format_exc())
        return unprocessed_event

    def __build_event_instance(self, unprocessed_event: 'Inbox'):
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
        return f"[Inbox Worker - {self.context_name}]"


class OneThreadPerBoundedContextRunner:
    def __init__(self, consumer_thread_worker_strategy: Type[ConsumerThreadWorkerStrategy], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threads = {}  # type: Dict[str, threading.Thread]
        self.consumer_thread_worker_strategy = consumer_thread_worker_strategy
        self.consumers_list = HandlersPerContextFactory().get()

    def run(self):
        for context_name, handlers in self.consumers_list.items():
            self.__start_thread(context_name, handlers)
        while True:
            self.__check_thread_status()
            sleep(5)

    def __check_thread_status(self):
        for context_name, thread in self.threads.items():
            if not thread.is_alive():
                logger.warning(f"| Consumer {context_name} : DOWN |")
                self.__start_thread(context_name, self.consumers_list[context_name])

    def __start_thread(self, context_name: str, handlers: 'EventHandlers'):
        logger.debug(f"| Start Consumer {context_name} ...")
        consumer_thread_worker = self.consumer_thread_worker_strategy(context_name, handlers)
        consumer_thread_worker.setDaemon(True)
        consumer_thread_worker.start()
        self.threads[context_name] = consumer_thread_worker
