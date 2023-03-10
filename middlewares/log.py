#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2023 Université catholique de Louvain (http://www.uclouvain.be)
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
from typing import Union

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.http import StreamingHttpResponse

UNDEFINED = "Undefined"
NO_GET_PARAMETERS = 'No GET parameters'
REQUEST_REMOTE_ADDR = "REMOTE_ADDR"
HIJACK_HISTORY_SESSION_KEY = "hijack_history"

class LogUserNavigationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        logger_name = getattr(settings, 'EVENT_LOGGER', 'event')
        self.logger = logging.getLogger(logger_name)
        self.level = logging.INFO

        self.env = settings.ENVIRONMENT

    def __call__(self, request: 'HttpRequest'):
        response =  self.get_response(request)  # type: Union[HttpResponse, StreamingHttpResponse]

        self.log(request, response)

        return response

    def log(
            self,
            request: 'HttpRequest',
            response: Union['HttpResponse', 'StreamingHttpResponse'],
    ) -> None:
        try:
            msg = generate_log_message(request, response, self.env)
            self.logger.log(self.level, msg)
        except Exception:
            self.logger.exception("Error logging request")


def generate_log_message(
        request: 'HttpRequest',
        response: Union['HttpResponse', 'StreamingHttpResponse'],
        env: str
) -> str:
    ip_addr = request.META.get(REQUEST_REMOTE_ADDR, UNDEFINED)

    view_func = UNDEFINED
    if request.resolver_match:
        view_func = request.resolver_match.func.__name__

    app = UNDEFINED
    if request.resolver_match:
        app = str(request.resolver_match.func.__module__).split(".")[0]

    user = request.user.username
    if _is_hijacked(request):
        user = _get_hijacked_user(request)

    get_parameters = request.GET.urlencode() or NO_GET_PARAMETERS
    msg = f"[{env}] " \
          f"{ip_addr} | " \
          f"{request.method} | " \
          f"{response.status_code} | " \
          f"{request.path} | " \
          f"{get_parameters} | " \
          f"{view_func} | " \
          f"{app} | " \
          f"{user}"

    return msg


def _is_hijacked(request: 'HttpRequest') -> bool:
    return hasattr(request.user, 'is_hijacked') and request.user.is_hijacked

def _get_hijacked_user(request: 'HttpRequest') -> str:
    hijacker_pk = request.session[HIJACK_HISTORY_SESSION_KEY][-1]
    hijacker = User.objects.get(pk=hijacker_pk)
    return f"{request.user.username} (hijacked by {hijacker})"
