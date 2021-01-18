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
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

BELGIUM_NAT_NUMBER_LENGTH = 11
BELGIUM_NAT_NUMBER_CHECKSUM_KEY = 97


def belgium_national_register_number_validator(value):
    nat_nbr = ''.join(filter(str.isdigit, str(value)))

    if not all([
        _length_is_valid(nat_nbr),
        _included_date_is_valid(nat_nbr),
        _checksum_is_valid(nat_nbr)
    ]):
        raise ValidationError(
            _('%(value)s is not a valid identification number of the National Register of Belgium'),
            params={'value': value},
        )


def _length_is_valid(value):
    return len(value) == BELGIUM_NAT_NUMBER_LENGTH


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
