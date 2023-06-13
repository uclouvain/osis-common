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
from typing import List, Dict

from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Model
from django.utils.module_loading import import_string

from infrastructure.utils import EventHandlers

logger = logging.getLogger(settings.DEFAULT_LOGGER)


class InboxThreadWorker(threading.Thread):
    def __init__(self, consummer_name: str, event_handlers: EventHandlers, inbox_model: Model):
        super().__init__()
        self.consummer_name = consummer_name
        self.event_handlers = event_handlers
        self.inbox_model = inbox_model

    def run(self):
        while True:
            self._execute_unprocessed_events()
            sleep(1)

    def _execute_unprocessed_events(self):
        with transaction.atomic():
            unprocessed_events = self.inbox_model.objects.select_for_update().filter(
                consumer=self.consummer_name,
                completed=False
            ).order_by('creation_date')

            if unprocessed_events:
                logger.info(f"{self._logger_prefix_message()}: Process {len(unprocessed_events)} events...")
            else:
                logger.info(f"{self._logger_prefix_message()}: No unprocessed events...")

            for unprocessed_event in unprocessed_events:
                event_name = unprocessed_event.event_name
                # Start method

    def _logger_prefix_message(self) -> str:
        return f"[Inbox Worker - Thread {self.consummer_name} - Thread: {self.ident} / PID: {os.getpid()} / PPID: {os.getppid()}]"


class Command(BaseCommand):
    help = """
    Command to start 1 thread/bounded context in order to processing reaction according to event
    Script must be run in the root of the project
    """

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.threads = []  # type: List[InboxThreadWorker]
        self._load_inbox_model()

    def handle(self, *args, **options):
        self._retrieve_consummers_and_its_event_handlers()

        for consummer_name, event_handlers in self.consummers_list.items():
            inbox_thread_worker = InboxThreadWorker(consummer_name, event_handlers, self.inbox_model)
            inbox_thread_worker.setDaemon(False)
            inbox_thread_worker.start()
            self.threads.append(inbox_thread_worker)

    def _load_inbox_model(self):
        inbox_model_path = settings.MESSAGE_BUS['INBOX_MODEL']
        self.inbox_model = import_string(inbox_model_path)

    def _retrieve_consummers_and_its_event_handlers(self) -> Dict[str, EventHandlers]:
        self.consummers_list = {}
        handlers_path = glob.glob("infrastructure/*/handlers.py", recursive=True)
        for handler_path in handlers_path:
            with contextlib.suppress(AttributeError):
                handler_module = self.__import_file('handler_module', handler_path)
                if handler_module.EVENT_HANDLERS:
                    bounded_context = os.path.dirname(handler_path).split(os.sep)[-1]
                    self.consummers_list[bounded_context] = handler_module.EVENT_HANDLERS
        return self.consummers_list

    def __import_file(self, full_name, path):
        spec = util.spec_from_file_location(full_name, path)
        mod = util.module_from_spec(spec)

        spec.loader.exec_module(mod)
        return mod
