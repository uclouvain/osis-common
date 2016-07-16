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
Utility files for message sending
"""
from html import unescape

from django.core.mail import send_mail
from django.template import Template, Context
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from django.conf import settings
from osis_common.models import message_history as message_history_mdl
from osis_common.models import message_template as message_template_mdl
from django.utils.translation import ugettext as _
from django.utils import translation


def _get_all_lang_templates(templates_refs):
    """
    Get all the templates, for all languages, according to the list of template reference.
    :param templates_refs: The list of templates references we want to retrieve
    :return: A tuple of dictionnary with language as key and template as value.
    The tuple length and items depends on the list of references.
    """
    return ({template.language: template for template in
             list(message_template_mdl.find_by_reference(template_ref))} for template_ref in templates_refs)


def _get_template_by_language_or_default(lang_code, html_message_templates, txt_message_templates):
    """
    Get the txt and html templates by language if the lang_code exists in templates dictionnaries.
    If not , the default language template is taken.
    :param lang_code: The language_code we want for the template
    :param html_message_templates: html templates dictionnary
    :param txt_message_templates:  txt template dictionnary
    :return: The html and txt templates
    """
    if lang_code in html_message_templates:
        html_message_template = html_message_templates.get(lang_code)
    else:
        html_message_template = html_message_templates.get(settings.LANGUAGE_CODE)
    if lang_code in txt_message_templates:
        txt_message_template = txt_message_templates.get(lang_code)
    else:
        txt_message_template = txt_message_templates.get(settings.LANGUAGE_CODE)
    return html_message_template, txt_message_template


def __send_messages(html_message_template, txt_message_template, html_data, txt_data, receivers, subject):
    """
    Send a message to a list of person ,with txt and html format.
    The messages are build according templates and data (dictionnary of template vars).
    Messages are sent by mail and saved in history.
    :param html_message_template: The html template of the message
    :param txt_message_template: The txt template of the message
    :param html_data: the data for the html_template
    :param txt_data: the data for the txt template
    :param receivers: The receivers list of the message
    :param subject: The subject of the message
    """
    html_data['signature'] = render_to_string('messaging/html_email_signature.html', {
        'logo_mail_signature_url': settings.LOGO_EMAIL_SIGNATURE_URL,
        'logo_osis_url': settings.LOGO_OSIS_URL})
    html_message = Template(html_message_template.template).render(Context(html_data))
    txt_message = Template(txt_message_template.template).render(Context(txt_data))
    __send_and_save(receivers=receivers,
                    subject=unescape(strip_tags(subject)),
                    message=unescape(strip_tags(txt_message)),
                    html_message=html_message, from_email=settings.DEFAULT_FROM_EMAIL)


def __render_table_template_as_string(table_headers, table_rows, html_format):
    """
     Render the table template as a string.
     If htmlformat is True , render the html table template , else the txt table template
     Used to create dynamically a table of data to insert into email template.
     :param table_headers: The header of the table as a list of Strings
     :param table_rows: The content of each row as a list of item list
     :param html_format True if you want the html template , False if you want the txt template
    """
    if html_format:
        template = 'messaging/html_email_table_template.html'
    else:
        template = 'messaging/txt_email_table_template.html'
    data = {
        'table_headers': table_headers,
        'table_rows': table_rows
    }
    return render_to_string(template, data)


def __map_receivers_by_languages(receivers):
    """
    Convert a list of persons into a dictionnary langage_code: list_of_persons ,
    according to the language of the person.
    :param receivers the list of receivers we want to map
    """
    lang_dict = {lang[0]: [] for lang in settings.LANGUAGES}
    for receiver in receivers:
        if receiver.get('receiver_lang', None) in lang_dict.keys():
            lang_dict[receiver.get('receiver_lang')].append(receiver)
        else:
            lang_dict[settings.LANGUAGE_CODE].append(receiver)
    return lang_dict


def send_again(receiver, message_history_id):
    """
    send a message from message history again
    :param message_history_id The id of the message history to send again
    :return the sent message
    """
    message_history = message_history_mdl.find_by_id(message_history_id)
    __send_and_save(receivers=(receiver, ),
                    reference=message_history.reference,
                    subject=message_history.subject,
                    message=message_history.content_txt,
                    html_message=message_history.content_html,
                    from_email=settings.DEFAULT_FROM_EMAIL)
    return message_history


def __send_and_save(receivers, reference=None, **kwargs):
    """
    Send the message :
    - by mail if person.mail exists
    Save the message in message_history table
    :param receivers List of the receivers of the message
    :param reference business reference of the message
    :param kwargs List of arguments used by the django send_mail method.
    The recipient_list argument is taken form the persons list.
    """
    recipient_list = []
    if receivers:
        for receiver in receivers:
            if receiver.get('receiver_email'):
                recipient_list.append(receiver.get('receiver_email'))
            message_history = message_history_mdl.MessageHistory(
                reference=reference,
                subject=kwargs.get('subject'),
                content_txt=kwargs.get('message'),
                content_html=kwargs.get('html_message'),
                receiver_id=receiver.get('receiver_id'),
                sent=timezone.now() if receiver.get('receiver_email') else None
            )
            message_history.save()
        send_mail(recipient_list=recipient_list, **kwargs)


def __make_tables_template_data(tables, lang_code):
    """
    Make table from data and header to insert into messages.
    :param tables: The lists of tables to inserts into template.
    Table are created by message_config.create_table function
    :return: The html tables and txt table to insert in each type of messages
    """
    html_templates_data = {}
    txt_templates_data = {}
    for table in tables:
        table_template_name = table.get('table_template_name')
        table_header_txt = table.get('header_txt')
        with translation.override(lang_code):
            table_headers = (_(txt) for txt in table_header_txt)
        table_data = table.get('data')
        table_html = __render_table_template_as_string(
            table_headers,
            table_data,
            True
        )
        table_txt = __render_table_template_as_string(
            table_headers,
            table_data,
            False
        )
        html_templates_data[table_template_name] = table_html
        txt_templates_data[table_template_name] = table_txt
    return html_templates_data, txt_templates_data


def send_messages(message_content):
    """
    Send messages according to the message_content
    :param message_content: The message content and configuration dictionnary
    message_content is created by message_config.create_message_content function
    :return: An error message if something wrong,None else
    """
    html_template_ref = message_content.get('html_template_ref', None)
    txt_template_ref = message_content.get('txt_template_ref', None)
    tables = message_content.get('tables', None)
    receivers = message_content.get('receivers', None)
    template_base_data = message_content.get('template_base_data', None)
    subject_data = message_content.get('subject_data', None)
    if not (html_template_ref and receivers and subject_data):
        return _('message_content_error')
    html_message_templates, txt_message_templates = _get_all_lang_templates([html_template_ref,
                                                                             txt_template_ref])
    if not html_message_templates:
        return _('template_error').format(html_template_ref)

    for lang_code, receivers in __map_receivers_by_languages(receivers).items():
        html_table_data, txt_table_data = __make_tables_template_data(tables, lang_code)
        html_message_template, txt_message_template = _get_template_by_language_or_default(lang_code,
                                                                                           html_message_templates,
                                                                                           txt_message_templates)
        subject = html_message_template.subject.format(subject_data)
        html_data = template_base_data.copy()
        html_data.update(html_table_data)
        txt_data = template_base_data.copy()
        txt_data.update(txt_table_data)
        html_data['signature'] = render_to_string('messaging/html_email_signature.html', {
            'logo_mail_signature_url': settings.LOGO_EMAIL_SIGNATURE_URL,
            'logo_osis_url': settings.LOGO_OSIS_URL, })
        __send_messages(html_message_template, txt_message_template, html_data, txt_data, receivers, subject)

    return None
