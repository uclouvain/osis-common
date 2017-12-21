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
import re
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl import Workbook
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
import logging
from django.conf import settings
from openpyxl.styles import Color, Style, PatternFill


FIRST_DATA_LINE = 2
MAX_COL_WIDTH = 50
XLS_EXTENSION = 'xlsx'
OPENPYXL_STRING_FORMAT = '@'

LIST_DESCRIPTION_KEY = 'list_description'
FILENAME_KEY = 'filename'
USER_KEY = 'username'

WORKSHEETS_DATA = 'data'
CONTENT_KEY = 'content'
HEADER_TITLES_KEY = 'header_titles'
WORKSHEET_TITLE_KEY = 'worksheet_title'
COLORED_ROWS = 'colored_rows'
COLORED_COLS = 'colored_cols'

STYLE_NO_GRAY = Style(fill=PatternFill(patternType='solid', fgColor=Color('C1C1C1')))
STYLE_RED = Style(fill=PatternFill(patternType='solid', fgColor=Color(rgb='00FF0000')))

logger = logging.getLogger(settings.DEFAULT_LOGGER)


def generate_xls(list_parameters):
    if _is_valid(list_parameters):
        return _create_xls(list_parameters)
    else:
        logger.warning('Error data invalid to create xls')
        return HttpResponse('')


def _create_xls(parameters_dict):
    filename = _build_filename(parameters_dict.get(FILENAME_KEY))

    workbook = Workbook(encoding='utf-8')
    sheet_number = 0
    for worksheet_data in parameters_dict.get(WORKSHEETS_DATA):
        _build_worksheet(worksheet_data,  workbook, sheet_number)
        sheet_number = sheet_number + 1

    _build_worksheet_parameters(workbook, parameters_dict.get(USER_KEY), parameters_dict.get(LIST_DESCRIPTION_KEY))
    response = HttpResponse(save_virtual_workbook(workbook), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet; charset=binary')
    response['Content-Disposition'] = "%s%s" % ("attachment; filename=", filename)

    return response


def _build_worksheet(worksheet_data, workbook, sheet_number):
    content = worksheet_data.get(CONTENT_KEY)

    a_worksheet = _create_worksheet(workbook,
                                   _create_worsheet_title(sheet_number, worksheet_data.get(WORKSHEET_TITLE_KEY)),
                                   sheet_number)
    _add_column_headers(worksheet_data.get(HEADER_TITLES_KEY), a_worksheet)
    _add_content(content, a_worksheet)
    _adjust_column_width(a_worksheet)
    _adapt_format_for_string_with_numbers(a_worksheet, content)
    _coloring_rows(a_worksheet, worksheet_data.get(COLORED_ROWS, None))
    _coloring_cols(a_worksheet, worksheet_data.get(COLORED_COLS, None))


def _add_column_headers(headers_title, worksheet1):
    worksheet1.append(headers_title)


def _add_content(content, a_worksheet_param):
    a_worksheet = a_worksheet_param
    for line in content:
        a_worksheet.append(_validate_fields(line))
    return a_worksheet


def _adjust_column_width(worksheet):
    for col in worksheet.columns:
        max_length = 0
        column = col[0].column  # Get the column name
        for cell in col:
            if cell.coordinate in worksheet.merged_cells:  # not check merge_cells
                continue
            try:  # Necessary to avoid error on empty cells
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        if adjusted_width > MAX_COL_WIDTH:
            adjusted_width = MAX_COL_WIDTH
            worksheet.column_dimensions[column].width = adjusted_width
        else:
            worksheet.column_dimensions[column].width = adjusted_width


def _build_filename(filename):
    return '%s.%s' % (filename, XLS_EXTENSION)


def _create_worksheet(workbook, title, sheet_num):
    if sheet_num == 0:
        worksheet1 = workbook.active
        worksheet1.title = title
    else:
        worksheet1 = workbook.create_sheet(title=title)

    return worksheet1


def _build_worksheet_parameters(workbook, a_user, list_description=None):
    worksheet_parameters = workbook.create_sheet(title=str(_('parameters')))
    today = datetime.date.today()
    worksheet_parameters.append([str(_('creation_date')), today.strftime('%d-%m-%Y')])
    worksheet_parameters.append([str(_('created_by')), str(a_user)])
    if list_description:
        worksheet_parameters.append([str(_('description')), list_description])
    _adjust_column_width(worksheet_parameters)
    return worksheet_parameters


def as_text(value):
    if value is None:
        return ""
    return str(value)


def _create_worsheet_title(sheet_number, worksheet_titles):
    current_worksheet_num = sheet_number + 1
    if worksheet_titles:
        return "{} - {}".format(current_worksheet_num, worksheet_titles)

    return "{} - {}{}".format(current_worksheet_num, _('worksheet'), current_worksheet_num)


def _is_valid(list_parameters):
    if list_parameters:
        return _is_checked_file_parameters_list(list_parameters) and _is_checked_worsheets_data(list_parameters)
    return False


def _adapt_format_for_string_with_numbers(worksheet1, worksheet_content):
    """
    Necessary, otherwise the string which contains only numbers considered as a number and set with a quote while
    looking at the input line
    """
    num_corresponding_row = FIRST_DATA_LINE
    for record in worksheet_content:
        num_corresponding_column = 1
        for element in record:
            if type(element) is str and re.match(r'^[0-9]+$', element):
                worksheet1.cell(column=num_corresponding_column,
                                row=num_corresponding_row).number_format = OPENPYXL_STRING_FORMAT
            num_corresponding_column = num_corresponding_column + 1
        num_corresponding_row = num_corresponding_row+1


def _is_checked_file_parameters_list(list_parameters):
    expected_keys = [LIST_DESCRIPTION_KEY,
                     FILENAME_KEY,
                     USER_KEY,
                     WORKSHEETS_DATA]
    return _compare_dicts(expected_keys, list_parameters)


def _compare_dicts(expected_keys, list_parameters):
    keys = list(list_parameters.keys())
    return len((list(set(expected_keys).intersection(set(keys))))) == len(expected_keys)


def _is_checked_worsheets_data(list_parameters):
    expected_keys = [CONTENT_KEY,
                     HEADER_TITLES_KEY,
                     WORKSHEET_TITLE_KEY]
    if list_parameters.get(WORKSHEETS_DATA) is None:
        return False
    else:
        for data in list_parameters.get(WORKSHEETS_DATA):
            if not _compare_dicts(expected_keys, data) or \
                    not _check_correct_number_of_fields(list_parameters.get(HEADER_TITLES_KEY),
                                                        list_parameters.get(CONTENT_KEY)):
                return False
        return True


def _check_correct_number_of_fields(header_titles, content):
    if header_titles and content:
        if len(header_titles) != len(content):
            return False
    return True


def _coloring_rows(ws, data):
    if data:
        for a_style in data.keys():
            row_numbers = data.get(a_style, None)
            if row_numbers:
                _set_row_style(a_style, row_numbers, ws)


def _set_row_style(key, row_numbers, ws):
    for index, row in enumerate(ws.iter_rows()):
        for r in row_numbers:
            if index == r:
                for cell in row:
                    cell.style = key


def _coloring_cols(ws, data):
    if data:
        for a_style in data.keys():
            col_numbers = data.get(a_style)
            if col_numbers:
                _set_col_style(a_style, col_numbers, ws)


def _set_col_style(a_style, col_numbers, ws):
    for index, row in enumerate(ws.iter_rows()):
        for cell in row:
            if cell.col_idx in col_numbers:
                cell.style = a_style


def _validate_fields(line):
    return [as_text(col_content) for col_content in line]


def translate(string_value):
    if type(string_value) == str and string_value:
        return str(_(string_value))
    elif type(string_value) == bool:
        if string_value:
            return _('true')
        return _('false')
    return None
