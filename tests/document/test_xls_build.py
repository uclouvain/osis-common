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
import datetime
from django.test.testcases import TestCase
from osis_common.document import xls_build

TODAY = datetime.date.today()


class TestXlsBuild(TestCase):
    def test_valid_data(self):
        data = getRightData()
        self.assertTrue(xls_build._is_valid(data))

    def test_data_empty(self):
        self.assertFalse(xls_build._is_valid(None))

    def test_data_for_file_incomplete_missing_worksheets_data(self):
        data = {xls_build.LIST_DESCRIPTION_KEY: 'Liste de cours',
                xls_build.FILENAME_KEY: 'fichier_test',
                xls_build.USER_KEY: 'Dupuis'
                }
        self.assertFalse(xls_build._is_checked_file_parameters_list(data))

    def test_data_for_file_complete(self):
        data = {xls_build.LIST_DESCRIPTION_KEY: 'Liste de cours',
                xls_build.FILENAME_KEY: 'fichier_test',
                xls_build.USER_KEY: 'Dupuis',
                xls_build.WORKSHEETS_DATA: None}
        self.assertTrue(xls_build._is_checked_file_parameters_list(data))

    def test_with_no_data(self):
        data = {xls_build.WORKSHEETS_DATA: None}
        self.assertFalse(xls_build._is_checked_worsheets_data(data))

    def test_with_wrong_worksheet_data(self):
        data = {xls_build.WORKSHEETS_DATA:
            [{xls_build.CONTENT_KEY: [
                ['LBIR1225', 'Cours de Bir', '123456789', 2017, TODAY.strftime('%d-%m-%Y')]]}
            ]}
        self.assertFalse(xls_build._is_checked_worsheets_data(data))

    def test_with_correct_worksheet_data(self):
        data = {xls_build.WORKSHEETS_DATA:
            [{xls_build.CONTENT_KEY: [['LAGRE2020', 'C. biologie', 'Marcel Lenoir', 2018]],
              xls_build.HEADER_TITLES_KEY: ['Code', 'Short title', 'Name', 'Year'],
              xls_build.WORKSHEET_TITLE_KEY: 'Feuille 2', }
            ]}
        self.assertTrue(xls_build._is_checked_worsheets_data(data))

    def test_check_xls_generation(self):
        data = getRightData()
        http_response = xls_build._create_xls(data)
        self.assertEqual(http_response.status_code, 200)
        self.assertIsNotNone(http_response.content)
        self.assertEqual(http_response['content-type'], 'application/vnd.ms-excel')


def getRightData():
    # Return a valid template data
    return {xls_build.LIST_DESCRIPTION_KEY: 'Liste de cours',
            xls_build.FILENAME_KEY: 'fichier_test',
            xls_build.USER_KEY: 'Dupuis',
            xls_build.WORKSHEETS_DATA:
                [{xls_build.CONTENT_KEY: [['Col1 Row1', 'Cours de Bir', '123456789', 2017, TODAY.strftime('%d-%m-%Y')],
                                          ['Col1 Row2', 'Cours de Bir', '123456789', 2018, TODAY.strftime('%d-%m-%Y')],
                                          ['Col1 Row3', 'Cours biologie', 'o', 2017, None]],
                  xls_build.HEADER_TITLES_KEY: ['Acronym', 'Title', 'Global id', 'Year', 'Changed'],
                  xls_build.WORKSHEET_TITLE_KEY: 'Feuille 1',
                  xls_build.COLORED_ROWS: {xls_build.STYLE_NO_GRAY: [3],
                                           xls_build.STYLE_RED: [2]},
                  xls_build.COLORED_COLS: {xls_build.STYLE_NO_GRAY: [1],
                                           xls_build.STYLE_RED: [2]},
                  },
                 {xls_build.CONTENT_KEY: [['Col1 Row1', 'C. biologie', 'Marcel Lenoir', 2018]],
                  xls_build.HEADER_TITLES_KEY: ['Code', 'Short title', 'Name', 'Year'],
                  xls_build.WORKSHEET_TITLE_KEY: 'Feuille 2',
                  xls_build.COLORED_ROWS: {xls_build.STYLE_NO_GRAY: [2]}
                  }
                 ]}
