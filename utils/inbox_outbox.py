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
import contextlib
import datetime
import glob
import json
import logging
import os
import traceback
import uuid
from decimal import Decimal
from importlib import util
from typing import List, Dict

import cattr
import pika
from django.conf import settings
from django.db import transaction
from django.db.models import Model
from django.utils.module_loading import import_string
from opentelemetry import trace, propagate
from opentelemetry.trace import SpanContext, TraceFlags, NonRecordingSpan, Span

from osis_common.ddd.interface import EventHandler, EventConsumptionMode
from osis_common.ddd.interface.domain_models import EventHandlers
from osis_common.queue import queue_sender

logger = logging.getLogger(settings.ASYNC_WORKERS_LOGGER)
tracer = trace.get_tracer(settings.OTEL_TRACER_MODULE_NAME, settings.OTEL_TRACER_LIBRARY_VERSION)

# Converters to serialize / deserialize events payload
cattr.register_structure_hook(uuid.UUID, lambda d, t: d)
cattr.register_structure_hook(Decimal, lambda d, t: d)

MAX_ATTEMPS_BEFORE_DEAD_LETTER = settings.MESSAGE_BUS['INBOX_MAX_RETRIES']
INBOX_BATCH_EVENTS = settings.MESSAGE_BUS['INBOX_BATCH_EVENTS']


def _load_inbox_model() -> Model:
    inbox_model_path = settings.MESSAGE_BUS['INBOX_MODEL']
    return import_string(inbox_model_path)


def _load_outbox_model() -> Model:
    inbox_model_path = settings.MESSAGE_BUS['OUTBOX_MODEL']
    return import_string(inbox_model_path)


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


class EventQueueProducer:
    """
    Class which is in charge to read on outbox model and send it to the rabbitMQ queue
    """
    def __init__(self):
        self.outbox_model = _load_outbox_model()
        self.establish_connection()

    def establish_connection(self):
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

    def send_pending_events_to_queue(self):
        with transaction.atomic():
            unprocessed_events = self.outbox_model.objects.select_for_update().filter(
                sent=False
            ).order_by('creation_date')
            if unprocessed_events:
                logger.info(
                    f"{self.get_logger_prefix_message()}: Sending {len(unprocessed_events)} unprocessed events..."
                )

            for unprocessed_event in unprocessed_events:
                with self._start_as_current_span_from_unprocessed_event(unprocessed_event) as span:
                    span.set_attribute("event.class", unprocessed_event.event_name)
                    span.set_attribute("event.value", json.dumps(unprocessed_event.payload))
                    self._process_unprocessed_event(unprocessed_event)

    def close_connection(self):
        if self.connection:
            self.connection.close()

    def _start_as_current_span_from_unprocessed_event(self, unprocess_event_rowdb):
        otel_data = unprocess_event_rowdb.meta.get('OTEL')
        otel_context = None
        if otel_data and all(key in otel_data for key in ['TRACE_ID', 'SPAN_ID']):
            span_context = SpanContext(
                trace_id=otel_data["TRACE_ID"],
                span_id=otel_data["SPAN_ID"],
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
                is_remote=True
            )
            otel_context = trace.set_span_in_context(NonRecordingSpan(span_context))
        return tracer.start_as_current_span(
            f"outbox_worker.publish.{unprocess_event_rowdb.event_name}",
            context=otel_context
        )

    def _process_unprocessed_event(self, unprocess_event_rowdb):
        headers = {}
        propagate.inject(headers)

        self.channel.basic_publish(
            exchange=settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
            routing_key='.'.join(
                [settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'], unprocess_event_rowdb.event_name]
            ),
            body=json.dumps(unprocess_event_rowdb.payload),
            properties=pika.BasicProperties(
                headers=headers,
                message_id=str(unprocess_event_rowdb.transaction_id),
                content_encoding='utf-8',
                content_type='application/json',
                delivery_mode=2,
            )
        )
        unprocess_event_rowdb.sent = True
        unprocess_event_rowdb.sent_date = datetime.datetime.now()
        unprocess_event_rowdb.save()

    def get_logger_prefix_message(self) -> str:
        return f"[EventQueueProducer]"


class EventQueueConsumer:
    """
    Class which is in charge to read on the rabbitMQ queue and store event to inbox model for a specific
    bounded context
    """
    def __init__(self, context_name: str, event_handlers: 'EventHandlers', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_name = context_name
        self.event_handlers = event_handlers
        self.inbox_model = _load_inbox_model()
        self.establish_connection()

    def establish_connection(self):
        self.connection = queue_sender.get_connection(
            client_properties={'connection_name': self.get_consumer_queue_name()}
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(
            queue=self.get_consumer_queue_name(),
            auto_delete=False,
            durable=True
        )
        for interested_event in self.get_interested_events():
            self.channel.queue_bind(
                queue=self.get_consumer_queue_name(),
                exchange=settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
                routing_key=f"{settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME']}.{interested_event}"
            )

    def get_consumer_queue_name(self) -> str:
        return f"{self.context_name}_consumer"

    def get_interested_events(self) -> List[str]:
        return [event.__name__ for event in self.event_handlers.keys()]

    def get_logger_prefix_message(self) -> str:
        return f"[EventQueueConsumer - {self.context_name}]"

    def read_queue(self):
        logger.debug(f"{self.get_logger_prefix_message()}: Start consuming...")
        method, properties, body = self.channel.basic_get(
            queue=self.get_consumer_queue_name(),
            auto_ack=False,
        )
        if method:
            self._process_message(self.channel, method, properties, body)
        else:
            logger.debug(f"{self.get_logger_prefix_message()}: No message to consume...")

    def _process_message(self, ch, method, properties, body):
        headers = properties.headers if properties and properties.headers else {}
        otel_context = propagate.extract(headers)

        event_name = method.routing_key.split('.')[-1]
        with tracer.start_as_current_span(
            f"{self.context_name}.consumers_worker.process.{event_name}",
            context=otel_context
        ) as span:
            logger.info(f"{self.get_logger_prefix_message()}: Process message started...")
            if not properties.message_id:
                span.set_status(trace.StatusCode.ERROR, "Missing message_id in properties")
                logger.error(f"{self.get_logger_prefix_message()}: Missing message_id in properties.")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

            self.inbox_model.objects.get_or_create(
                consumer=self.context_name,
                transaction_id=uuid.UUID(properties.message_id),
                defaults={
                    "event_name": event_name,
                    "payload": json.loads(body),
                    "meta": {
                        'OTEL': self._get_otel_metadata(span)
                    }
                }
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"{self.get_logger_prefix_message()}: Process message finished...")

    @staticmethod
    def _get_otel_metadata(span: 'Span') -> Dict[str, int]:
        return {
            "TRACE_ID": span.get_span_context().trace_id,
            "SPAN_ID": span.get_span_context().span_id,
        }


class InboxConsumer:
    """
    Class which is in charge to read the event in inbox model and execute event handler function for a specific
    bounded context
    """
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
            status__in=[
                self.inbox_model.PROCESSED,
                self.inbox_model.DEAD_LETTER,
            ]
        ).order_by('creation_date')

        unprocessed_events_count = unprocessed_events_qs.count()
        if unprocessed_events_count:
            logger.info(f"{self.get_logger_prefix_message()}: Remaining {unprocessed_events_count} unprocess events...")

            with transaction.atomic():
                unprocessed_events_in_batch = self.inbox_model.objects.select_for_update().filter(
                    pk__in=unprocessed_events_qs.values_list('pk', flat=True)[:batch_size]
                ).order_by('creation_date')
                logger.info(f"{self.get_logger_prefix_message()}: Process {len(unprocessed_events_in_batch)} events...")
                for unprocessed_event in unprocessed_events_in_batch:
                    with self._start_as_current_span_from_unprocessed_event(unprocessed_event) as span:
                        span.set_attribute("event.class", unprocessed_event.event_name)
                        span.set_attribute("event.value", json.dumps(unprocessed_event.payload))

                        processed_event = self.consume(unprocessed_event)
                        if not processed_event.is_successfully_processed():
                            if processed_event.attempts_number >= MAX_ATTEMPS_BEFORE_DEAD_LETTER:
                                span.set_status(trace.StatusCode.ERROR, "Max attemps retried reached")
                                logger.error(
                                    f"{self.get_logger_prefix_message()}: "
                                    f"Mark event as dead letter because max attemps reached "
                                    f"(ID: {processed_event.id} - Name {processed_event.event_name})"
                                )
                                processed_event.mark_as_dead_letter()
                            else:
                                logger.warning(
                                    f"{self.get_logger_prefix_message()}: Stop events processing because "
                                    f"current event (ID: {processed_event.id} - Name {processed_event.event_name}) "
                                    f"not correctly processed..."
                                )
                                break

    def _start_as_current_span_from_unprocessed_event(self, unprocess_event_rowdb):
        otel_data = unprocess_event_rowdb.meta.get('OTEL')
        otel_context = None
        if otel_data and all(key in otel_data for key in ['TRACE_ID', 'SPAN_ID']):
            span_context = SpanContext(
                trace_id=otel_data["TRACE_ID"],
                span_id=otel_data["SPAN_ID"],
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
                is_remote=True
            )
            otel_context = trace.set_span_in_context(NonRecordingSpan(span_context))
        return tracer.start_as_current_span(
            f"{unprocess_event_rowdb.consumer}.inbox_worker.process.{unprocess_event_rowdb.event_name}",
            context=otel_context
        )

    def consume(self, unprocessed_event):
        event_instance = None
        event_name = unprocessed_event.event_name
        try:
            event_instance = self.__build_event_instance(unprocessed_event)
            event_handlers_declared_as_async = [
                f for f in self.event_handlers[event_instance.__class__]
                if isinstance(f, EventHandler) and f.consumption_mode == EventConsumptionMode.ASYNCHRONOUS
            ]
            for event_handler in event_handlers_declared_as_async:
                event_handler.handle(self.message_bus_instance, event_instance)
            unprocessed_event.mark_as_processed()
        except EventClassNotFound as e:
            logger.warning(e.message)
            # mark as dead letter pour éviter de bloquer le processus de consommation pour une raison autre que métier
            # Si l'event n'est plus dans les handlers, pas nécessaire de réessayer 15 fois (peut-être obsolète)
            unprocessed_event.mark_as_dead_letter('\n'.join(traceback.format_exception(e)))
        except Exception as e:
            logger.exception(
                f"{self.get_logger_prefix_message()}: Cannot process {event_name} event ({event_instance})",
                exc_info=True
            )
            unprocessed_event.mark_as_error('\n'.join(traceback.format_exception(e)))
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

    def get_logger_prefix_message(self) -> str:
        return f"[Inbox Worker - {self.context_name}]"
