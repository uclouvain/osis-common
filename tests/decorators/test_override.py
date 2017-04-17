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
from django.conf import settings
from django.test.testcases import TestCase
from osis_common.decorators.override import _check_super_class_method
from osis_common.models.exception import OverrideMethodError
from osis_common.tests.models_for_tests.override_tests_models import WrongOverrideMethod, \
    GoodOverrideChild, ClassToOverride
import logging

logger = logging.getLogger(settings.DEFAULT_LOGGER)


class TestOverrideDecorator(TestCase):

    def test_wrong_method_override(self):
        with self.assertRaises(OverrideMethodError) as e:
            WrongOverrideMethod().foo('args')

    def test_override_decorator_ok(self):
        GoodOverrideChild().method_to_override('args')

    def test_check_super_class_method_valid(self):
        self.assertTrue(_check_super_class_method(GoodOverrideChild().__class__.__bases__,
                        ClassToOverride().method_to_override.__name__))

    def test_check_super_class_method_wrong(self):
        self.assertFalse(_check_super_class_method(WrongOverrideMethod().__class__.__bases__,
                                                   WrongOverrideMethod().foo.__name__))
