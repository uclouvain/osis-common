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
import json
import logging

import pika
from django.conf import settings

logger = logging.getLogger(settings.DEFAULT_LOGGER)


def get_connection():
    credentials = pika.PlainCredentials(settings.QUEUES.get('QUEUE_USER'),
                                        settings.QUEUES.get('QUEUE_PASSWORD'))
    return pika.BlockingConnection(pika.ConnectionParameters(settings.QUEUES.get('QUEUE_URL'),
                                                             settings.QUEUES.get('QUEUE_PORT'),
                                                             settings.QUEUES.get('QUEUE_CONTEXT_ROOT'),
                                                             credentials))


def get_channel(connection, queue_name):
    if connection:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        return channel
    else:
        return None


def send_message(queue_name, message, connection=None, channel=None):
    """
    Send the message in the queue passed in parameter.
    If the connection doesn't exist, the function will create it, send the message, then close the connection.
    That's the same for the channel ; if any channel is given, the function will create it, send the message,
    then close the channel.

    WARNING : If a connection or a channel is given, the function doesn't close it. Do not forget to close
              the channel and the connection after you sent all your messages in the queue.

    :param queue_name: the name of the queue in which we have to send the JSON message.
    :param message: JSON data sent into the queue.
    :param connection: A connection to a Queue.
    :param channel: An opened channel from the connection given in parameter.
    """
    if channel and not connection:
        raise Exception('Please give the connection from which you opened the channel given by parameter')

    #Get connection [Raise exception if no connection]
    if not connection or connection.is_closed:
        connection = get_connection()

    #Get channel
    if not channel or channel.is_closed:
        channel = get_channel(connection, queue_name)

    # Turn on delivery confirmations
    channel.confirm_delivery()

    try:
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(content_type='application/json', delivery_mode=2)
        )
    except Exception:
        logger.exception("Exception in queue")
    finally:
        if channel and channel.is_open:
            channel.close()
        if connection and connection.is_open:
            connection.close()