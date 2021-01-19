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
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from osis_common.utils.validators import belgium_national_register_number_validator

BELGIUM_NAT_NUMBER_LENGTH = 11


class TestBelgiumNationalRegisterNumberValidator(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.common_exception_message = _(
            '%(value)s is not a valid identification number of the National Register of Belgium')

    def test_correct_register_number(self):
        valid_cases = ['911210-123.20', '06 11 17.456.13', '85 07 30 033 28', '17073003384']
        for case in valid_cases:
            with self.subTest(case=case):
                belgium_national_register_number_validator(case)

    def test_invalid_characters(self):
        invalid_characters_cases = ['', '170730_03384', '170730:033 84', '170730033A84']
        for case in invalid_characters_cases:
            with self.subTest(case=case):
                excepted_message = "{} ({})".format(
                    self.common_exception_message % {"value": case},
                    _('the only characters allowed are : digits and . and - and /')
                )
                with self.assertRaisesMessage(ValidationError, excepted_message):
                    belgium_national_register_number_validator(case)

    def test_invalid_length(self):
        invalid_length_cases = ['123', '1234567890', '91 07 09.456.7', '20.07.15.999.111', '1234567891011']
        for case in invalid_length_cases:
            with self.subTest(case=case):
                excepted_message = "{} ({})".format(
                    self.common_exception_message % {"value": case},
                    _('it must be %(length)s digits long') % {"length": BELGIUM_NAT_NUMBER_LENGTH}
                )
                with self.assertRaisesMessage(ValidationError, excepted_message):
                    belgium_national_register_number_validator(case)

    def test_invalid_included_date(self):
        invalid_date_cases = ['911310 123 66', '06 11 42.456.77']
        for case in invalid_date_cases:
            with self.subTest(case=case):
                excepted_message = "{} ({})".format(
                    self.common_exception_message % {"value": case},
                    _('it does not match a valid birth date')
                )
                with self.assertRaisesMessage(ValidationError, excepted_message):
                    belgium_national_register_number_validator(case)

    def test_invalid_checksum(self):
        invalid_date_cases = ['840820 311 70', '06 11 10.456.77']
        for case in invalid_date_cases:
            with self.subTest(case=case):
                excepted_message = "{} ({})".format(
                    self.common_exception_message % {"value": case},
                    _('the checksum is invalid')
                )
                with self.assertRaisesMessage(ValidationError, excepted_message):
                    belgium_national_register_number_validator(case)
