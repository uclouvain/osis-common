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
import hashlib
import importlib
import json
import logging
import os
import traceback
import uuid
from decimal import Decimal
from importlib import util
from typing import List, Dict, Type, Callable, Optional

import cattr
import pika
import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Model
from django.utils.module_loading import import_string
from opentelemetry import trace, propagate
from opentelemetry.trace import SpanContext, TraceFlags, NonRecordingSpan, Span

from osis_common.ddd import interface
from osis_common.ddd.interface import EventHandler, EventConsumptionMode
from osis_common.ddd.interface.domain_models import EventHandlers, Event
from osis_common.queue import queue_sender

logger = logging.getLogger(settings.ASYNC_WORKERS_LOGGER)
tracer = trace.get_tracer(settings.OTEL_TRACER_MODULE_NAME, settings.OTEL_TRACER_LIBRARY_VERSION)

# Converters to serialize / deserialize events payload
cattr.register_structure_hook(uuid.UUID, lambda value, klass: uuid.UUID(value))
cattr.register_structure_hook(Decimal, lambda value, klass: Decimal(value))
cattr.register_structure_hook(interface.EntityIdentity, lambda value, klass: klass.deserialize(value))
cattr.register_structure_hook(
    datetime.datetime,
    lambda value, klass: datetime.datetime.strptime(value, settings.EVENT_DATETIME_FORMAT)
)
cattr.register_structure_hook(
    datetime.date,
    lambda value, klass: datetime.datetime.strptime(value, settings.EVENT_DATE_FORMAT).date()
)
DEFAULT_ROUTING_STRATEGY_NAME = 'default'


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
        # TODO repositionner sur la racine d'Osis
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


class InboxConsumerRoutingStrategyFactory:
    @staticmethod
    def get(context_name: str) -> 'InboxConsumerRoutingStrategy':
        routing_module_path = f"infrastructure.{context_name}.inbox_consumer_routing"
        try:
            routing_module = importlib.import_module(routing_module_path)
            routing_strategy = routing_module.get()
            log_msg = f"Custom routing strategy found for {context_name}"
            logger.info(f"{log_msg} ({routing_module_path})")
        except (ImportError, AttributeError) as e:
            routing_strategy = InboxConsumerRoutingStrategy(context_name=context_name)
            log_msg = f"No custom routing strategy for {context_name}, using fallback '{DEFAULT_ROUTING_STRATEGY_NAME}'"
            logger.info(f"{log_msg} ({routing_module_path})")
        return routing_strategy


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
        headers = {
            'event_name_hash': unprocess_event_rowdb.meta.get('EVENT_NAME_HASH'),
        }
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
    def __init__(self, context_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_name = context_name
        self.event_handlers = HandlersPerContextFactory.get()[self.context_name]
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
                routing_key=self.get_routing_key(interested_event)
            )

    def get_routing_key(self, event_name: str):
        return f"{settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME']}.{event_name}"

    def clear_uninterested_events(self) -> None:
        """
        This function will remove bindings (= eventname) which are not used anymore
        Pika doesn't provided a function, we need to call API manager
        """
        logger.info(f"{self.get_logger_prefix_message()}: Starting clear uninterested events")
        self.establish_connection()

        VHOST = settings.QUEUES.get('QUEUE_CONTEXT_ROOT')
        if VHOST == '/':
            VHOST='%2F'

        url = f"{settings.QUEUES.get('API_MANAGEMENT_URL')}/bindings/{VHOST}/e/" \
              f"{settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME']}/q/{self.get_consumer_queue_name()}"
        response = requests.get(
            url, auth=(
                settings.QUEUES.get('QUEUE_USER'),
                settings.QUEUES.get('QUEUE_PASSWORD')
            )
        )
        if response.status_code != 200:
            logger.error(
                f"{self.get_logger_prefix_message()}: Erreur lors de la récupération des bindings "
                f"(URL: {url} / Result: f{response.text})"
            )
            return

        bindings_current = [binding["routing_key"] for binding in response.json()]
        bindings_to_keep = [self.get_routing_key(interested_event) for interested_event in self.get_interested_events()]
        for routing_key in bindings_current:
            if routing_key not in bindings_to_keep:
                logger.info(f"{self.get_logger_prefix_message()}: Suppression du binding: {routing_key}")
                self.channel.queue_unbind(
                    queue=self.get_consumer_queue_name(),
                    exchange=settings.MESSAGE_BUS['ROOT_TOPIC_EXCHANGE_NAME'],
                    routing_key=routing_key
                )

    def get_consumer_queue_name(self) -> str:
        return f"{self.context_name}_consumer"

    def get_interested_events(self) -> List[str]:
        return [event.__name__ for event in self.event_handlers.keys()]

    def get_logger_prefix_message(self) -> str:
        return f"[EventQueueConsumer - {self.context_name}]"

    def read_queue(self, batch_size=None):
        if batch_size is None:
            batch_size = settings.MESSAGE_BUS['CONSUMER_BATCH_SIZE']

        logger.debug(f"{self.get_logger_prefix_message()}: Start consuming (batch_size={batch_size})...")
        current_message_count = 0
        while current_message_count < batch_size:
            method, properties, body = self.channel.basic_get(
                queue=self.get_consumer_queue_name(),
                auto_ack=False,
            )
            if method:
                is_message_processed_with_success = self._process_message(self.channel, method, properties, body)
                if not is_message_processed_with_success:
                    break
            else:
                logger.debug(f"{self.get_logger_prefix_message()}: No message to consume...")
                break
            current_message_count += 1

    def _process_message(self, ch, method, properties, body) -> bool:
        logger.info(f"{self.get_logger_prefix_message()}: Process message started...")
        headers = properties.headers if properties and properties.headers else {}
        event_name = method.routing_key.split('.')[-1]

        otel_context = propagate.extract(headers)
        with tracer.start_as_current_span(
            f"{self.context_name}.consumers_worker.process.{event_name}",
            context=otel_context
        ) as span:
            if not self._is_event_name_hash_valid(event_name, headers):
                logger.info(
                    f"{self.get_logger_prefix_message()}: Discard event {event_name} because invalid event name hash..."
                )
            elif not self._have_at_least_one_event_declared_async(event_name):
                logger.info(
                    f"{self.get_logger_prefix_message()}: "
                    f"Discard event {event_name} because no async action in context {self.context_name}..."
                )
            elif not properties.message_id:
                span.set_status(trace.StatusCode.ERROR, "Missing message_id in properties")
                logger.error(f"{self.get_logger_prefix_message()}: Missing message_id in properties.")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return False
            else:
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
            return True

    def _have_at_least_one_event_declared_async(self, event_name: str) -> bool:
        event_class = next(
            (cls for cls in self.event_handlers if cls.__name__ == event_name),
            None
        )
        if event_class is None:
            return False

        async_handlers = [
            handler for handler in self.event_handlers[event_class]
            if isinstance(handler, EventHandler) and handler.consumption_mode == EventConsumptionMode.ASYNCHRONOUS
        ]
        return bool(async_handlers)

    def _is_event_name_hash_valid(self, event_name: str, headers: Dict) -> bool:
        event_class = next(
            (cls for cls in self.event_handlers if cls.__name__ == event_name),
            None
        )
        if event_class is None:
            return False

        hasher = hashlib.new('sha256')
        hasher.update(str(event_class.__module__).encode('utf-8'))
        return hasher.hexdigest() == headers.get('event_name_hash')


    @staticmethod
    def _get_otel_metadata(span: 'Span') -> Dict[str, int]:
        return {
            "TRACE_ID": span.get_span_context().trace_id,
            "SPAN_ID": span.get_span_context().span_id,
        }


class InboxConsumer:
    """
    Consume events from the Inbox model for a specific bounded context.

    This class dynamically loads a routing strategy, filters events according to the strategy and consumer ID,
    and dispatches them to the appropriate asynchronous event handlers.
    """
    def __init__(
        self,
        message_bus_instance,
        context_name: str,
        consumer_id: int = 0,
        strategy_name: str = DEFAULT_ROUTING_STRATEGY_NAME,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.message_bus_instance = message_bus_instance
        self.context_name = context_name
        self.strategy_name = strategy_name
        self.consumer_id = consumer_id
        self.routing_strategy = InboxConsumerRoutingStrategyFactory.get(context_name=self.context_name)
        self.event_handlers = HandlersPerContextFactory.get()[self.context_name]
        self.inbox_model = _load_inbox_model()
        self._validate_configuration()

    def _validate_configuration(self):
        if self.strategy_name not in self.routing_strategy.strategies:
            raise ValueError(
                f"Strategy '{self.strategy_name}' is not registered for context '{self.context_name}'."
            )

        strategy = self.routing_strategy.strategies[self.strategy_name]
        if self.consumer_id < 0:
            raise ValueError("consumer_id must be greater than or equal to 0")

        if self.consumer_id >= strategy.total_consumers:
            raise ValueError(
                f"Consumer ID {self.consumer_id} is out of bounds for strategy '{self.strategy_name}' "
                f"(total consumers: {strategy.total_consumers} - start at 0)."
            )

    def consume_all_unprocessed_events(self, batch_size: int = None):
        if batch_size is None:
            batch_size = settings.MESSAGE_BUS['INBOX_BATCH_EVENTS']

        unprocessed_events_ids = self.get_unprocessed_events_ids(batch_size=batch_size)
        logger.info(
            f"{self.get_logger_prefix_message()}: Found {len(unprocessed_events_ids)} "
            f"events matching strategy and consumer"
        )
        if len(unprocessed_events_ids):
            failed_event = None
            try:
                with transaction.atomic():
                    unprocessed_events_in_batch = self.inbox_model.objects.select_for_update().filter(
                        pk__in=unprocessed_events_ids
                    ).order_by('creation_date')

                    logger.info(f"{self.get_logger_prefix_message()}: Process {len(unprocessed_events_in_batch)} events...")
                    for unprocessed_event in unprocessed_events_in_batch:
                        with self._start_as_current_span_from_unprocessed_event(unprocessed_event) as span:
                            span.set_attribute("event.class", unprocessed_event.event_name)
                            span.set_attribute("event.value", json.dumps(unprocessed_event.payload))
                            span.set_attribute("inbox_consumer.strategy_name", self.strategy_name)
                            span.set_attribute("inbox_consumer.consumer_id", self.consumer_id)

                            try:
                                self.consume(unprocessed_event)
                            except Exception as e:
                                span.set_status(trace.StatusCode.ERROR, str(e))
                                logger.exception(
                                    f"{self.get_logger_prefix_message()}: "
                                    f"Exception raised while consuming event (ID: {unprocessed_event.id})"
                                )
                                failed_event = unprocessed_event
                                raise   # Trigger rollback
            except Exception as e:
                logger.warning(f"{self.get_logger_prefix_message()}: Transaction rollbacked due to an exception.")
                if failed_event:
                    if failed_event.attempts_number >= settings.MESSAGE_BUS['INBOX_MAX_RETRIES']:
                        logger.error(
                            f"{self.get_logger_prefix_message()}: "
                            f"Mark event as dead letter because max attempts reached "
                            f"(ID: {failed_event.id} - Name {failed_event.event_name})"
                        )
                        failed_event.mark_as_dead_letter('\n'.join(traceback.format_exception(e)))
                    else:
                        failed_event.mark_as_error('\n'.join(traceback.format_exception(e)))

    def get_unprocessed_events_ids(self, batch_size: int) -> List[int]:
        """
        Return a list of unprocessed events id of the current strategy routing and current consumer
        order by creation date
        """
        # Step 1 : Filter to routing strategy
        unprocessed_events_qs = self.inbox_model.objects.filter(
            consumer=self.context_name,
        ).exclude(
            status__in=[
                self.inbox_model.PROCESSED,
                self.inbox_model.DEAD_LETTER,
            ]
        )
        if self.strategy_name == DEFAULT_ROUTING_STRATEGY_NAME:
            # Exclude events which are declared in other strategies because default strategy doesn't required
            # event registration
            unprocessed_events_qs = unprocessed_events_qs.exclude(
                event_name__in=self.routing_strategy.get_all_handled_event_names()
            )
            delta_event = 1
        else:
            # Filter only on event which are declared in current strategy
            unprocessed_events_qs = unprocessed_events_qs.filter(
                event_name__in=self.routing_strategy.handled_event_names(strategy_name=self.strategy_name)
            )
            delta_event = self.routing_strategy.strategies[self.strategy_name].total_consumers
        unprocessed_events_qs = unprocessed_events_qs.order_by('creation_date')

        # Step 2 : Filter to consumer ID
        # /!\ Take more data than batch size (* delta_event) because, we filter in memory according to routing_key
        unprocessed_events_of_current_strategy = list(unprocessed_events_qs[:batch_size * delta_event])
        unprocessed_events_of_current_consumer = []
        for unprocessed_event in unprocessed_events_of_current_strategy:
            event_instance = self._build_event_instance(unprocessed_event)
            if not event_instance:
                continue
            if self.routing_strategy.should_process(event_instance, self.consumer_id):
                unprocessed_events_of_current_consumer.append(unprocessed_event.pk)
            if len(unprocessed_events_of_current_consumer) >= batch_size:
                break
        return unprocessed_events_of_current_consumer

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
        event_instance = self._build_event_instance(unprocessed_event)
        if event_instance:
            event_handlers_declared_as_async = [
                f for f in self.event_handlers[event_instance.__class__]
                if isinstance(f, EventHandler) and f.consumption_mode == EventConsumptionMode.ASYNCHRONOUS
            ]
            for event_handler in event_handlers_declared_as_async:
                event_handler.handle(self.message_bus_instance, event_instance)
            unprocessed_event.mark_as_processed(strategy_name=self.strategy_name, consumer_id=self.consumer_id)
        return unprocessed_event

    def _build_event_instance(self, unprocessed_event: 'Inbox') -> Optional['Event']:
        try:
            return self._deserialize_event(unprocessed_event)
        except (StopIteration, EventClassNotFound):
            # mark as dead letter pour éviter de bloquer le processus de consommation pour une raison autre que métier
            # Si l'event n'est plus dans les handlers, pas nécessaire de réessayer
            exception = EventClassNotFound(unprocessed_event.event_name)
            unprocessed_event.mark_as_dead_letter('\n'.join(traceback.format_exception(exception)))
        except Exception as e:
            unprocessed_event.mark_as_error('\n'.join(traceback.format_exception(e)))

    def _deserialize_event(self, unprocessed_event):
        event_cls = next(
            event_cls for event_cls, fn_list in self.event_handlers.items()
            if event_cls.__name__ == unprocessed_event.event_name
        )
        return event_cls.deserialize(
            {
                'transaction_id': str(unprocessed_event.transaction_id),
                **unprocessed_event.payload,
            }
        )

    def get_logger_prefix_message(self) -> str:
        return f"[Inbox Worker - {self.context_name} - " \
               f"Routing Strategy name: {self.strategy_name} - Consumer ID: {str(self.consumer_id)}]"


class RoutingStrategy:
    def __init__(self, name: str, total_consumers: int = 1):
        self.name = name
        self.total_consumers = total_consumers
        self.event_routing_functions: Dict[Type[Event], Callable[[Event], str]] = {}

    def register(self, event_cls: Type[Event], routing_fn: Callable[[Event], str]):
        if event_cls in self.event_routing_functions:
            raise ValueError(f"{event_cls.__name__} already registered in strategy '{self.name}'")
        self.event_routing_functions[event_cls] = routing_fn

    def can_handle(self, event_instance: Event) -> bool:
        return type(event_instance) in self.event_routing_functions

    def get_routing_key(self, event_instance: Event) -> str:
        event_cls = type(event_instance)
        if event_cls not in self.event_routing_functions:
            raise ValueError(f"Strategy '{self.name}' cannot handle event class {event_cls.__name__}")
        raw_key = self.event_routing_functions[event_cls](event_instance)
        return f"{self.name}:{raw_key}"

    def get_handled_event_names(self) -> List[str]:
        return [event_cls.__name__ for event_cls in self.event_routing_functions]

    def should_process(self, event_instance: Event, consumer_id: int) -> bool:
        routing_key = self.get_routing_key(event_instance)
        return int(hashlib.md5(routing_key.encode()).hexdigest(), 16) % self.total_consumers == consumer_id


class DefaultRoutingStrategy(RoutingStrategy):
    def __init__(self):
        super().__init__(name=DEFAULT_ROUTING_STRATEGY_NAME, total_consumers=1)

    def register(self, event_cls: Type[Event], routing_fn: Callable[[Event], str]):
        raise ValueError('Event cannot be register in DefaultRoutingStrategy')

    def can_handle(self, event_instance: Event) -> bool:
        return True

    def get_routing_key(self, event_instance: Event) -> str:
        return DEFAULT_ROUTING_STRATEGY_NAME

    def should_process(self, event_instance: Event, consumer_id: int) -> bool:
        return consumer_id == 0  # Un seul consommateur autorisé par défaut

    def get_handled_event_names(self) -> List[str]:
        raise ValueError('Cannot get handled_event_names in DefaultRoutingStrategy because no event is registered.')


class InboxConsumerRoutingStrategy:
    """
    Class which is in charge to read the inbox consumer strategy for a specific context.
    This allow to consume multiple event at the same time for a specific context according to the routing key
    """
    def __init__(self, context_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_name = context_name
        self.strategies: Dict[str, RoutingStrategy] = {DEFAULT_ROUTING_STRATEGY_NAME: DefaultRoutingStrategy()}

    def register_strategy(
        self,
        strategy_name: str,
        events_cls: List[Type[Event]],
        routing_fn: Callable[[Event], str],
        total_consumers: int = 1
    ):
        if strategy_name not in self.strategies:
            self.strategies[strategy_name] = RoutingStrategy(
                name=strategy_name,
                total_consumers=total_consumers,
            )

        strategy = self.strategies[strategy_name]
        for event_cls in events_cls:
            # Vérifie que l'événement n'est pas déjà enregistré dans une autre stratégie
            for other_strategy_name, other_strategy in self.strategies.items():
                if other_strategy_name != strategy_name and event_cls in other_strategy.event_routing_functions:
                    raise ValueError(
                        f"{event_cls.__name__} already registered in strategy '{other_strategy_name}'"
                    )
            strategy.register(event_cls, routing_fn)

    def get_routing_key(
        self,
        event_instance: Event
    ) -> str:
        strategy = self._resolve_strategy_for_event(event_instance)
        return strategy.get_routing_key(event_instance)

    def should_process(self, event_instance: Event, consumer_id: int) -> bool:
        strategy = self._resolve_strategy_for_event(event_instance)
        return strategy.should_process(event_instance, consumer_id)

    def _resolve_strategy_for_event(self, event_instance: Event) -> RoutingStrategy:
        return next(
            (
                s for name, s in self.strategies.items()
                if name != DEFAULT_ROUTING_STRATEGY_NAME and s.can_handle(event_instance)
            ),
            self.strategies[DEFAULT_ROUTING_STRATEGY_NAME]
        )

    def handled_event_names(self, strategy_name: str) -> List[str]:
        return self.strategies[strategy_name].get_handled_event_names()

    def get_all_handled_event_names(self) -> List[str]:
        all_handled_event_names = []
        for strategy_name, strategy in self.strategies.items():
            if strategy_name != DEFAULT_ROUTING_STRATEGY_NAME:
                all_handled_event_names.extend(strategy.get_handled_event_names())
        return all_handled_event_names
