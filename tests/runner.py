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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
import unittest

import time
from django import get_version as get_django_version
from django.conf import settings
from django.test.runner import DiscoverRunner
from mock import patch

from osis_common.tests.functional.models.report import make_html_report


class DebugTimeTextTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        self.test_timings = []
        super().__init__(stream, descriptions, verbosity)

    def startTest(self, test):
        self._test_started_at = time.time()
        super().startTest(test)

    def addSuccess(self, test):
        time_elapsed = time.time() - self._test_started_at
        test_name = self.getDescription(test)
        self.test_timings.append((test_name, time_elapsed))
        super().addSuccess(test)


class DebugTimeTestRunner(unittest.TextTestRunner):
    resultclass = DebugTimeTextTestResult
    stream = None

    def run(self, test):
        result = super().run(test)
        slow_test_threshold = self.get_slow_test_threshold()
        slowest_test_timings = filter(
            lambda test_name__time_elapsed: test_name__time_elapsed[1] > slow_test_threshold, result.test_timings
        )
        slowest_test_timings = sorted(slowest_test_timings, key=lambda tup: tup[1], reverse=True)

        self.stream.writeln("\n {} slow tests (>{:.03}s):".format(len(slowest_test_timings), slow_test_threshold))
        for test_name, time_elapsed in slowest_test_timings:
            self.stream.writeln("({:.03}s) {}".format(time_elapsed, test_name))
        return result

    def get_slow_test_threshold(self):
        return getattr(settings, 'SLOW_TEST_THRESHOLD', 0.8)


class InstalledAppsTestRunner(DiscoverRunner):
    test_runner = DebugTimeTestRunner

    @staticmethod
    def mock_user_roles_api_return():
        import json
        with open('osis_common/tests/ressources/person_roles_from_api.json') as json_file:
            data = json.load(json_file)
        return data

    def build_suite(self, test_labels=None, *args, **kwargs):
        django_version = get_django_version()
        if hasattr(settings, 'TESTS_TYPES') and settings.TESTS_TYPES == 'ALL':
            tests_type = 'Unit Tests + Selenium Tests'
        elif hasattr(settings, 'TESTS_TYPES') and settings.TESTS_TYPES == 'SELENIUM':
            tests_type = 'Selenium Tests Only'
            self.tags = ['selenium']
        else:
            tests_type = 'Unit Tests Only'
            self.exclude_tags.add('selenium')
        print('###### Tests Infos #####################################')
        print('### Test Runner : {}'.format(settings.TEST_RUNNER))
        print('### Django Version : {}'.format(django_version))
        print('### Tests type: {}'.format(tests_type))
        if hasattr(settings, 'FUNCT_TESTS_CONFIG') and settings.FUNCT_TESTS_CONFIG:
            print('### Virtual Dispaly: {}'.format(settings.FUNCT_TESTS_CONFIG.get('VIRTUAL_DISPLAY')))
        print('########################################################')
        print('')
        if hasattr(settings, 'MOCK_USER_ROLES_API_CALL') and settings.MOCK_USER_ROLES_API_CALL:
            self.user_roles_api_call = patch(settings.USER_ROLES_API_MOCKED_FUNCT)
            self.mock_user_roles_api_call = self.user_roles_api_call.start()
            self.mock_user_roles_api_call.return_value = self.mock_user_roles_api_return()
        return super(InstalledAppsTestRunner, self).build_suite(test_labels or settings.APPS_TO_TEST, *args, **kwargs)

    def teardown_test_environment(self, **kwargs):
        if hasattr(settings, 'FUNCT_TESTS_CONFIG') and settings.FUNCT_TESTS_CONFIG \
                and settings.FUNCT_TESTS_CONFIG.get('HTML_REPORTS') and settings.FUNCT_TESTS_CONFIG.get('HTML_REPORTS_DIR'):
            make_html_report()
        if hasattr(settings, 'MOCK_USER_ROLES_API_CALL') and settings.MOCK_USER_ROLES_API_CALL:
            self.user_roles_api_call.stop()
        super(InstalledAppsTestRunner, self).teardown_test_environment(**kwargs)

