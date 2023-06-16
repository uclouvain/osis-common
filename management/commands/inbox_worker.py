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
from importlib import util
from time import sleep
from typing import Dict

import cattr
from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Model
from django.utils.module_loading import import_string

from infrastructure.messages_bus import message_bus_instance
from infrastructure.utils import EventHandlers

logger = logging.getLogger(settings.DEFAULT_LOGGER)


cattr.register_structure_hook(uuid.UUID, lambda d, t: d)


class EventClassNotFound(Exception):
    def __init__(self, event_name: str, **kwargs):
        self.message = f"Cannot process {event_name} events because not found in handlers definition..."
        super().__init__(self.message)


class InboxThreadWorker(threading.Thread):
    def __init__(self, consumer_name: str, event_handlers: EventHandlers, inbox_model: Model):
        super().__init__()
        self.consumer_name = consumer_name
        self.event_handlers = event_handlers
        self.inbox_model = inbox_model

    def run(self):
        while True:
            self._execute_unprocessed_events()
            sleep(2)

    def _execute_unprocessed_events(self):
        with transaction.atomic():
            unprocessed_events = self.inbox_model.objects.select_for_update().filter(
                consumer=self.consumer_name,
                status=self.inbox_model.PENDING
            ).order_by('creation_date')
            if unprocessed_events:
                logger.info(f"{self._logger_prefix_message()}: Process {len(unprocessed_events)} events...")

            for unprocessed_event in unprocessed_events:
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
                **unprocessed_event.payload,
                'transaction_id': unprocessed_event.transaction_id
            }, event_cls)
        except StopIteration:
            raise EventClassNotFound(unprocessed_event.event_name)

    def _logger_prefix_message(self) -> str:
        return f"[Inbox Worker - {self.consumer_name} - Thread: {self.ident}]"


class Command(BaseCommand):
    help = """
    Command to start 1 thread/bounded context in order to processing reaction according to event
    Script must be run in the root of the project
    """

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.threads = {}  # type: Dict[str, InboxThreadWorker]
        self.__load_inbox_model()
        self.__retrieve_consumers_and_its_event_handlers()

    def handle(self, *args, **options):
        for consumer_name in self.consumers_list.keys():
            self.__start_thread(consumer_name)

        while True:
            self.__check_thread_status()
            sleep(2)

    def __load_inbox_model(self):
        inbox_model_path = settings.MESSAGE_BUS['INBOX_MODEL']
        self.inbox_model = import_string(inbox_model_path)

    def __retrieve_consumers_and_its_event_handlers(self):
        self.consumers_list = {}
        handlers_path = glob.glob("infrastructure/*/handlers.py", recursive=True)
        for handler_path in handlers_path:
            with contextlib.suppress(AttributeError):
                handler_module = self.__import_file('handler_module', handler_path)
                if handler_module.EVENT_HANDLERS:
                    bounded_context = os.path.dirname(handler_path).split(os.sep)[-1]
                    self.consumers_list[bounded_context] = handler_module.EVENT_HANDLERS

    def __import_file(self, full_name, path):
        spec = util.spec_from_file_location(full_name, path)
        mod = util.module_from_spec(spec)

        spec.loader.exec_module(mod)
        return mod

    def __check_thread_status(self):
        logger.info("********** [THREAD STATUS] ************")
        for consumer_name, thread in self.threads.items():
            if not thread.is_alive():
                logger.warning(f"| Consumer {consumer_name} : DOWN |")
                self.__start_thread(consumer_name)
            else:
                logger.info(f"| Consumer {consumer_name} : OK |")
        logger.info("***********************************")

    def __start_thread(self, consumer_name):
        logger.info(f"| Start Consumer {consumer_name} ...")
        inbox_thread_worker = InboxThreadWorker(consumer_name, self.consumers_list[consumer_name], self.inbox_model)
        inbox_thread_worker.setDaemon(True)
        inbox_thread_worker.start()
        self.threads[consumer_name] = inbox_thread_worker
