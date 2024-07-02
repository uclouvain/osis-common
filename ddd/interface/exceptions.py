##############################################################################
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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
from typing import List
from django.utils.translation import gettext_lazy as _


__all__ = [
    "BusinessException",
    "BusinessExceptions",
    "InfrastructureException",
    "EntityConcurrencyViolationException",
]


class BusinessException(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(**kwargs)

    def __reduce__(self):
        """
        Subclasses of Exception with different parameters MUST implement the __reduce__ method in order to be pickable.
        Here we force the unpickled instance to be a BusinessException, so that it can be pickled first.
        This is only used in Django tests ran with --parallel. The original exception can still be seen with tests
        ran without it, but this is not possible to do on the CI for example.

        https://github.com/python/cpython/issues/76877
        """
        return BusinessException, (self.message,)


class BusinessExceptions(BusinessException):
    def __init__(self, messages: List[str]):
        self.messages = messages

    def __reduce__(self):
        return BusinessExceptions, (self.messages,)


class InfrastructureException(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(**kwargs)


class EntityConcurrencyViolationException(InfrastructureException):
    def __init__(self, **kwargs):
        message = _('Concurrency Violation: Stale data detected. Entity was already modified.')
        super().__init__(message, **kwargs)
