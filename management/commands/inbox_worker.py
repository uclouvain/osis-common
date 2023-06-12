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
import contextlib
import glob
import logging
import os
from importlib import util
from typing import List

from django.conf import settings
from django.core.management import BaseCommand
from django.utils.module_loading import import_string

from osis_common.queue import queue_sender

logger = logging.getLogger(settings.DEFAULT_LOGGER)


class Command(BaseCommand):
    help = """
    Command to store events (aka. message_bus_instance.apublish) comming from to the message broker to the context
    Script must be run in the root of the project
    """

    def handle(self, *args, **options):
        consummers = self._retrieve_consummers_list()
        print(consummers)

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

    def _retrieve_consummers_list(self) -> List[str]:
        consummers_list = []
        handlers_path = glob.glob("infrastructure/*/handlers.py", recursive=True)
        for handler_path in handlers_path:
            with contextlib.suppress(AttributeError):
                handler_module = self.__import_file('handler_module', handler_path)
                if handler_module.EVENT_HANDLERS:
                    bounded_context = os.path.dirname(handler_path).split(os.sep)[-1]
                    consummers_list.append(bounded_context)
        return consummers_list

    def __import_file(self, full_name, path):
        spec = util.spec_from_file_location(full_name, path)
        mod = util.module_from_spec(spec)

        spec.loader.exec_module(mod)
        return mod
