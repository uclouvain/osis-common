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
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from osis_common.models import message_history as message_history_mdl


class MailSenderInterface(abc.ABC):
    def __init__(self, receivers, reference, **kwargs):
        self.receivers = receivers
        self.reference = reference
        self.kwargs = kwargs

    @abc.abstractmethod
    def send_mail(self):
        pass


class FallbackMailSender(MailSenderInterface):
    """
    Do not send actual email
    Log into message_history table
    """

    def send_mail(self):
        for receiver in self.receivers:
            message_history_mdl.MessageHistory.objects.create(
                reference=self.reference,
                subject=self.kwargs.get('subject'),
                content_txt=self.kwargs.get('message'),
                content_html=self.kwargs.get('html_message'),
                receiver_id=receiver.get('receiver_id'),
                sent=timezone.now() if receiver.get('receiver_email') else None
            )


class GenericMailSender(FallbackMailSender):
    """
    Send email to a generic email address (settings.COMMON_EMAIL_RECEIVER)
    Log into message_history table
    """

    def send_mail(self):
        receivers_addresses = [
            receiver.get('receiver_email') for receiver in self.receivers if receiver.get('receiver_email')
        ]
        self.add_testing_informations_to_contents(receivers_addresses)
        super().send_mail()

    def add_testing_informations_to_contents(self, receivers_addresses):
        testing_informations = _(
            "This is a test email sent from OSIS, only sent to {generic_address}. "
            "Original recipients were : {receivers_addresses}."
        ).format(
            generic_address=settings.COMMON_EMAIL_RECEIVER,
            receivers_addresses=', '.join(receivers_addresses)
        )

        self.kwargs['message'] = "{testing_informations} \n {original_message}".format(
            testing_informations=testing_informations,
            original_message=self.kwargs.get('message')
        )
        self.kwargs['html_message'] = "<p>{testing_informations}</p> {original_message}".format(
            testing_informations=testing_informations,
            original_message=self.kwargs.get('html_message')
        )


class ConnectedUserMailSender(FallbackMailSender):
    """
    Send email to the email address of the connected user
    Log into message_history table
    """

    def send_mail(self):
        self.kwargs['subject'] = "TESTTESTTESTTEST"
        super().send_mail()


class MailSender(FallbackMailSender):
    """
   Send email to the email address of the real recipient
    Log into message_history table
   """

    def send_mail(self):
        super().send_mail()
