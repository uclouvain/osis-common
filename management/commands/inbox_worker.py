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
from django.core.management import BaseCommand

from osis_common.utils.inbox_outbox import InboxConsumer, HandlersPerContextFactory


class Command(BaseCommand):
    help = """
    Command to start 1 thread/bounded context in order to processing reaction according to event
    Script must be run in the root of the project
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--context_name",
            dest='context_name',
            type=str,
            required=True,
            help="The name of the bounded context"
        )
        parser.add_argument(
            "-s",
            "--strategy_name",
            dest="strategy_name",
            type=str,
            default="default",
            help="The name of the routing strategy (default: 'default')"
        )
        parser.add_argument(
            "-i",
            "--consumer_id",
            dest="consumer_id",
            type=int,
            default=0,
            help="The ID of the consumer (default: 0)"
        )

    def handle(self, *args, **options):
        from infrastructure.messages_bus import message_bus_instance

        context_name = options["context_name"]
        strategy_name = options["strategy_name"]
        consumer_id = options["consumer_id"]


        InboxConsumer(
            message_bus_instance=message_bus_instance,
            context_name=context_name,
            strategy_name=strategy_name,
            consumer_id=consumer_id,
            event_handlers=HandlersPerContextFactory.get()[context_name]
        ).consume_all_unprocessed_events()
