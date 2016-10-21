#!/usr/bin/env python3
##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2016 Université catholique de Louvain (http://www.uclouvain.be)
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
"""
This script is used to make initial migrations of data between osis and osis portal
It has to be used when data already exists in osis or osis-portal and one
of these project was used alone whitout the second one.
The script functions have to be launched from common line 'dbshell' in osis or osis-portal environnment.
Migrations are made trough the queue system

ex from osis :
(VENV) cd /path/to/osis
(VENV) python3 manage.py dbshell
~ from osis_common.scripts import initial_migration
~ initial_migration.migrate_document_files_to_osis_portal()
"""
from django.apps import AppConfig
from pika.exceptions import ChannelClosed, ConnectionClosed
from osis_common.models.serializable_model import format_data_for_migration
from osis_common.queue import queue_sender
from django.conf import settings


def migrate_model(model_name):
    if hasattr(settings, 'QUEUES'):
        Model = AppConfig.get_model(model_name)
        objects = Model.objects.all()
        try:
            queue_sender.send_message(settings.QUEUES.get('QUEUES_NAME').get('MODEL_MIGRATION'),
                                      format_data_for_migration(objects))
        except (ChannelClosed, ConnectionClosed):
            print('QueueServer is not installed or not launched')
    else:
        print('You have to configure queues to use migration script!')

