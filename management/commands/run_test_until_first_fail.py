##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2022 Université catholique de Louvain (http://www.uclouvain.be)
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
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Launch test/test case/tests app until first failed. This makes it easier to fail a random test fail
    Arguments :
            -k : if presents, keep the database
            --tests/-t : mandatory, followed by one or many tests separated by a space
            -n : number of try
    Example:
            python manage.py run_test_until_first_fail -k --tests assessments.tests.views assessments.tests.forms
    """

    def add_arguments(self, parser):
        parser.add_argument('-k', action='store_true', help="keep the database")
        parser.add_argument('-n', action='store', help="number of try")
        parser.add_argument(
            '--tests', '-t',
            nargs='+',
            help="path to the test/test case/app to test  with dot (Examples : "
                 "- assessments.tests.views.test_scores_responsible.ScoresResponsibleSearchTestCase."
                 "                      test_assert_template_used"
                 "- assessments.tests.views.test_scores_responsible.ScoresResponsibleSearchTestCase"
                 "- assessments",
            required=True
        )

    def handle(self, *args, **kwargs):
        command = "python manage.py test {reinit_db} {test_cases}".format(
            reinit_db="--keepdb" if kwargs['k'] is True else "",
            test_cases=' '.join(kwargs['tests'])
        )
        max_try = int(kwargs['n']) if kwargs.get('n') else float('inf')
        number_of_try = 0
        while number_of_try < max_try:
            result = os.system(command)
            if result != 0:
                break
            number_of_try += 1
