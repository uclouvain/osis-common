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
from django.conf import settings
from django.test.runner import DiscoverRunner
from mock import patch

from osis_common.decorators import override
from django import get_version as get_django_version

from osis_common.tests.functional.models.report import make_html_report


class InstalledAppsTestRunner(DiscoverRunner):

    @staticmethod
    def mock_user_roles_api_return():
        import json
        with open('osis_common/tests/ressources/person_roles_from_api.json') as json_file:
            data = json.load(json_file)
        return data

    @override(DiscoverRunner)
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
            self.user_roles_api_call = patch(settings.get('USER_ROLES_API_MOCKED_FUCNT'))
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

