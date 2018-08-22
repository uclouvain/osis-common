##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2017 Université catholique de Louvain (http://www.uclouvain.be)
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
from osis_common.decorators import override
from django import get_version as get_django_version


class InstalledAppsTestRunner(DiscoverRunner):

    @override(DiscoverRunner)
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        django_version = get_django_version()
        tests_type = 'Unit Tests Only'
        if test_labels:
            if test_labels[0] == 'selenium':
                tests_type = 'Unit Tests + Selenium Tests'
                test_labels = test_labels[1:]
            elif test_labels[0] == 'selenium_only':
                tests_type = 'Selenium Tests Only'
                test_labels = test_labels[1:]
                self.tags = ['selenium']
            else:
                self.exclude_tags.add('selenium')
        else:
            self.exclude_tags.add('selenium')

        if not test_labels:
            test_labels = settings.APPS_TO_TEST
        print('###### Tests Infos #####################################')
        print('### Test Runner : {}'.format(settings.TEST_RUNNER))
        print('### Django Version : {}'.format(django_version))
        print('### Tests type: {}'.format(tests_type))
        print('########################################################')
        print('')
        return super().build_suite(test_labels=test_labels, extra_tests=extra_tests, **kwargs)

