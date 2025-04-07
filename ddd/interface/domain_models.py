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
import datetime
import json
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Callable, Any

import attr


__all__ = [
    "CommandRequest",
    "Event",
    "ValueObject",
    "EntityIdentity",
    "Entity",
    "RootEntity",
    "DomainService",
    "AbstractRepository",
]

import cattr
from django.conf import settings


@attr.s(frozen=True, slots=True)
class CommandRequest(abc.ABC):
    transaction_id = attr.ib(init=False, type=uuid.UUID, default=attr.Factory(uuid.uuid4), eq=False)


@attr.dataclass
class ValueSerializer:
    value: Any

    def serialize(self):
        if isinstance(self.value, (Decimal, uuid.UUID)):
            return str(self.value)
        elif isinstance(self.value, datetime.datetime):
            return self.value.strftime(settings.EVENT_DATETIME_FORMAT)
        elif isinstance(self.value, datetime.date):
            return self.value.strftime(settings.EVENT_DATE_FORMAT)
        elif isinstance(self.value, EntityIdentity):
            return self.value.serialize()
        return self.value


@attr.dataclass(frozen=True, slots=True)
class Event(abc.ABC):
    entity_id: 'EntityIdentity'
    transaction_id: uuid.UUID = attr.Factory(uuid.uuid4)

    def serialize(self) -> Dict:
        return attr.asdict(
            self,
            value_serializer=lambda inst, field, value: ValueSerializer(value).serialize(),
            recurse=True,
        )

    @classmethod
    def deserialize(cls, payload: Dict) -> 'Event':
        return cattr.structure({
            **payload,
        }, cls)


class ValueObject(abc.ABC):
    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError


class EntityIdentity(ValueObject, abc.ABC):

    def serialize(self) -> Dict:
        return attr.asdict(
            self,
            value_serializer=lambda inst, field, value: ValueSerializer(value).serialize(),
            recurse=True,
        )

    @classmethod
    def deserialize(cls, payload: Dict) -> Optional['EntityIdentity']:
        if not payload:
            return
        return cls(**payload)


class Entity(abc.ABC):
    def __init__(self, *args, entity_id: EntityIdentity = None, **kwargs):
        self.entity_id = entity_id
        super().__init__(*args, **kwargs)

    def __eq__(self, other):
        if type(other) == self.__class__:
            return self.entity_id == other.entity_id
        return False

    def __hash__(self):
        return hash(self.entity_id)


@attr.s(eq=False, hash=False)
class RootEntity(Entity):
    version_id = attr.ib(type=int, default=0, eq=False, repr=False, kw_only=True)


class DomainService(abc.ABC):
    """
    A service used by the domain to return informations from database.
    These informations can not be Domain object.
    Exemples of DomainServices :
    - CheckIfSomethingExist()
    - EntityIdentityGenerator()
    """
    pass


class AbstractRepository(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get(cls, entity_id: EntityIdentity) -> RootEntity:
        """
        Function used to get root entity by entity identity.
        :return: The root entity
        """
        pass

    @classmethod
    @abc.abstractmethod
    def search(cls, entity_ids: Optional[List[EntityIdentity]] = None, **kwargs) -> List[RootEntity]:
        """
        Function used to search multiple root entity (by entity identity for ex).
        :return: The list of root entities found
        """
        pass

    @classmethod
    @abc.abstractmethod
    def delete(cls, entity_id: EntityIdentity, **kwargs) -> None:
        """
        Function used to delete a root entity via it's entity identity.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def save(cls, entity: RootEntity) -> None:
        """
        Function used to persist existing domain RootEntity (aggregate) into the database.
        :param entity: Any domain root entity.
        """
        pass


EventHandlers = Dict[Event, List[Callable]]
