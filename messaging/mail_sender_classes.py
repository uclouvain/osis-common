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
import abc

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from osis_common.models import message_history as message_history_mdl

import logging

logger = logging.getLogger(settings.SEND_MAIL_LOGGER)


class MailSenderInterface(abc.ABC):
    def __init__(self, receivers, reference, connected_user=None, **kwargs):
        self.receivers = receivers
        self.reference = reference
        self.connected_user = connected_user
        self.kwargs = kwargs

    @abc.abstractmethod
    def send_mail(self):
        pass

    def create_message_history(self):
        for receiver in self.receivers:
            message_history_mdl.MessageHistory.objects.create(
                reference=self.reference,
                subject=self.kwargs.get('subject'),
                content_txt=self.kwargs.get('message'),
                content_html=self.kwargs.get('html_message'),
                receiver_id=receiver.get('receiver_id'),
                sent=timezone.now() if receiver.get('receiver_email') else None
            )

    def add_testing_informations_to_contents(self, original_receivers_addresses, replacement_receiver):
        testing_informations = _(
            "This is a test email sent from OSIS, only sent to {new_dest_address}."
            "Planned recipients were : {receivers_addresses}."
        ).format(
            new_dest_address=replacement_receiver,
            receivers_addresses=', '.join(original_receivers_addresses)
        )

        self.kwargs['message'] = "{testing_informations} \n {original_message}".format(
            testing_informations=testing_informations,
            original_message=self.kwargs.get('message')
        )
        self.kwargs['html_message'] = "<p>{testing_informations}</p> {original_message}".format(
            testing_informations=testing_informations,
            original_message=self.kwargs.get('html_message')
        )

    def build_and_send_msg(self, recipient_list):
        msg = EmailMultiAlternatives(
            subject=self.kwargs.get('subject'),
            body=self.kwargs.get('message'),
            from_email=self.kwargs.get('from_email'),
            to=recipient_list,
            attachments=_get_attachments(self.kwargs)
        )
        msg.attach_alternative(self.kwargs.get('html_message'), "text/html")
        logger.info(
            'Sending mail to {} (MailSenderClass : {})'.format(
                ', '.join(recipient_list),
                self.__class__.__name__
            )
        )
        msg.send()


class FallbackMailSender(MailSenderInterface):
    """
    Do not send actual email
    Log into message_history table
    """

    def send_mail(self):
        self.create_message_history()


class GenericMailSender(MailSenderInterface):
    """
    Send email to a generic email address (settings.COMMON_EMAIL_RECEIVER)
    Log into message_history table
    """

    def send_mail(self):
        replacement_receiver = settings.COMMON_EMAIL_RECEIVER
        original_receivers_addresses = [
            receiver.get('receiver_email') for receiver in self.receivers if receiver.get('receiver_email')
        ]
        self.add_testing_informations_to_contents(original_receivers_addresses, replacement_receiver)

        self.create_message_history()

        recipients_list = [replacement_receiver]
        self.build_and_send_msg(recipients_list)


class ConnectedUserMailSender(MailSenderInterface):
    """
    Send email to the email address of the connected user
    Log into message_history table
    """
    def __init__(self, receivers, reference, connected_user=None, **kwargs):
        if not connected_user:
            raise AttributeError('The attribute connected_user is mandatory to use the ConnectedUserMailSender class')

        super().__init__(receivers, reference, connected_user, **kwargs)

    def send_mail(self):
        replacement_receiver = self.connected_user.person.email
        original_receivers_addresses = [
            receiver.get('receiver_email') for receiver in self.receivers if receiver.get('receiver_email')
        ]
        self.add_testing_informations_to_contents(original_receivers_addresses, replacement_receiver)

        self.create_message_history()

        recipients_list = [replacement_receiver]
        self.build_and_send_msg(recipients_list)


class MailSender(MailSenderInterface):
    """
   Send email to the email address of the real recipient
    Log into message_history table
   """

    def send_mail(self):
        self.create_message_history()

        recipients_list = [
            receiver.get('receiver_email') for receiver in self.receivers if receiver.get('receiver_email')
        ]
        self.build_and_send_msg(recipients_list)


def _get_attachments(attributes_message):
    attachment = attributes_message.get("attachment")
    if attachment:
        return [attachment]
    return None
