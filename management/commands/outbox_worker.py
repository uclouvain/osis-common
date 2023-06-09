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
import logging
import pika

from django.conf import settings
from django.core.management import BaseCommand
from django.utils.module_loading import import_string

from osis_common.queue import queue_sender


logger = logging.getLogger(settings.DEFAULT_LOGGER)


class Command(BaseCommand):
    help = """
    Command to send events (aka. message_bus_instance.apublish) produce by the application to the message broker
    """

    def handle(self, *args, **options):
        self._load_outbox_model()
        self._initialize_broker_channel()

    def _initialize_broker_channel(self):
        connection = queue_sender.get_connection()
        channel = connection.channel()

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
        outbox_model_path = settings.MESSAGE_BUS['CREATE_OUTBOX_ENTRY_HOOK']
        self.outbox_model = import_string(outbox_model_path)
