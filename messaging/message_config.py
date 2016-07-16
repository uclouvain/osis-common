##############################################################################
#
# OSIS stands for Open Student Information System. It's an application
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


def create_message_content(html_template_ref,
                           txt_template_ref,
                           tables,
                           receivers,
                           template_base_data,
                           subject_data):
    """

    :param html_template_ref:
    :param txt_template_ref:
    :param tables:
    :param receivers:
    :param template_base_data:
    :param subject_data:
    :return:
    """
    return {
        'html_template_ref':    html_template_ref,
        'txt_template_ref':     txt_template_ref,
        'tables':               tables,
        'receivers':            receivers,
        'template_base_data':   template_base_data,
        'subject_data':         subject_data,
    }


def create_table(table_template_name, header_txt, data):
    """

    :param table_template_name:
    :param header_txt:
    :param data:
    :return:
    """
    return {
        'table_template_name':  table_template_name,
        'header_txt':           header_txt,
        'data':                 data
    }


def create_receiver(receiver_id, receiver_email, receiver_lang):
    """

    :param receiver_id:
    :param receiver_email:
    :param receiver_lang:
    :return:
    """
    return {
        'receiver_id':      receiver_id,
        'receiver_email':   receiver_email,
        'receiver_lang':    receiver_lang
    }
