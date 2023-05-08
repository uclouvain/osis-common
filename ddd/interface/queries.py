##############################################################################
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
import abc
import uuid
from typing import Optional

import attr
from .domain_models import Event


__all__ = [
    "QueryRequest",
    "PaginatedQueryRequest",
    "DTO",
    "ReadModel",
    "ReadModelRepository",
]


@attr.s(frozen=True, slots=True)
class QueryRequest(abc.ABC):
    transaction_id = attr.ib(init=False, type=uuid.UUID, default=attr.Factory(uuid.uuid4), eq=False)


@attr.dataclass(frozen=True, slots=True)
class PaginatedQueryRequest(QueryRequest):
    ordre_tri: Optional[str] = None
    nombre_elements_par_page: int = 25
    page: int = 0


class DTO:
    """
    Data Transfer Object : only contains declaration of primitive fields.
    """
    pass


class ReadModel(abc.ABC):
    @classmethod
    def initialize(cls, *args, **kwargs) -> None:
        """
        Function used to build read model from scratch (ORM / SQL / Python processing)
        """
        pass

    @classmethod
    def handle(cls, event: 'Event') -> None:
        """
        Function used to hydrate ReadModel via events subscribed
        """
        pass


class ReadModelRepository(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get(cls, *args, **kwargs) -> 'DTO':
        pass
