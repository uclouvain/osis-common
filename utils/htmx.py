# ##############################################################################
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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
# ##############################################################################
import json
from http import HTTPStatus
from typing import List

SUCCESS_HTTP_STATUS_CODES = {
    HTTPStatus.OK,
    HTTPStatus.CREATED,
    HTTPStatus.ACCEPTED,
    HTTPStatus.NO_CONTENT,
    HTTPStatus.FOUND,
}


class HtmxMixin:
    htmx_template_name: str = None
    htmx_push_url: bool = False

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            'cleaned_urlencode': self.get_cleaned_urlencode()
        }

    def get_htmx_custom_triggers(self) -> List[str]:
        return []

    @classmethod
    def get_default_triggered_event_name(cls) -> str:
        view_name = getattr(cls, 'name', None)
        if view_name:
            return f'{view_name}-event'

    def get_template_names(self):
        if self.request.htmx:
            return [self.htmx_template_name]
        return super().get_template_names()

    def dispatch(self, *args, **kwargs):
        response = super().dispatch(*args, **kwargs)
        default_event_name = self.get_default_triggered_event_name()
        if default_event_name and response.status_code in SUCCESS_HTTP_STATUS_CODES:
            # Suffix with request.method (POST or GET) to avoid refreshing on GET
            response['HX-Trigger'] = json.dumps(
                {
                    f"{default_event_name}-{self.request.method}": "",
                    **{f"{custom_event}-{self.request.method}": "" for custom_event in self.get_htmx_custom_triggers()},
                }
            )
            if self.htmx_push_url:
                response['HX-Push'] = self.get_cleaned_query_string_path()
        return response


    def get_cleaned_urlencode(self):
        query_params = [f"{key}={value}" for key, value in self.request.GET.items()]
        return f"{'&'.join([*set(query_params)])}"

    def get_cleaned_query_string_path(self):
        query_string = self.get_cleaned_urlencode()
        return f"{self.request.path}?{query_string}" if query_string else self.request.path
