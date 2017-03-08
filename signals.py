import logging
from django.dispatch import Signal
from django.conf import settings
from pika.exceptions import ChannelClosed, ConnectionClosed
from osis_common.queue import queue_sender
from osis_common.models import serializable_model

LOGGER = logging.getLogger(settings.DEFAULT_LOGGER)

send_to_queue = Signal(providing_args=["instance", "kwargs"])


def _send_to_queue_handler(sender, instance, **kwargs):
    if hasattr(settings, 'QUEUES'):
        try :
            instance_serialized = {'body': serializable_model.serialize(instance), 'to_delete': kwargs.get('to_delete')}
            queue_sender.send_message(settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_PRODUCE'),
                                      instance_serialized)
        except (ChannelClosed, ConnectionClosed):
            LOGGER.exception('QueueServer is not installed or not launched')

send_to_queue.connect(_send_to_queue_handler)