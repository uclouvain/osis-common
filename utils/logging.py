#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2022 Université catholique de Louvain (http://www.uclouvain.be)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
import functools
from enum import Enum, auto
import logging
from typing import Union, Callable

from django.conf import settings
from django.http import HttpRequest
from django.views import View

logger = logging.getLogger(settings.EVENT_LOGGER)


REQUEST_REMOTE_ADDR = "REMOTE_ADDR"
UNDEFINED = "Undefined"


class EventType(Enum):
    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()
    VIEW = auto()


def log_event_dec(event_type: 'EventType', domain: str, msg: str, level=logging.INFO) -> Callable:
    def log_decorator(view_function: Callable) -> Callable:
        """
        :param view_function: can either be a django function view or a method from class based view
        """
        @functools.wraps(view_function)
        def decorated_view_function(self_or_request: Union['View', 'HttpRequest'], *args, **kwargs) -> Callable:
            response = view_function(self_or_request, *args, **kwargs)

            if isinstance(self_or_request, HttpRequest):
                log_event(self_or_request, event_type, domain, msg, level=level)
            else:
                log_event(self_or_request.request, event_type, domain, msg, level=level, view=self_or_request)

            return response
        return decorated_view_function
    return log_decorator


def log_event(
        request: 'HttpRequest',
        event_type: 'EventType',
        domain: str,
        msg: str,
        level=logging.INFO,
        view: View = None
) -> None:
    ip_addr = request.META.get(REQUEST_REMOTE_ADDR, UNDEFINED)
    formatted_msg = msg.format(self=view)
    logger.log(msg=f"{ip_addr} - {request.user.username} - {event_type.name} - {domain} - {formatted_msg}", level=level)
