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
from django.conf import settings
from django.test import TestCase
from osis_common.messaging.send_message import send_again
from osis_common.models import message_history
from osis_common.messaging import send_message
from osis_common.messaging.message_config import create_receiver, create_table, create_message_content
from osis_common.models.message_template import MessageTemplate


class MessagesTestCase(TestCase):

    fixtures = ['osis_common/fixtures/messages_tests.json']

    def test_get_all_lang_templates(self):
        txt_message_templates, html_message_templates = send_message._get_all_lang_templates(
            ['assessments_scores_submission_html',
             'assessments_scores_submission_txt'])

        self.assertEqual(len(txt_message_templates), 2, '2 txt templates')
        self.assertEqual(len(html_message_templates), 2, '2 html templates')
        for key, value in txt_message_templates.items():
            self.assertIsInstance(value, MessageTemplate, 'value of the dict is a MessageTemplate object')
        for key, value in html_message_templates.items():
            self.assertIsInstance(value, MessageTemplate, 'value of the dict is a MessageTemplate object')

    def test_get_template_by_language_or_default(self):
        txt_message_templates, html_message_templates = send_message._get_all_lang_templates(
            ['assessments_scores_submission_html',
             'assessments_scores_submission_txt'])
        # Lang exists
        html_message_template, txt_message_template = send_message._get_template_by_language_or_default(
            'en', html_message_templates, txt_message_templates)
        self.assertEquals(html_message_template.language, 'en', 'The language should exists')
        self.assertEquals(txt_message_template.language, 'en', 'The language should exists')

        # Lang does not exists
        html_message_template, txt_message_template = send_message._get_template_by_language_or_default(
            'pt-BR',
            html_message_templates,
            txt_message_templates)
        self.assertNotEqual(html_message_template.language, 'pt_BR', 'The language does not exists')
        self.assertNotEqual(txt_message_template.language, 'pt_BR', 'The language does not exists')
        self.assertEquals(html_message_template.language, settings.LANGUAGE_CODE, 'The default language is taken')
        self.assertEquals(txt_message_template.language, settings.LANGUAGE_CODE, 'The default language is taken')

    def test_send_messages(self):
        count_messages_before_send = len(message_history.MessageHistory.objects.all())
        receivers = self.__make_receivers()
        tables = (self.__make_table(),)
        template_base_data = {'learning_unit_name': 'DROI1100', }
        subject_data = ('DROI1100', )
        message_content = create_message_content('assessments_scores_submission_html',
                                                 'assessments_scores_submission_txt',
                                                 tables,
                                                 receivers,
                                                 template_base_data,
                                                 subject_data)
        message_error = send_message.send_messages(message_content)
        self.assertIsNone(message_error, 'No message error should be sent')
        count_messages_after_send_again = len(message_history.MessageHistory.objects.all())
        self.assertTrue(count_messages_after_send_again == count_messages_before_send + 5,
                        '5 messages should have been sent')

        content_no_html_ref = create_message_content(None,
                                                     'assessments_scores_submission_txt',
                                                     tables,
                                                     receivers,
                                                     template_base_data,
                                                     subject_data)
        message_error = send_message.send_messages(content_no_html_ref)
        self.assertIsNotNone(message_error, 'A message error should be sent')
        content_no_receivers = create_message_content('assessments_scores_submission_html',
                                                      'assessments_scores_submission_txt',
                                                      tables,
                                                      None,
                                                      template_base_data,
                                                      subject_data)
        message_error = send_message.send_messages(content_no_receivers)
        self.assertIsNotNone(message_error, 'A message error should be sent')
        content_no_subject_data = create_message_content('assessments_scores_submission_html',
                                                         'assessments_scores_submission_txt',
                                                         tables,
                                                         receivers,
                                                         template_base_data,
                                                         None)
        message_error = send_message.send_messages(content_no_subject_data)
        self.assertIsNotNone(message_error, 'A message error should be sent')
        content_wrong_html_ref = create_message_content('unknown_template_html',
                                                        'assessments_scores_submission_txt',
                                                        tables,
                                                        receivers,
                                                        template_base_data,
                                                        subject_data)
        message_error = send_message.send_messages(content_wrong_html_ref)
        self.assertIsNotNone(message_error, 'A message error should be sent')

    def test_send_again(self):
        count_messages_before_send_again = len(message_history.MessageHistory.objects.all())
        message = message_history.MessageHistory.objects.get(id=1)
        receiver = create_receiver(message.receiver_id, 'receiver_new@mail.org', 'fr-BE')
        message = send_again(receiver, message.id)
        self.assertIsNotNone(message, 'Message history should have been sent again')
        count_messages_after_send_again = len(message_history.MessageHistory.objects.all())
        self.assertTrue(count_messages_after_send_again == count_messages_before_send_again + 1,
                        'It should be {} messges in messages history'.format(count_messages_before_send_again + 1))

    def __make_receivers(self):
        receiver1 = create_receiver(1, 'receiver1@email.org', 'fr-BE')
        receiver2 = create_receiver(2, 'receiver2@email.org', 'fr-BE')
        receiver3 = create_receiver(3, 'receiver3@email.org', 'en')
        receiver4 = create_receiver(4, 'receiver4@email.org', 'en')
        receiver5 = create_receiver(5, 'receiver1@email.org', 'pt-BR')
        return receiver1, receiver2, receiver3, receiver4, receiver5

    def __make_table(self):
        table_headers = ('acronym', 'session_title', 'registration_number',
                         'lastname', 'firstname', 'score', 'documentation')
        table_data = self.__make_table_data()
        return create_table('enrollments', table_headers, table_data)

    def __make_table_data(self):
        data1 = ('DROI1BA', 1, '001', 'Person1', 'FirstName1', '12', None)
        data2 = ('DROI1BA', 2, '002', 'Person2', 'FirstName2', '13', None)
        data3 = ('DROI1BA', 3, '003', 'Person3', 'FirstName3', '14', None)
        return [data1, data2, data3]
