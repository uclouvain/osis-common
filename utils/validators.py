##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2021 Université catholique de Louvain (http://www.uclouvain.be)
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

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

BELGIUM_NAT_NUMBER_LENGTH = 11
BELGIUM_NAT_NUMBER_CHECKSUM_KEY = 97
BELGIUM_NAT_NUMBER_REGEX = r"[0-9 ./-]+"


def belgium_national_register_number_validator(value):
    common_exception_message = _('%(value)s is not a valid identification number of the National Register of Belgium')

    if not _all_characters_are_valid(value):
        raise ValidationError(
            "{} ({})".format(
                common_exception_message,
                _('the only characters allowed are : digits and . and - and /')
            ),
            params={'value': value}
        )

    nat_nbr = ''.join(filter(str.isdigit, str(value)))

    if not _length_is_valid(nat_nbr):
        raise ValidationError(
            "{} ({})".format(
                common_exception_message,
                _('it must be %(length)s digits long')
            ),
            params={'value': value, 'length': BELGIUM_NAT_NUMBER_LENGTH}
        )

    elif not _included_date_is_valid(nat_nbr):
        raise ValidationError(
            "{} ({})".format(
                common_exception_message,
                _('it does not match a valid birth date')
            ),
            params={'value': value}
        )

    elif not _checksum_is_valid(nat_nbr):
        raise ValidationError(
            "{} ({})".format(
                common_exception_message,
                _('the checksum is invalid')
            ),
            params={'value': value}
        )


def _length_is_valid(value):
    return len(value) == BELGIUM_NAT_NUMBER_LENGTH


def _all_characters_are_valid(value):
    match = re.fullmatch(BELGIUM_NAT_NUMBER_REGEX, value)
    return match


def _included_date_is_valid(value):
    birth_month = int(value[2:4])
    birth_day = int(value[4:6])
    return 0 <= birth_month <= 12 and 0 <= birth_day <= 31


def _checksum_is_valid(value):
    part_to_check = int(value[0:9])
    part_to_check_birth_after_year_2000 = int('2' + value[0:9])
    checksum = int(value[9:11])

    return checksum == __compute_checksum(part_to_check) or \
        checksum == __compute_checksum(part_to_check_birth_after_year_2000)


def __compute_checksum(value):
    return BELGIUM_NAT_NUMBER_CHECKSUM_KEY - value % BELGIUM_NAT_NUMBER_CHECKSUM_KEY
