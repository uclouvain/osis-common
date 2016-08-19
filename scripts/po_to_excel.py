#!/usr/bin/env python3
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
"""
Import all data from the .po files (translation files) to a .xlsl file (excel file).
The format of the excel file is the following one:

KEY ENGLISH_TRANSLATION  FRENCH_TRANSLATION   ENGLISH_MODIFIED_TRANSLATION FRENCH_MODIFIED_TRANSLATION

Where KEY is the "msgid" value of the .po files.
ENGLISH_TRANSLATION  and FRENCH_TRANSLATION are the "msgstr" values of the english and french .po files
respectively.
ENGLISH_MODIFIED_TRANSLATION and FRENCH_MODIFIED_TRANSLATION are empty columns used to write correction of the
english and french translations of the .po files.
"""
import xlsxwriter
from osis_common.scripts import sort_po_files


def parse_file(file):
    """
    Do the same thing as parse_file of the "sort_po_files" file.
    But don't return the header.
    :param file: File object to be parsed
    :return: a dictionnary of key value
    """
    dic, head = sort_po_files.parse_file(file)
    return dic


def write_header(worksheet, header_data, format=None):
    """
    Writhe the header to the worksheet.
    :param worksheet: worksheet object
    :param format: Format object.
    :param header_data: an array of string
    :return:
    """
    write_row(worksheet, header_data, format=format)


def write_row(worksheet, data_to_write, row=0, column=0, format=None):
    """
    Write data to the worksheet.
    :param worksheet:  worksheet object
    :param data_to_write: an array of string. One string by column.
    :param row: row number to write to
    :param column: column to start writing to
    :param format:
    :return:
    """
    for item in data_to_write:
        worksheet.write(row, column, item, format)
        column += 1


def format_string(string_to_format):
    """
    Format the string.
    :param string_to_format: a string
    :return: the formatted string
    """
    formatted_string = string_to_format.strip().strip('"')
    return formatted_string



print("Create a workbook and add a worksheet")
workbook = xlsxwriter.Workbook("translations.xlsx")
worksheet = workbook.add_worksheet()

print("Initialize formats")
bold = workbook.add_format({'bold': True})

# Header
header = ["Key", "English", "French", "English Modification", "French Modification"]

# Files
list_files_path = ["/home/ndizera/workspace/work/osis-portal/base/locale/en/LC_MESSAGES/django.po",
                   "/home/ndizera/workspace/work/osis-portal/base/locale/fr_BE/LC_MESSAGES/django.po"]
# List of path to the translation files (one by language) by module.

print("Fetch data")
list_data = []  # List of dictionary (one by language).
for file_path in list_files_path:
    with open(file_path) as f:
        dic = parse_file(f)  # Dictionary where the key is the msgid and value is the msgstr.
        list_data.append(dic)

print("Write to worksheet")

print("Write header")
write_header(worksheet, header, bold)

print("Write translations")
list_data_copy = list(map(dict.copy, list_data))

row = 1
for x in range(0, len(list_data)):
    for key in list(list_data[x].keys()):
        data_to_write = [format_string(key)]
        for dic in list_data_copy:
            value = dic.pop(key, " ")
            value = format_string(value)
            data_to_write.append(value)
        write_row(worksheet, data_to_write, row=row)
        row += 1
    list_data = list_data_copy

print("Close")
workbook.close()






