from .domain_models import *
from .queries import *
from .builders import *
from .exceptions import *
from .events import *

from decimal import Decimal
from typing import Union, List, Callable

ApplicationServiceResult = Union[EntityIdentity, List[EntityIdentity], DTO, List[DTO]]
ApplicationService = Callable[[CommandRequest], ApplicationServiceResult]
PrimitiveType = Union[int, str, float, Decimal]
