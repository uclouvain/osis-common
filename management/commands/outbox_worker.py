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
import datetime
import logging
import json
import os

import pika

from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.module_loading import import_string

from osis_common.queue import queue_sender

logger = logging.getLogger(settings.DEFAULT_LOGGER)


class Command(BaseCommand):
    help = """
    Command to send events (aka. message_bus_instance.apublish) produce by the application to the message broker
    Script must be run in the root of the project
    """

    def handle(self, *args, **options):
        self._load_outbox_model()
        self._initialize_broker_channel()

        while True:
            self._send_unprocessed_events()
            self.connection.sleep(1)

    def _send_unprocessed_events(self):
        with transaction.atomic():
            unprocessed_events = self.outbox_model.objects.select_for_update().filter(sent=False)
            if unprocessed_events:
                logger.info(f"{self._logger_prefix_message()}: Sending {len(unprocessed_events)} unprocessed events...")
            else:
                logger.info(f"{self._logger_prefix_message()}: No unprocessed events...")

            for unprocessed_event in unprocessed_events:
                self.channel.basic_publish(
                    exchange=settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
                    routing_key='.'.join(
                        [settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'], unprocessed_event.event_name]
                    ),
                    body=json.dumps(unprocessed_event.payload),
                    properties=pika.BasicProperties(
                        message_id=str(unprocessed_event.transaction_id),
                        content_encoding='utf-8',
                        content_type='application/json',
                        delivery_mode=2,
                    )
                )
                unprocessed_event.sent = True
                unprocessed_event.sent_date = datetime.datetime.now()
                unprocessed_event.save()

    def _initialize_broker_channel(self):
        self.connection = queue_sender.get_connection(client_properties={'connection_name': 'outbox_worker'})
        channel = self.connection.channel()

        channel.exchange_declare(
            exchange=settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
            exchange_type='topic',
            passive=False,
            durable=True,
            auto_delete=False
        )
        channel.confirm_delivery()
        self.channel = channel

    def _load_outbox_model(self):
        outbox_model_path = settings.MESSAGE_BUS['OUTBOX_MODEL']
        self.outbox_model = import_string(outbox_model_path)

    def _logger_prefix_message(self) -> str:
        return f"[Outbox Worker thread - PID: {os.getpid()} / PPID: {os.getppid()}]"
