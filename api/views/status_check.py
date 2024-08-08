# ##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2024 Université catholique de Louvain (http://www.uclouvain.be)
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
# ##############################################################################

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views import View

from osis_common.status import db, cache, queue


class StatusCheckView(View):
    name = "status_check"

    def get(self, request, *args, **kwargs):
        try:
            self.authenticate(request)
        except PermissionDenied:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        list_status = [
            db.check_db(),
            cache.check_cache(),
            queue.check_queue()
        ]
        data = []
        for status in list_status:
            data.append({
                'service': status.service,
                'error': status.is_in_error(),
                'message': str(status)
            })
        has_error = any(service_status.is_in_error() for service_status in list_status)
        return JsonResponse(data, status=self.get_status_code(has_error), safe=False)

    @staticmethod
    def get_status_code(has_error: bool) -> int:
        return 200 if not has_error else 503

    @staticmethod
    def authenticate(request):
        authorization = request.headers.get('Authorization')
        if authorization:
            token = authorization.split(" ")[1]
            if token == settings.OSIS_HEALTH_SECRET_KEY:
                return
        raise PermissionDenied
