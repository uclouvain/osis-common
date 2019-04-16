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
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase

from osis_common.utils.perms import BasePerm

error_msg1 = "Number too big"
error_msg2 = "Number is not pair"

def predicate1(*, n):
    value = n <= 10
    if not value:
        raise PermissionDenied(error_msg1)


def predicate2(*, n):
    value = n % 2 == 0
    if not value:
        raise PermissionDenied(error_msg2)


class IsNumberLegit(BasePerm):
    predicates = (predicate1, predicate2)


class TestBasePerms(SimpleTestCase):
    def test_errors(self):
        errors = IsNumberLegit(n=11).errors
        self.assertListEqual(errors, [error_msg1, error_msg2])

        errors = IsNumberLegit(n=9).errors
        self.assertListEqual(errors, [error_msg2])

        errors = IsNumberLegit(n=6).errors
        self.assertListEqual(errors, [])

    def test_is_valid(self):
        is_valid = IsNumberLegit(n=9).is_valid()
        self.assertFalse(is_valid)

        is_valid = IsNumberLegit(n=6).is_valid()
        self.assertTrue(is_valid)

    def test_as_ul(self):
        html = IsNumberLegit(n=6).as_ul
        self.assertEqual(html, "")

        html = IsNumberLegit(n=11).as_ul
        self.assertEqual("<ul><li>{msg1}</li><li>{msg2}</li></ul>".format(msg1=error_msg1, msg2=error_msg2),
                         html)
