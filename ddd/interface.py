import abc
from typing import List, Optional


class CommandRequest(abc.ABC):
    pass


class BusinessException(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(**kwargs)


class ValueObject(abc.ABC):
    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError


class EntityIdentity(ValueObject):
    pass


class Entity(abc.ABC):
    def __init__(self, *args, entity_id: EntityIdentity = None, **kwargs):
        self.entity_id = entity_id
        super().__init__(*args, **kwargs)

    def __eq__(self, other):
        return self.entity_id == other.entity_id

    def __hash__(self):
        return hash(self.entity_id)


class RootEntity(Entity):
    pass


class AbstractRepository(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, entity: Entity) -> EntityIdentity:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def update(cls, entity: Entity) -> EntityIdentity:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get(cls, entity_id: EntityIdentity) -> Entity:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def search(cls, entity_ids: Optional[List[EntityIdentity]] = None, **kwargs) -> Entity:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def delete(cls, entity_id: EntityIdentity) -> None:
        raise NotImplementedError
