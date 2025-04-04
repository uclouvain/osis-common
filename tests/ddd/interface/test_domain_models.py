import datetime
from decimal import Decimal
import uuid

import attr
from django.test import SimpleTestCase

from osis_common.ddd import interface


@attr.dataclass(frozen=True, slots=True)
class EntityIdToTest(interface.EntityIdentity):
    a: int
    b: str


@attr.dataclass(frozen=True, slots=True, kw_only=True)
class EventToTest(interface.Event):
    entity_id: 'EntityIdToTest'
    int_field: int
    str_field: str
    float_field: float
    date_field: datetime.date
    datetime_field: datetime.datetime
    decimal_field: Decimal
    uuid_field: uuid.UUID


class TestSerializeDeserializeEvent(SimpleTestCase):

    def test_should_serialize_and_deserialize_event(self):
        event = EventToTest(
            entity_id=EntityIdToTest(a=1, b='test'),
            int_field=35,
            str_field='Coucou',
            float_field=float(13.5),
            date_field=datetime.date.today(),
            datetime_field=datetime.datetime.now(),
            decimal_field=Decimal(17.66),
            uuid_field=uuid.uuid4(),
        )
        payload = event.serialize()
        new_event = EventToTest.deserialize(payload)
        self.assertEqual(event, new_event)
        event = attr.evolve(event, entity_id=None)
        payload = event.serialize()
        new_event = EventToTest.deserialize(payload)
        self.assertEqual(event, new_event)
