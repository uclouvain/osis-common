##############################################################################
#
# OSIS stands for Open Student Information System. It's an application
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
import abc
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from osis_common.models import message_history as message_history_mdl

logger = logging.getLogger(settings.SEND_MAIL_LOGGER)


class MailSenderInterface(abc.ABC):
    @abc.abstractmethod
    def send_mail(self):
        pass


class MasterMailSender(MailSenderInterface):
    def __init__(self, receivers, reference, connected_user=None, **kwargs):
        self.receivers = receivers
        self.reference = reference
        self.connected_user = connected_user
        self.kwargs = kwargs
        self.original_receivers_list = self.get_original_receivers_list()
        self.real_receivers_list = self.get_real_receivers_list()

    def get_original_receivers_list(self):
        return [
            receiver.get('receiver_email') for receiver in self.receivers if receiver.get('receiver_email')
        ]

    def get_real_receivers_list(self):
        return []

    def send_mail(self):
        msg = EmailMultiAlternatives(
            subject=self.kwargs.get('subject'),
            body=self.kwargs.get('message'),
            from_email=self.kwargs.get('from_email'),
            to=self.real_receivers_list,
            attachments=_get_attachments(self.kwargs)
        )
        msg.attach_alternative(self.kwargs.get('html_message'), "text/html")
        logger.info(
            'Sending mail to {} (MailSenderClass : {})'.format(
                ', '.join(self.real_receivers_list),
                self.__class__.__name__
            )
        )
        msg.send()


class MessageHistorySender(MasterMailSender):
    """
    Log into message_history table
    """
    def send_mail(self):
        for receiver in self.receivers:
            message_history_mdl.MessageHistory.objects.create(
                reference=self.reference,
                subject=self.kwargs.get('subject'),
                content_txt=self.kwargs.get('message'),
                content_html=self.kwargs.get('html_message'),
                receiver_person_id=receiver.get('receiver_person_id'),
                receiver_email=receiver.get('receiver_email'),
                sent=timezone.now() if receiver.get('receiver_email') else None
            )


class GenericMailSender(MasterMailSender):
    """
    Add testing information to message
    Send email to a generic email address (settings.COMMON_EMAIL_RECEIVER)
    """
    def get_real_receivers_list(self):
        return [settings.COMMON_EMAIL_RECEIVER]

    def send_mail(self):
        add_testing_information_to_contents(self)
        super().send_mail()


class ConnectedUserMailSender(MasterMailSender):
    """
    Add testing information to message
    Send email to the email address of the connected user
    """
    def get_real_receivers_list(self):
        if self.connected_user and self.connected_user.person.email:
            return [self.connected_user.person.email]
        else:
            missing_field = 'connected_user' + (' email' if self.connected_user else '')
            logger.error('ConnectedUserMailSender class was used, but no ' + missing_field + ' was given. '
                         'Email will be sent to the COMMON_EMAIL_RECEIVER (from settings) instead.')
            return [settings.COMMON_EMAIL_RECEIVER]

    def send_mail(self):
        add_testing_information_to_contents(self)
        super().send_mail()


class RealReceiverMailSender(MasterMailSender):
    """
    DO NOT add testing information to message
    Send email to the email addresses of the real receivers
    """
    def get_real_receivers_list(self):
        return self.get_original_receivers_list()


def _get_attachments(attributes_message):
    attachment = attributes_message.get("attachment")
    if attachment:
        if isinstance(attachment, list):
            return attachment
        else:
            return [attachment]
    return None


def add_testing_information_to_contents(mail):
    testing_informations = _(
        "This is a test email sent from OSIS, only sent to {new_dest_address}. "
        "Planned receivers were : {receivers_addresses}."
    ).format(
        new_dest_address=', '.join(filter(None, mail.real_receivers_list)),
        receivers_addresses=', '.join(filter(None, mail.original_receivers_list))
    )

    mail.kwargs['message'] = "{testing_informations} \n {original_message}".format(
        testing_informations=testing_informations,
        original_message=mail.kwargs.get('message')
    )
    mail.kwargs['html_message'] = "<p>{testing_informations}</p> {original_message}".format(
        testing_informations=testing_informations,
        original_message=mail.kwargs.get('html_message')
    )
