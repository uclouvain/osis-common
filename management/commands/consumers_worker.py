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
import json
import logging
import os
import threading
import uuid
from importlib import util
from time import sleep
from typing import List, Dict

from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Model
from django.utils.module_loading import import_string

from infrastructure.utils import EventHandlers
from osis_common.queue import queue_sender

logger = logging.getLogger(settings.DEFAULT_LOGGER)


class ConsumerThreadWorker(threading.Thread):
    def __init__(self, consumer_name: str, event_handlers: EventHandlers, inbox_model: Model):
        super().__init__()
        self.consumer_name = consumer_name
        self.event_handlers = event_handlers
        self.inbox_model = inbox_model

        consumer_queue_name = f"{self.consumer_name}_consumer"
        self.connection = queue_sender.get_connection(client_properties={'connection_name': consumer_queue_name})
        self.channel = self.connection.channel()
        self.channel.queue_declare(
            consumer_queue_name,
            auto_delete=False,
            durable=True
        )

        for interested_event in self.get_interested_events():
            self.channel.queue_bind(
                consumer_queue_name,
                settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
                routing_key=f"{settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME']}.{interested_event}"
            )
        self.channel.basic_consume(
            self._process_message,
            queue=consumer_queue_name,
            no_ack=False,  # Manual acknowledgement,
            exclusive=True  # Force only one consumer by queue
        )

    def run(self):
        logger.info(f"{self._logger_prefix_message()}: Start consuming...")
        self.channel.start_consuming()

    def _process_message(self, ch, method_frame, header_frame, body):
        logger.info(f"{self._logger_prefix_message()}: Process message started...")
        if not header_frame.message_id:
            logger.warning(f"{self._logger_prefix_message()}: Missing message_id in header_frame.")
            ch.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
            return

        self.inbox_model.objects.get_or_create(
            consumer=self.consumer_name,
            transaction_id=uuid.UUID(header_frame.message_id),
            defaults={
                "event_name": method_frame.routing_key.split('.')[-1],
                "payload": json.loads(body),
            }
        )
        ch.basic_ack(delivery_tag=method_frame.delivery_tag)
        logger.info(f"{self._logger_prefix_message()}: Process message finished...")

    def get_interested_events(self) -> List[str]:
        return [event.__name__ for event in self.event_handlers.keys()]

    def _logger_prefix_message(self) -> str:
        return f"[Consumer Worker - {self.consumer_name} - Thread: {self.ident}]"


class Command(BaseCommand):
    help = """
    Command to start 1 thread/bounded context in order to read events from the queue and store it to the inbox table
    for further processing (via inbox_worker)
    Script must be run in the root of the project
    """

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.threads = {}  # type: Dict[str, ConsumerThreadWorker]
        self._load_inbox_model()

    def handle(self, *args, **options):
        self._retrieve_consumers_and_its_event_handlers()
        self._initialize_broker_channel()

        for consumer_name, event_handlers in self.consumers_list.items():
            consumer_thread = ConsumerThreadWorker(consumer_name, event_handlers, self.inbox_model)
            consumer_thread.setDaemon(False)
            consumer_thread.start()
            self.threads[consumer_name] = consumer_thread

        while True:
            self.__display_thread_status()
            sleep(30)

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

    def _retrieve_consumers_and_its_event_handlers(self) -> Dict[str, EventHandlers]:
        self.consumers_list = {}
        handlers_path = glob.glob("infrastructure/*/handlers.py", recursive=True)
        for handler_path in handlers_path:
            with contextlib.suppress(AttributeError):
                handler_module = self.__import_file('handler_module', handler_path)
                if handler_module.EVENT_HANDLERS:
                    bounded_context = os.path.dirname(handler_path).split(os.sep)[-1]
                    self.consumers_list[bounded_context] = handler_module.EVENT_HANDLERS
        return self.consumers_list

    def __import_file(self, full_name, path):
        spec = util.spec_from_file_location(full_name, path)
        mod = util.module_from_spec(spec)

        spec.loader.exec_module(mod)
        return mod

    def __display_thread_status(self):
        logger.info("********** [THREAD STATUS] ************")
        for consumer_name, thread in self.threads.items():
            logger.info(f"| Consumer {consumer_name} : {thread.is_alive()} |")
        logger.info("***********************************")
