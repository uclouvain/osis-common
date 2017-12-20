##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2017 Université catholique de Louvain (http://www.uclouvain.be)
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
import re

from django.conf import settings
from django.db import connection
from django.db import transaction
from django.core.exceptions import PermissionDenied


@transaction.atomic
def execute(sql_command):
    results = []
    if sql_command:
        if sql_command_contains_forbidden_keyword(sql_command):
            raise PermissionDenied("SQL command contains forbidden SQL keyword")

        with connection.cursor() as cursor:
            sql_commands = sql_command.split(";")

            for count, command in enumerate(sql_commands):
                stripped_command = command.strip()
                if stripped_command:
                    if get_sql_data_management_readonly():
                        protected_command = get_sql_command_readonly(stripped_command)
                    else:
                        protected_command = stripped_command

                    try:
                        cursor.execute(protected_command)
                        results += [u'%d: %s\n> %s\n\n' % (count + 1, stripped_command, cursor.fetchall())]
                    except Exception as e:
                        results += [u'%d: %s\n> %s\n\n' % (count + 1, stripped_command, e)]
    return results


def get_sql_command_readonly(command):
    return "SET TRANSACTION READ ONLY; " + command


def sql_command_contains_forbidden_keyword(sql_command):
    return exact_words_of_list_in_string(get_forbidden_sql_keywords(), sql_command, False)


def exact_words_of_list_in_string(words_list, string, case_sensitive=False):
    if case_sensitive:
        return [word for word in words_list if re.search(r'\b' + word + r'\b', string)]
    else:
        return [word for word in words_list if re.search(r'\b' + word.lower() + r'\b', string.lower())]


def get_forbidden_sql_keywords():
    if hasattr(settings, 'FORBIDDEN_SQL_KEYWORDS'):
        return settings.FORBIDDEN_SQL_KEYWORDS
    return []


def get_sql_data_management_readonly():
    if hasattr(settings, 'SQL_DATA_MANAGEMENT_READONLY'):
        return settings.SQL_DATA_MANAGEMENT_READONLY
    return True
