##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2024 Université catholique de Louvain (http://www.uclouvain.be)
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
from pathlib import Path

from django.test import TestCase

from osis_common.utils.file_router import FileRouter


class FileRouterTestCase(TestCase):
    def setUp(self):
        self.router = FileRouter()
        self.patterns = self.router(str(Path(__file__).parent / 'file_router_views'))

    def _get_pattern(self, patterns, name):
        return next(
            (
                pattern
                for pattern in patterns
                if getattr(pattern, 'app_name', None) == name or getattr(pattern, 'name', None) == name
            ),
            None,
        )

    def test_file_router(self):
        self.assertEqual(len(self.patterns), 3)

        doctorate_patterns = self._get_pattern(self.patterns, 'doctorate')
        doctorate_patterns = self._get_pattern(doctorate_patterns.url_patterns, 'test')
        general_patterns = self._get_pattern(self.patterns, 'general')
        general_patterns = self._get_pattern(general_patterns.url_patterns, 'test')
        continuing_patterns = self._get_pattern(self.patterns, 'continuing')
        continuing_patterns = self._get_pattern(continuing_patterns.url_patterns, 'test')

        self.assertEqual(len(doctorate_patterns.url_patterns), 1)
        self.assertEqual(len(general_patterns.url_patterns), 2)
        self.assertEqual(len(continuing_patterns.url_patterns), 3)

        general_test_view = self._get_pattern(general_patterns.url_patterns, 'test_view')
        self.assertEqual(
            general_test_view.lookup_str, 'osis_common.tests.utils.file_router_views.general.test.views.TestGeneralView'
        )

        continuing_test_view = self._get_pattern(continuing_patterns.url_patterns, 'test_view')
        self.assertEqual(
            continuing_test_view.lookup_str,
            'osis_common.tests.utils.file_router_views.continuing.test.views.TestContinuingView',
        )
