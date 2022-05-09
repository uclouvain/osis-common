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
import logging
from enum import Enum, auto
from functools import wraps
from typing import Callable, Union, Dict

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.views import View

HIJACK_HISTORY_SESSION_KEY = "hijack_history"
REQUEST_REMOTE_ADDR = "REMOTE_ADDR"
UNDEFINED = "Undefined"
EVENT_LOGGER = getattr(settings, 'EVENT_LOGGER', 'event')

logger = logging.getLogger(EVENT_LOGGER)


class EventType(Enum):
    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()
    VIEW = auto()


def log_event_decorator(event_type: 'EventType', domain: str, msg: str, level=logging.INFO) -> Callable:
    def log_decorator(cls_or_fn: Union[View, Callable]):
        if not isinstance(cls_or_fn, type):
            view = cls_or_fn

            @wraps(view)
            def wrapped_view(request, *args, **kwargs):
                response = view(request, *args, **kwargs)
                log_event(request, event_type, domain, msg, level=level, kwargs=kwargs)
                return response
            return wrapped_view

        cls = cls_or_fn
        original_get = getattr(cls, 'get', None)
        original_post = getattr(cls, 'post', None)

        def logged_get_func(self, *args, **kwargs):
            response = original_get(self, *args, **kwargs)

            log_event(self.request, event_type, domain, msg, level=level, view=self)

            return response

        def logged_post_func(self, *args, **kwargs):
            response = original_post(self, *args, **kwargs)

            log_event(self.request, event_type, domain, msg, level=level, view=self)

            return response

        if original_get:
            cls.get = logged_get_func
        if original_post:
            cls.post = logged_post_func
        return cls
    return log_decorator


def log_event(
        request: 'HttpRequest',
        event_type: 'EventType',
        domain: str,
        description: str,
        level=logging.INFO,
        view: View = None,
        kwargs: Dict = None
) -> None:
    ip_addr = request.META.get(REQUEST_REMOTE_ADDR, UNDEFINED)
    formatted_description = description.format(self=view, **(kwargs or {}))

    user = request.user.username
    if _is_hijacked(request):
        user = _get_hijacked_user(request)

    msg = f"{ip_addr} | {request.method} | {request.path} | {user} | {event_type.name} | {domain} |" \
          f" {formatted_description}"
    logger.log(
        msg=msg,
        level=level
    )


def _is_hijacked(request: 'HttpRequest'):
    return bool(request.session.get(HIJACK_HISTORY_SESSION_KEY, []))


def _get_hijacked_user(request: 'HttpRequest') -> str:
    hijacker_pk = request.session[HIJACK_HISTORY_SESSION_KEY][-1]
    hijacker = User.objects.get(pk=hijacker_pk)
    return f"{request.user.username} (hijacked by {hijacker})"
