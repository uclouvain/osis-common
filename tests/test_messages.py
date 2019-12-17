##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2019 Université catholique de Louvain (http://www.uclouvain.be)
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
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from base.tests.factories.person import PersonFactory
from osis_common.messaging import mail_sender_classes
from osis_common.messaging import send_message, message_config
from osis_common.messaging.message_config import create_receiver, create_table, create_message_content
from osis_common.models import message_history
from osis_common.models.message_history import MessageHistory
from osis_common.models.message_template import MessageTemplate
from django.utils.translation import gettext_lazy as _


class MessagesTestCase(TestCase):

    fixtures = ['osis_common/fixtures/messages_tests.json']

    def setUp(self):
        self.connected_user = PersonFactory().user

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
        self.assertEqual(html_message_template.language, 'en', 'The language should exists')
        self.assertEqual(txt_message_template.language, 'en', 'The language should exists')

        # Lang does not exists
        html_message_template, txt_message_template = send_message._get_template_by_language_or_default(
            'pt-BR',
            html_message_templates,
            txt_message_templates)
        self.assertNotEqual(html_message_template.language, 'pt_BR', 'The language does not exists')
        self.assertNotEqual(txt_message_template.language, 'pt_BR', 'The language does not exists')
        self.assertEqual(html_message_template.language, settings.LANGUAGE_CODE, 'The default language is taken')
        self.assertEqual(txt_message_template.language, settings.LANGUAGE_CODE, 'The default language is taken')

    def test_send_messages(self):
        count_messages_before_send = len(message_history.MessageHistory.objects.all())
        receivers = self.__make_receivers()
        tables = (self.__make_table(),)
        template_base_data = {'learning_unit_name': 'DROI1100', }
        subject_data = {}
        message_content = create_message_content('assessments_scores_submission_html',
                                                 'assessments_scores_submission_txt',
                                                 tables,
                                                 receivers,
                                                 template_base_data,
                                                 subject_data)
        message_error = send_message.send_messages(
            message_content=message_content,
            connected_user=self.connected_user
        )
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
        message_error = send_message.send_messages(
            message_content=content_no_html_ref,
            connected_user=self.connected_user
        )
        self.assertIsNotNone(message_error, 'A message error should be sent')

        content_no_receivers = create_message_content('assessments_scores_submission_html',
                                                      'assessments_scores_submission_txt',
                                                      tables,
                                                      None,
                                                      template_base_data,
                                                      subject_data)
        message_error = send_message.send_messages(
            message_content=content_no_receivers,
            connected_user=self.connected_user
        )
        self.assertIsNotNone(message_error, 'A message error should be sent')

        content_wrong_html_ref = create_message_content('unknown_template_html',
                                                        'assessments_scores_submission_txt',
                                                        tables,
                                                        receivers,
                                                        template_base_data,
                                                        subject_data)
        message_error = send_message.send_messages(
            message_content=content_wrong_html_ref,
            connected_user=self.connected_user
        )
        self.assertIsNotNone(message_error, 'A message error should be sent')

    @patch('osis_common.messaging.send_message._build_and_send_message')
    @patch('osis_common.messaging.send_message._get_all_lang_templates')
    def test_build_and_send_messages_called_once_with_one_receiver(
            self, mock_get_all_lang_templates, mock_build_and_send_message):
        mock_get_all_lang_templates.return_value = 'template_html', 'template_txt'
        receiver = PersonFactory()
        receivers = [message_config.create_receiver(receiver.id, receiver.email, None)]
        msg_content = message_config.create_message_content('template_html', 'template_txt', [], receivers, {}, {})
        send_message.send_messages(msg_content)
        self.assertEqual(mock_build_and_send_message.call_count, 1)

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


class MailClassesTestCase(TestCase):
    def setUp(self):
        self.connected_person = PersonFactory()
        self.receiver = PersonFactory()
        self.receivers = [
            message_config.create_receiver(
                self.receiver.id,
                self.receiver.email,
                None
            )
        ]

    @patch('django.core.mail.message.EmailMessage.send')
    def test_message_history_mail_sender(self, mock_mail_send):
        mail_sender = mail_sender_classes.MessageHistorySender(
            receivers=self.receivers,
            reference="reference",
            connected_user=self.connected_person.user,
            subject="test subject",
            message="test message",
            html_message="<p>test html message</p>",
            from_email=settings.DEFAULT_FROM_EMAIL,
            attachment=None
        )
        mail_sender.send_mail()
        self.assertTrue(
            MessageHistory.objects.get(
                reference="reference",
                subject="test subject",
                content_txt="test message",
                content_html="<p>test html message</p>",
                receiver_person_id=self.receiver.pk,
                receiver_email=self.receiver.email,
            )
        )
        mock_mail_send.assert_not_called()

    @patch('logging.Logger.info')
    @patch('django.core.mail.message.EmailMessage.send')
    def test_generic_mail_sender(self, mock_mail_send, mock_logger):
        mail_sender = mail_sender_classes.GenericMailSender(
            receivers=self.receivers,
            reference="reference",
            connected_user=self.connected_person.user,
            subject="test subject",
            message="test message",
            html_message="<p>test html message</p>",
            from_email=settings.DEFAULT_FROM_EMAIL,
            attachment=None
        )
        mail_sender.send_mail()
        self.assertEqual(mock_mail_send.call_count, 1)
        log = mock_logger.call_args[0][0]
        self.assertEqual(
            log,
            'Sending mail to {} (MailSenderClass : GenericMailSender)'.format(settings.COMMON_EMAIL_RECEIVER)
        )

    @patch('logging.Logger.info')
    @patch('django.core.mail.message.EmailMessage.send')
    def test_connected_user_mail_sender(self, mock_mail_send, mock_logger):
        mail_sender = mail_sender_classes.ConnectedUserMailSender(
            receivers=self.receivers,
            reference="reference",
            connected_user=self.connected_person.user,
            subject="test subject",
            message="test message",
            html_message="<p>test html message</p>",
            from_email=settings.DEFAULT_FROM_EMAIL,
            attachment=None
        )
        mail_sender.send_mail()
        self.assertEqual(mock_mail_send.call_count, 1)
        log = mock_logger.call_args[0][0]
        self.assertEqual(
            log,
            'Sending mail to {} (MailSenderClass : ConnectedUserMailSender)'.format(self.connected_person.email)
        )

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('django.core.mail.message.EmailMessage.send')
    def test_connected_user_mail_sender_without_connected_user(self, mock_mail_send, mock_logger, mock_logger_error):
        mail_sender = mail_sender_classes.ConnectedUserMailSender(
            receivers=self.receivers,
            reference="reference",
            connected_user=None,
            subject="test subject",
            message="test message",
            html_message="<p>test html message</p>",
            from_email=settings.DEFAULT_FROM_EMAIL,
            attachment=None
        )
        mail_sender.send_mail()
        self.assertEqual(mock_mail_send.call_count, 1)

        log = mock_logger.call_args[0][0]
        self.assertEqual(
            log,
            'Sending mail to {} (MailSenderClass : ConnectedUserMailSender)'.format(settings.COMMON_EMAIL_RECEIVER)
        )

        error_log = mock_logger_error.call_args[0][0]
        self.assertEqual(
            error_log,
            'ConnectedUserMailSender class was used, but no connected_user was given. '
            'Email will be sent to the COMMON_EMAIL_RECEIVER (from settings) instead.'
        )

    @patch('logging.Logger.info')
    @patch('django.core.mail.message.EmailMessage.send')
    def test_mail_sender(self, mock_mail_send, mock_logger):
        mail_sender = mail_sender_classes.RealReceiverMailSender(
            receivers=self.receivers,
            reference="reference",
            connected_user=self.connected_person.user,
            subject="test subject",
            message="test message",
            html_message="<p>test html message</p>",
            from_email=settings.DEFAULT_FROM_EMAIL,
            attachment=None
        )
        mail_sender.send_mail()
        self.assertEqual(mock_mail_send.call_count, 1)
        log = mock_logger.call_args[0][0]
        self.assertEqual(
            log,
            'Sending mail to {} (MailSenderClass : RealReceiverMailSender)'.format(
                self.receivers[0].get('receiver_email')
            )
        )

    @patch('logging.Logger.error')
    def test_add_testing_information_to_contents_missing_email(self, mock_logger_error):
        connected_user_missing_email = PersonFactory(email="").user
        mail_sender = mail_sender_classes.ConnectedUserMailSender(
            receivers=self.receivers,
            reference="reference",
            connected_user=connected_user_missing_email,
            subject="test subject",
            message="test message",
            html_message="<p>test html message</p>",
            from_email=settings.DEFAULT_FROM_EMAIL,
            attachment=None
        )
        email_message = mail_sender.kwargs['message']

        dest_email = 'dest@gmail.com'
        mail_sender.real_receivers_list = [None, dest_email]

        receiver_email = 'receiver@gmail.com'
        mail_sender.original_receivers_list = [receiver_email, None]

        mail_sender_classes.add_testing_information_to_contents(mail_sender)

        error_log = mock_logger_error.call_args[0][0]
        self.assertEqual(
            error_log,
            'ConnectedUserMailSender class was used, but no connected_user email was given. '
            'Email will be sent to the COMMON_EMAIL_RECEIVER (from settings) instead.'
        )

        expected_message = "{} \n {}".format(
            _('This is a test email sent from OSIS, only sent to {new_dest_address}. '
              'Planned receivers were : {receivers_addresses}.').format(new_dest_address=dest_email,
                                                                        receivers_addresses=receiver_email),
            email_message)

        self.assertEqual(mail_sender.kwargs['message'], expected_message)
