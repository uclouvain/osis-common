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
import datetime
import json
import logging
import uuid
from time import sleep

from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction

from osis_common.queue import queue_sender
from osis_common.utils.inbox_outbox import OneThreadPerBoundedContextRunner, ConsumerThreadWorkerStrategy

logger = logging.getLogger(settings.ASYNC_WORKERS_LOGGER)


class Command(BaseCommand):
    help = """
    Command to start 1 thread/bounded context in order to read events from the queue and store it to the inbox table
    for further processing (via inbox_worker)
    Script must be run in the root of the project
    """

    def handle(self, *args, **options):
        if settings.ASYNC_CONSUMING_STRATEGY == "WITH_BROKER":
            OneThreadPerBoundedContextRunner(BrokerConsumerThreadWorker).run()
        else:
            OneThreadPerBoundedContextRunner(LocalConsumerThreadWorker).run()


class LocalConsumerThreadWorker(ConsumerThreadWorkerStrategy):
    def run(self):
        while True:
            self._execute_unprocessed_events()
            sleep(5)

    def _execute_unprocessed_events(self):
        logger.debug(f"{self._logger_prefix_message()}: Start consuming...")
        with transaction.atomic():
            unprocessed_events = self.outbox_model.objects.select_for_update().filter(
                event_name__in=self.get_interested_events(),
                sent=False,
            ).order_by('creation_date')
            if unprocessed_events:
                logger.debug(f"{self._logger_prefix_message()}: Sending {len(unprocessed_events)} unprocessed events...")

            for unprocessed_event in unprocessed_events:
                self.inbox_model.objects.get_or_create(
                    consumer=self.bounded_context_name,
                    transaction_id=unprocessed_event.transaction_id,
                    defaults={
                        "event_name": unprocessed_event.event_name,
                        "payload": unprocessed_event.payload,
                    }
                )
                unprocessed_event.sent = True
                unprocessed_event.sent_date = datetime.datetime.now()
                unprocessed_event.save()


class BrokerConsumerThreadWorker(ConsumerThreadWorkerStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        consumer_queue_name = f"{self.bounded_context_name}_consumer"
        self.connection = queue_sender.get_connection(client_properties={'connection_name': consumer_queue_name})
        self.channel = self.connection.channel()
        self.channel.queue_declare(
            queue=consumer_queue_name,
            auto_delete=False,
            durable=True
        )

        for interested_event in self.get_interested_events():
            self.channel.queue_bind(
                queue=consumer_queue_name,
                exchange=settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
                routing_key=f"{settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME']}.{interested_event}"
            )

        self.channel.basic_consume(
            self._process_message,
            queue=consumer_queue_name,
            no_ack=False,  # Manual acknowledgement,
            exclusive=True  # Force only one consumer by queue
        )

    def run(self):
        logger.debug(f"{self._logger_prefix_message()}: Start consuming...")
        self.channel.start_consuming()

    def _process_message(self, ch, method_frame, header_frame, body):
        logger.debug(f"{self._logger_prefix_message()}: Process message started...")
        if not header_frame.message_id:
            logger.error(f"{self._logger_prefix_message()}: Missing message_id in header_frame.")
            ch.basic_reject(delivery_tag=method_frame.delivery_tag, requeue=False)
            return

        self.inbox_model.objects.get_or_create(
            consumer=self.bounded_context_name,
            transaction_id=uuid.UUID(header_frame.message_id),
            defaults={
                "event_name": method_frame.routing_key.split('.')[-1],
                "payload": json.loads(body),
            }
        )
        ch.basic_ack(delivery_tag=method_frame.delivery_tag)
        logger.debug(f"{self._logger_prefix_message()}: Process message finished...")
