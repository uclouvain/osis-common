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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
from django.db.utils import InternalError
from django.core.exceptions import PermissionDenied
from django.test import TestCase

import factory.fuzzy
from unittest import mock

from osis_common.utils import native


class TestNativeUtils(TestCase):
    def test_exact_words_of_list_in_string(self):
        test_string = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                       "Morbi molestie velit quis lacus eleifend pretium."
                       "Nunc lacinia aliquam ipsum, quis iaculis lacus vehicula non. In nec nibh nunc. Aliquam velit.")

        list_3_matching_words = ['Lorem', 'lacus', 'NUnc']
        list_no_matching_word = ['azerty', '321gr', 'qsdfg', 'WxCvB']
        list_3_of_7_matching_word = list_3_matching_words + list_no_matching_word
        list_of_1_partially_matching_word = ['onsectetu']

        self.assertListEqual(
            native.exact_words_of_list_in_string(list_3_matching_words, test_string, False),
            list_3_matching_words
        )

        self.assertListEqual(
            native.exact_words_of_list_in_string(list_3_matching_words, test_string, True),
            ['Lorem', 'lacus']
        )

        self.assertListEqual(
            native.exact_words_of_list_in_string(list_no_matching_word, test_string, False),
            []
        )

        self.assertListEqual(
            native.exact_words_of_list_in_string(list_3_of_7_matching_word, test_string, False),
            list_3_matching_words
        )

        self.assertListEqual(
            native.exact_words_of_list_in_string(list_of_1_partially_matching_word, test_string, False),
            []
        )

    def test_execute_unauthorized_request(self):
        forbidden_sql_keywords = native.get_forbidden_sql_keywords()
        for forbidden in forbidden_sql_keywords:
            with self.assertRaises(PermissionDenied):
                unauthorized_request = _generate_fake_text_starting_with_keyword(forbidden)
                native.execute(unauthorized_request)

    @mock.patch('osis_common.utils.native.get_sql_data_management_readonly')
    def test_execute_write_sql_with_readonly_flag(self, mock_sql_readonly):
        mock_sql_readonly.return_value = True
        with self.assertRaises(InternalError):
            native.execute("UPDATE base_person set last_name='Toto'")


def _generate_fake_text_starting_with_keyword(keyword):
    return factory.fuzzy.FuzzyText(prefix=keyword+' ').fuzz()
