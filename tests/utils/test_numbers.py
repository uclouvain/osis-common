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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
from decimal import Decimal

from django.test import TestCase

from osis_common.utils import numbers


class TestNumbersUtils(TestCase):
    def test_to_float_or_zero(self):
        input_output = [(17, 17.0), (-42, -42.0), (0, 0), (None, 0), (False, 0), ("", 0)]
        for (inp, outp) in input_output:
            with self.subTest(inp=inp, outp=outp):
                self.assertEqual(numbers.to_float_or_zero(inp), outp)

        with self.assertRaises(ValueError):
            numbers.to_float_or_zero("string")

    def test_normalize_fraction(self):
        input_output = [(Decimal('5.00'), 5), (Decimal('3E1'), 30), (Decimal('5'), 5)]
        for (inp, outp) in input_output:
            with self.subTest(inp=inp, outp=outp):
                self.assertEqual(outp, numbers.normalize_fraction(inp))
