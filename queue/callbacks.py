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
import traceback

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.db.utils import OperationalError as DjangoOperationalError, InterfaceError as DjangoInterfaceError
from psycopg2._psycopg import OperationalError as PsycopOperationalError, InterfaceError as  PsycopInterfaceError

from osis_common.models.queue_exception import QueueException

logger = logging.getLogger(settings.DEFAULT_LOGGER)
queue_exception_logger = logging.getLogger(settings.QUEUE_EXCEPTION_LOGGER)


def add_user_field_to_object_if_possible(object):
    if __user_field_in_model(object):
        object = __set_deser_object_user_if_exists(object)
    return object


def __set_deser_object_user_if_exists(object):
    object_before_update = type(object).find_by_uuid(object.uuid)
    if object_before_update and object_before_update.user:
        object.user = object_before_update.user
    return object


def __user_field_in_model(object):
    try:
        return type(object)._meta.get_field('user')
    except FieldDoesNotExist:
        return False


def process_message(json_data):
    from osis_common.models import serializable_model
    json_data_dict = json.loads(json_data.decode("utf-8"))
    try:
        body = serializable_model.unwrap_serialization(json_data_dict)
        if body:
            serializable_model.persist(body)
    except (PsycopOperationalError, PsycopInterfaceError, DjangoOperationalError, DjangoInterfaceError) as ep:
        trace = traceback.format_exc()
        try:
            data = json.loads(json_data.decode("utf-8"))
            queue_exception = QueueException(queue_name=settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_CONSUME'),
                                             message=data,
                                             exception_title='[Catched and retried] - {}'.format(type(ep).__name__),
                                             exception=trace)
            queue_exception_logger.error(queue_exception.to_exception_log())
        except Exception:
            logger.error(trace)
            log_trace = traceback.format_exc()
            logger.warning('Error during queue logging and retry:\n {}'.format(log_trace))
        connection.close()
        process_message(json_data)
    except Exception as e:
        trace = traceback.format_exc()
        try:
            data = json.loads(json_data.decode("utf-8"))
            queue_exception = QueueException(queue_name=settings.QUEUES.get('QUEUES_NAME').get('MIGRATIONS_TO_CONSUME'),
                                             message=data,
                                             exception_title=type(e).__name__,
                                             exception=trace)
            queue_exception_logger.error(queue_exception.to_exception_log())
        except Exception:
            logger.error(trace)
            log_trace = traceback.format_exc()
            logger.warning('Error during queue logging :\n {}'.format(log_trace))

