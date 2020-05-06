import abc


class CommandRequest(abc.ABC):
    pass


class ValueObject(abc.ABC):
    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError


class EntityIdentity(ValueObject):
    pass


class Entity(abc.ABC):
    def __init__(self, *args, entity_id: EntityIdentity = None, **kwargs):
        if entity_id is not None:
            self.entity_id = entity_id
        super().__init__(*args, **kwargs)

    def __eq__(self, other):
        return self.entity_id == other.entity_id

    def __hash__(self):
        raise hash(self.entity_id)


class RootEntity(Entity):
    pass


class AbstractRepository(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def add(self, entity: Entity):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get(self, entity_id: EntityIdentity) -> Entity:
        raise NotImplementedError

    #  TODO Add method which are common accros repository
