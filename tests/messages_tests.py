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
from django.conf import settings
from django.test import TestCase
from osis_common.messaging import send_message
from osis_common.models.message_template import MessageTemplate


class MessagesTestCase(TestCase):

    fixtures = ['osis_common/fixtures/messages_tests.json']

    def test_get_all_lang_templates(self):
        txt_message_templates, html_message_templates = send_message.__get_all_lang_templates(
            ['assessments_scores_submission_html',
             'assessments_scores_submission_txt'])

        self.assertEqual(len(txt_message_templates), 2, '2 txt templates')
        self.assertEqual(len(html_message_templates), 2, '2 html templates')
        for key, value in txt_message_templates:
            self.assertIsInstance(value, MessageTemplate, 'value of the dict is a MessageTemplate object')
        for key, value in html_message_templates:
            self.assertIsInstance(value, MessageTemplate, 'value of the dict is a MessageTemplate object')

    def test_get_template_by_language_or_default(self):
        txt_message_templates, html_message_templates = send_message.__get_all_lang_templates(
            ['assessments_scores_submission_html',
             'assessments_scores_submission_txt'])
        # Lang exists
        html_message_template, txt_message_template = send_message.__get_template_by_language_or_default(
            'en', html_message_templates, txt_message_templates)
        self.assertEquals(html_message_template.language, 'en', 'The language should exists')
        self.assertEquals(txt_message_templates.language, 'en', 'The language should exists')

        # Lang does not exists
        html_message_template, txt_message_template = send_message.__get_template_by_language_or_default(
            'pt_BR',
            html_message_templates,
            txt_message_templates)
        self.assertNotEqual(html_message_template.language, 'pt_BR', 'The language does not exists')
        self.assertNotEqual(txt_message_templates.language, 'pt_BR', 'The language does not exists')
        self.assertEquals(html_message_template.language, settings.LANGUAGE_CODE, 'The default language is taken')
        self.assertEquals(txt_message_templates.language, settings.LANGUAGE_CODE, 'The default language is taken')