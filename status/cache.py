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

from osis_common.status.service_status import ServiceStatus, ServiceStatusError, ServiceStatusSuccess

SERVICE_NAME = "cache"
CACHE_KEY = "status"


def check_cache() -> 'ServiceStatus':
    """
        Check that the cache works.
        :return ServiceStatus
    """
    try:
        from django.core.cache import cache
        cache.set(CACHE_KEY, "check")
        cache.get(CACHE_KEY)
        cache.delete(CACHE_KEY)
    except Exception as e:
        return ServiceStatusError(service=SERVICE_NAME, original_error=e)
    return ServiceStatusSuccess(service=SERVICE_NAME)
