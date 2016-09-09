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


Usage
cd BASE_DIR
python3 manage.py shell
from osis_common.scripts import po_to_excel
"""
from django.conf import settings
import xlsxwriter
import os
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


def fetch_data(list_files_path):
    """
    Fetch the data to be written to the excel file.
    For that we convert each translation file (.po) to a dictionary
    where the key is the msgid and value the corresponding msgstr.
    :param list_files_path: list of string which are valid path to .po files
    :return: a list of dictionary where key is the msgid and value the msgstr
            (see .po files)
    """
    list_data = []  # List of dictionary (one by language).
    for file_path in list_files_path:
        with open(file_path) as f:
            dic = parse_file(f)  # Dictionary where the key is the msgid and value is the msgstr.
            list_data.append(dic)
    return list_data


def find_directories():
    """
    Find directory that contains translation files.
    :return: list of string
    """
    list_dirs_path = []
    for root, dirs, files in os.walk(settings.BASE_DIR):
        list_dirs_path = dirs
        break
    return list_dirs_path


def get_file_path(direcory_name, lang_list):
    """
    Get the file path of the translation file for that language
    for the directory.
    :param direcory_name: a string
    :param lang_list: as tring
    :return: expected file path
    """
    return "".join(["./", direcory_name, "/locale/", lang_list, "/LC_MESSAGES/django.po"])


def files_exist(list_files_path):
    """
    Return true if all files exist.
    :param list_files_path: list of string
    :return: boolean
    """
    for file_path in list_files_path:
        if not os.path.exists(file_path):
            return False
    return True

list_directories = find_directories()
language_list = ["en", "fr_BE"]
header = ["Key", "English", "French", "English Proposition", "French Proposition"]

for dir_name in list_directories:
    # List of path to the translation files (one by language) by module.
    list_files_path = list(map(lambda language: get_file_path(dir_name, language), language_list))
    if not files_exist(list_files_path):
        continue

    print("".join(["Directory: ", dir_name]))

    # Create a workbook and add a worksheet
    workbook = xlsxwriter.Workbook("".join([dir_name, ".xlsx"]))
    worksheet = workbook.add_worksheet()

    # Initialize formats
    bold = workbook.add_format({'bold': True})

    # Fetch data
    list_data = fetch_data(list_files_path)  # List of dictionary (one by language).

    # Write header
    write_header(worksheet, header, bold)

    # Write translations
    list_data_copy = list(map(dict.copy, list_data))

    # Need to iterate over all dictionary as it could happen that two translation files
    # don't have the same content (one has more translations for example)
    row = 1
    for x in range(0, len(list_data)):
        sorted_keys = sorted(list(list_data[x].keys()))
        for key in sorted_keys:
            data_to_write = [format_string(key)]
            # Pop the value corresponding to the key in each dictionary as to not iterate
            # over it again.
            for dic in list_data_copy:
                value = dic.pop(key, " ")
                value = format_string(value)
                data_to_write.append(value)
            write_row(worksheet, data_to_write, row=row)
            row += 1
        list_data = list_data_copy  # Fix for if two translations (.po) don't have the same content.

    # Close file
    workbook.close()






