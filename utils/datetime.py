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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
import datetime

from django.conf import settings
from django.utils import timezone


def get_tzinfo():
    if settings.USE_TZ:
        return timezone.get_current_timezone()
    return None


def strictly_ordered_dates(date_low, date_high):
    if not (isinstance(date_low, datetime.date) and isinstance(date_high, datetime.date)):
        raise TypeError("Arguments should be datetime.datetime or datetime.date")

    date_low = date_low.date() if isinstance(date_low, datetime.datetime) else date_low
    date_high = date_high.date() if isinstance(date_high, datetime.datetime) else date_high
    return date_low < date_high


def convert_date_to_datetime(value):
    if isinstance(value, datetime.datetime):
        return value
    elif isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day, tzinfo=get_tzinfo())
    else:
        return value


def convert_datetime_to_date(value):
    if isinstance(value, datetime.datetime):
        value = timezone.localtime(value, get_tzinfo())
        return datetime.date(value.year, value.month, value.day)
    else:
        return value


