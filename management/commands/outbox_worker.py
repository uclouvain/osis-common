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
import logging

from django.conf import settings
from django.core.management import BaseCommand

from osis_common.utils.inbox_outbox import EventQueueProducer

logger = logging.getLogger(settings.ASYNC_WORKERS_LOGGER)


class Command(BaseCommand):
    help = """
    Command to send events produce by the application to the message broker
    Script must be run in the root of the project
    """

    def handle(self, *args, **options):
        event_queue_producer = EventQueueProducer()
        event_queue_producer.send_pending_events_to_queue()
        event_queue_producer.close_connection()
