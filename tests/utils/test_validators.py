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
from django.test import SimpleTestCase

from osis_common.utils.validators import belgium_national_register_number_validator


class TestBelgiumNationalRegisterNumberValidator(SimpleTestCase):
    def test_correct_register_number(self):
        valid_cases = ['911210-123.20', '06 11 17.456.13', '850730 033 28', '170730 033 84']
        for case in valid_cases:
            with self.subTest(case=case):
                belgium_national_register_number_validator(case)

    def test_invalid_length(self):
        invalid_length_cases = ['1234567890', '91 12 03.456.7', '20.07.15.999.111']
        for case in invalid_length_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError):
                    belgium_national_register_number_validator(case)

    def test_invalid_included_date(self):
        invalid_date_cases = ['911310 123 66', '06 11 42.456.77']
        for case in invalid_date_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError):
                    belgium_national_register_number_validator(case)

    def test_invalid_checksum(self):
        invalid_date_cases = ['840820 311 70', '06 11 10.456.77']
        for case in invalid_date_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError):
                    belgium_national_register_number_validator(case)
