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

"""
Utility class used to create a message content.
The message content is used to send a message to one or more receiver.
"""

def create_message_content(html_template_ref,
                           txt_template_ref,
                           tables,
                           receivers,
                           template_base_data,
                           subject_data):
    """
    Create a message_content dict , used by the send_message function.
    The message_content dict contains all the data needed to create and send the message to a list of receiver.

    :param html_template_ref: The html template reference.
    :param txt_template_ref: The txt template reference
    :param tables: The tables to be inserted as template data.
    It is a list of 'table' created by the create_table function
    :param receivers: The receivers of the message.
    It is a list of receivers created by the crete_receiver function
    :param template_base_data: The data used by the template. ({{ my_data }} in templates)
    It is a dict like all context data used by django templates
    :param subject_data: The data used to format the subject.
    The subject is a string with formated param.
    The subject data is a dict, containing all key/value of the formated string.
    (Ex:
    str = 'This is a {param1} using {param2}'
    params = {'param1' : 'String', 'param2': 'dict formating'}
    print(str.format(**params)) => This is a String using dict formating'
    )
    :return: The message_content dict used by the send_message function
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
    Create à dict that represent the table of data hat has to be inserted in a message template.
    :param table_template_name:The name of the param in the template used to represent the table.
    :param header_txt: The header of the table, as a list of strings
    :param data: The data for each row of the table as list of tuples
    :return: The dict representing the table used in the formating of the message
    """
    return {
        'table_template_name':  table_template_name,
        'header_txt':           header_txt,
        'data':                 data
    }


def create_receiver(receiver_id, receiver_email, receiver_lang):
    """
    Create a receiver dict used by the sending message function.
    :param receiver_id: The id of the receiver (usually person.id)
    :param receiver_email: The eail of the receiver.
    :param receiver_lang: The language of the receiver
    :return: The dict representing the receiver of a message
    """
    return {
        'receiver_id':      receiver_id,
        'receiver_email':   receiver_email,
        'receiver_lang':    receiver_lang
    }
