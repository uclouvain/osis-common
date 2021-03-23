import abc
from typing import List, Optional, Callable, Union


class CommandRequest(abc.ABC):
    pass


class BusinessException(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(**kwargs)


class BusinessExceptions(BusinessException):
    def __init__(self, messages: List[str]):
        self.messages = messages


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
        if type(other) == self.__class__:
            return self.entity_id == other.entity_id
        return False

    def __hash__(self):
        return hash(self.entity_id)


class RootEntity(Entity):
    pass


ApplicationService = Callable[[CommandRequest], Union[EntityIdentity, List[EntityIdentity]]]


class AbstractRepository(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, entity: Entity, **kwargs: ApplicationService) -> EntityIdentity:
        """
        Function used to persist (create) new domain Entity into the database.
        :param entity: Any domain Entity.
        :param services: List of application services used to persist data into another domain.
        :return: The identity of the created entity.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def update(cls, entity: Entity, **kwargs: ApplicationService) -> EntityIdentity:
        """
        Function used to persist (update) existing domain Entity into the database.
        :param entity: Any domain Entity.
        :param services: List of application services used to persist data into another domain.
        :return: The identity of the updated entity.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get(cls, entity_id: EntityIdentity) -> Entity:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def search(cls, entity_ids: Optional[List[EntityIdentity]] = None, **kwargs) -> List[Entity]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def delete(cls, entity_id: EntityIdentity, **kwargs: ApplicationService) -> None:
        raise NotImplementedError


class DomainService(abc.ABC):
    """
    A service used by the domain to return informations from database.
    These informations can not be Domain object.
    Exemples of DomainServices :
    - CheckIfSomethingExist()
    - EntityIdentityGenerator()
    """
    pass


class DTO:
    """
    Data Transfer Object : only contains declaration of primitive fields.
    Used as 'contract" between 2 layers in the code (example : repository <-> factory)
    """
    pass


class RootEntityBuilder(abc.ABC):

    @classmethod
    def build_from_command(cls, cmd: 'CommandRequest') -> 'RootEntity':
        raise NotImplementedError()

    @classmethod
    def build_from_repository_dto(cls, dto_object: 'DTO') -> 'RootEntity':
        raise NotImplementedError()


class EntityIdentityBuilder(abc.ABC):

    @classmethod
    def build_from_command(cls, cmd: 'CommandRequest') -> 'EntityIdentity':
        raise NotImplementedError()

    @classmethod
    def build_from_repository_dto(cls, dto_object: 'DTO') -> 'EntityIdentity':
        raise NotImplementedError()
