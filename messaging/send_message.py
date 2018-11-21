##############################################################################
#
# OSIS stands for Open Student Information System. It's an application
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

"""
Utility files for message sending
"""
from html import unescape

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from django.conf import settings
from osis_common.models import message_history as message_history_mdl
from osis_common.models import message_template as message_template_mdl
from django.utils.translation import ugettext as _
from django.utils import translation

import logging

logger = logging.getLogger(settings.SEND_MAIL_LOGGER)


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


def __send_messages(html_message_template, txt_message_template, html_data, txt_data, receivers, subject, attachment,
                    force_sending_outside_production=False):
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
    :param attachment: An attachment to the message.
    :param force_sending_outside_production: Send the message to real receiver outside production environment
    """
    html_data['signature'] = render_to_string('messaging/html_email_signature.html', {
        'logo_mail_signature_url': settings.LOGO_EMAIL_SIGNATURE_URL,
        'logo_osis_url': settings.LOGO_OSIS_URL})
    html_message = Template(html_message_template.template).render(Context(html_data))
    txt_message = Template(txt_message_template.template).render(Context(txt_data))
    __send_and_save(receivers=receivers,
                    subject=unescape(strip_tags(subject)),
                    message=unescape(strip_tags(txt_message)),
                    html_message=html_message, from_email=settings.DEFAULT_FROM_EMAIL,
                    attachment=attachment,
                    force_sending_outside_production=force_sending_outside_production)


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
    :param receiver receiver of the message
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
    :param kwargs List of arguments used by the django EmailMultiAlternative class.
    The recipient_list argument is taken form the persons list.
    """
    recipient_list = []
    if receivers:
        for receiver in receivers:
            if not settings.EMAIL_PRODUCTION_SENDING:
                if kwargs.get('force_sending_outside_production'):
                    logger.info('Sending mail not in production to {}'.format(receiver.get('receiver_email')))
                    recipient_list.append(receiver.get('receiver_email'))
                else:
                    logger.info('Sending mail not in production to {}'.format(settings.COMMON_EMAIL_RECEIVER))
                    recipient_list.append(settings.COMMON_EMAIL_RECEIVER)
            elif receiver.get('receiver_email'):
                logger.info('Sending mail in production to {}'.format(receiver.get('receiver_email')))
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
        msg = EmailMultiAlternatives(kwargs.get('subject'), kwargs.get('message'), kwargs.get('from_email'),
                                     recipient_list, attachments=__get_attachments(kwargs))
        msg.attach_alternative(kwargs.get('html_message'), "text/html")
        msg.send()


def __get_attachments(attributes_message):
    attachment = attributes_message.get("attachment")
    if attachment:
        return [attachment]
    return None


def __make_tables_template_data(tables, lang_code):
    """
    Make table from data and header to insert into messages.
    :param tables: The lists of tables to inserts into template.
    Table are created by message_config.create_table function
    :return: The html tables and txt table to insert in each type of messages
    """
    html_templates_data = {}
    txt_templates_data = {}
    if tables:
        for table in tables:
            table_template_name = table.get('table_template_name')
            table_header_txt = table.get('header_txt')
            table_data = table.get('data')
            table_data_translatable = table.get('data_translatable')

            with translation.override(lang_code):
                table_headers = [_(txt) for txt in table_header_txt]
            table_data = __apply_translation_on_table_data(table_data, lang_code, table_header_txt,
                                                           table_data_translatable)
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


def __apply_translation_on_table_data(table_data, lang_code, table_header_txt, table_data_translatable):
    """
       Apply translation on data table
       :param table_data             :  The lists of tuple which compose the table data.
       :param lang_code              :  The language_code we want for translation
       :param table_header_txt       :  The headers [not translated] of table
       :param table_data_translatable:  The headers [not translated] of table
       :return: The data table which translation apply
    """
    table_data_translated = []
    col_indexes_to_translate = [table_header_txt.index(column_to_translated) for column_to_translated in
                                table_data_translatable if column_to_translated in table_header_txt]
    for row in table_data:
        with translation.override(lang_code):
            row_translated = __apply_translation_on_row_table_data(row, col_indexes_to_translate)
        table_data_translated.append(row_translated)
    return table_data_translated


def __apply_translation_on_row_table_data(row_data, col_indexes_to_translate):
    """
       Apply translation on row data table
       :param row_data                              :  The tuple which compose a row data.
       :param col_indexes_to_translate              :  The language_code we want for translation
       :return: The row table which translation apply
    """
    row_translated = []
    for col_idx, col_data in enumerate(row_data):
        if col_idx in col_indexes_to_translate and col_data is not None:
            row_translated.append(_(col_data))
        else:
            row_translated.append(col_data)
    return tuple(row_translated)


def send_messages(message_content, force_sending_outside_production=False):
    """
    Send messages according to the message_content
    :param message_content: The message content and configuration dictionnary
    message_content is created by message_config.create_message_content function
    :param force_sending_outside_production Send the message to real receivers outside production environment
    :return: An error message if something wrong,None else
    """
    html_template_ref = message_content.get('html_template_ref', None)
    txt_template_ref = message_content.get('txt_template_ref', None)
    tables = message_content.get('tables', None)
    receivers = message_content.get('receivers', None)
    template_base_data = message_content.get('template_base_data', None)
    subject_data = message_content.get('subject_data', None)
    attachment = message_content.get('attachment', None)
    if not html_template_ref:
        logger.error("No html template found in message content; no message/mail has been sent.")
        return _('No email has been sent because a technical error occured.')
    if not receivers:
        logger.warning("No receivers found ; no message/mail has been sent.")
        return _('No email has been sent because a technical error occured.')
    html_message_templates, txt_message_templates = _get_all_lang_templates([html_template_ref,
                                                                             txt_template_ref])
    if not html_message_templates:
        return _(
            'No messages were sent : the message template %(html_template_ref)s does not exist.'
        ).format(
            {
                'html_template_ref': html_template_ref
            }
        )

    for lang_code, receivers in __map_receivers_by_languages(receivers).items():
        html_table_data, txt_table_data = __make_tables_template_data(tables, lang_code)
        html_message_template, txt_message_template = _get_template_by_language_or_default(lang_code,
                                                                                           html_message_templates,
                                                                                           txt_message_templates)
        if subject_data:
            subject = html_message_template.subject.format(**subject_data)
        else:
            subject = html_message_template.subject
        html_data = template_base_data.copy()
        html_data.update(html_table_data)
        txt_data = template_base_data.copy()
        txt_data.update(txt_table_data)
        html_data['signature'] = render_to_string('messaging/html_email_signature.html', {
            'logo_mail_signature_url': settings.LOGO_EMAIL_SIGNATURE_URL,
            'logo_osis_url': settings.LOGO_OSIS_URL, })
        __send_messages(html_message_template, txt_message_template, html_data, txt_data, receivers,
                        subject, attachment, force_sending_outside_production)

    return None
