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

from osis_common.utils.inbox_outbox import EventQueueConsumer, HandlersPerContextFactory

logger = logging.getLogger(settings.ASYNC_WORKERS_LOGGER)


class Command(BaseCommand):
    help = """
    Command to remove the binding between queue (=context) and eventname which are not used anymore
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--context_name",
            dest='context_name',
            type=str,
            required=False,
            help="The name of the bounded context"
        )

    def handle(self, *args, **options):
        context_name = options.get('context_name')
        if context_name:
           context_names_to_clear = [context_name]
        else:
            context_names_to_clear = list(HandlersPerContextFactory.get().keys())

        for context_name in context_names_to_clear:
            EventQueueConsumer(context_name=context_name).clear_uninterested_events()
