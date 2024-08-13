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
from importlib import util
from time import sleep
from typing import List, Dict, Type

from django.conf import settings
from django.db.models import Model
from django.utils.module_loading import import_string

from infrastructure.utils import EventHandlers

logger = logging.getLogger(settings.DEFAULT_LOGGER)


def _load_inbox_model() -> Model:
    inbox_model_path = settings.MESSAGE_BUS['INBOX_MODEL']
    return import_string(inbox_model_path)


def _load_outbox_model() -> Model:
    inbox_model_path = settings.MESSAGE_BUS['OUTBOX_MODEL']
    return import_string(inbox_model_path)


class ConsumerThreadWorkerStrategy(threading.Thread):
    def __init__(self, bounded_context_name: str, event_handlers: EventHandlers):
        super().__init__()
        self.bounded_context_name = bounded_context_name
        self.event_handlers = event_handlers
        self.inbox_model = _load_inbox_model()
        self.outbox_model = _load_outbox_model()

    def get_interested_events(self) -> List[str]:
        return [event.__name__ for event in self.event_handlers.keys()]

    def _logger_prefix_message(self) -> str:
        return f"[Consumer Worker - {self.bounded_context_name} - Thread: {self.ident}]"


class OneThreadPerBoundedContextRunner:
    def __init__(self, consumer_thread_worker_strategy: Type[ConsumerThreadWorkerStrategy], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threads = {}  # type: Dict[str, threading.Thread]
        self.consumer_thread_worker_strategy = consumer_thread_worker_strategy
        self.consumers_list = self.__retrieve_consumers_and_its_event_handlers()  # type: Dict[str, EventHandlers]

    def run(self):
        for consumer_name in self.consumers_list.keys():
            self.__start_thread(consumer_name)
        while True:
            self.__check_thread_status()
            sleep(5)

    def __retrieve_consumers_and_its_event_handlers(self) -> Dict[str, EventHandlers]:
        consumers_list = {}
        handlers_path = glob.glob("infrastructure/*/handlers.py", recursive=True)
        for handler_path in handlers_path:
            with contextlib.suppress(AttributeError):
                handler_module = self.__import_file('handler_module', handler_path)
                if handler_module.EVENT_HANDLERS:
                    bounded_context = os.path.dirname(handler_path).split(os.sep)[-1]
                    consumers_list[bounded_context] = handler_module.EVENT_HANDLERS
        return consumers_list

    def __import_file(self, full_name, path):
        spec = util.spec_from_file_location(full_name, path)
        mod = util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def __check_thread_status(self):
        for consumer_name, thread in self.threads.items():
            if not thread.is_alive():
                logger.warning(f"| Consumer {consumer_name} : DOWN |")
                self.__start_thread(consumer_name)

    def __start_thread(self, consumer_name):
        logger.info(f"| Start Consumer {consumer_name} ...")
        consumer_thread_worker = self.consumer_thread_worker_strategy(
            consumer_name,
            self.consumers_list[consumer_name],
        )
        consumer_thread_worker.setDaemon(True)
        consumer_thread_worker.start()
        self.threads[consumer_name] = consumer_thread_worker
