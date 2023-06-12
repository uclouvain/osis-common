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
from typing import List, Dict

from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Model
from django.utils.module_loading import import_string

from infrastructure.utils import EventHandlers
from osis_common.queue import queue_sender

logger = logging.getLogger(settings.DEFAULT_LOGGER)


class ConsummerThreadWorker(threading.Thread):
    def __init__(self, consummer_name: str, event_handlers: EventHandlers, inbox_model: Model):
        super().__init__()
        self.consummer_name = consummer_name
        self.event_handlers = event_handlers
        self.inbox_model = inbox_model

        consummer_queue_name = f"{self.consummer_name}_consummer"
        self.connection = queue_sender.get_connection(client_properties={'connection_name': consummer_queue_name})
        self.channel = self.connection.channel()
        self.channel.queue_declare(
            consummer_queue_name,
            auto_delete=False,
            durable=True
        )

        for interested_event in self.get_interested_events():
            self.channel.queue_bind(
                consummer_queue_name,
                settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
                routing_key=f"{settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME']}.{interested_event}"
            )
        self.channel.basic_consume(
            self._process_message,
            queue=consummer_queue_name,
            no_ack=False  # Manual acknowledgement
        )

    def run(self):
        logger.info(f"{self._logger_prefix_message()}: Start consuming...")
        self.channel.start_consuming()

    def _process_message(self, ch, method_frame, header_frame, body):
        logger.info(f"{self._logger_prefix_message()}: Process message started...")
        self.inbox_model.objects.create(
            consumer=self.consummer_name,
            event_name=method_frame.routing_key.split('.')[-1],
            transaction_id=header_frame.message_id,
            payload=body,
        )
        logger.info(f"{self._logger_prefix_message()}: Process message finished...")

    def get_interested_events(self) -> List[str]:
        return [event.__name__ for event in self.event_handlers.keys()]

    def _logger_prefix_message(self) -> str:
        return f"[Consummer Worker - Thread {self.consummer_name} - Thread: {self.ident} / PID: {os.getpid()} / PPID: {os.getppid()}]"


class Command(BaseCommand):
    help = """
    Command to start 1 thread/bounded context in order to read events in the queue and store it to the inbox table
    for further processing (via inbox_worker)
    Script must be run in the root of the project
    """

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.threads = []  # type: List[ConsummerThreadWorker]
        self._load_inbox_model()

    def handle(self, *args, **options):
        self._retrieve_consummers_and_its_event_handlers()
        self._initialize_broker_channel()

        for consummer_name, event_handlers in self.consummers_list.items():
            consummer_thread = ConsummerThreadWorker(consummer_name, event_handlers, self.inbox_model)
            consummer_thread.setDaemon(False)
            consummer_thread.start()
            self.threads.append(consummer_thread)

    def _load_inbox_model(self):
        inbox_model_path = settings.MESSAGE_BUS['INBOX_MODEL']
        self.inbox_model = import_string(inbox_model_path)

    def _initialize_broker_channel(self) -> None:
        connection = queue_sender.get_connection()
        channel = connection.channel()
        channel.exchange_declare(
            exchange=settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
            exchange_type='topic',
            passive=False,
            durable=True,
            auto_delete=False
        )
        channel.close()
        connection.close()

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
