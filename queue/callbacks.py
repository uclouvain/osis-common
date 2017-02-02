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
import json
from django.core.exceptions import FieldDoesNotExist
from psycopg2._psycopg import OperationalError, InterfaceError
from django.db import connection


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
    data = json.loads(json_data.decode("utf-8"))
    body = serializable_model.unwrap_serialization(data)
    if body:
        try:
            serializable_model.persist(body)
        # except OperationalError:
        #     connection.rollback()
        #     process_message(json_data)
        # except InterfaceError as exc:
        #     db_conn = psycopg2.connect('default')
        #     cursor = db_conn.cursor()
        #     cursor.close()
        except (OperationalError, InterfaceError):
            connection.close()
            process_message(json_data)

