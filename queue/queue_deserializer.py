##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2016 Université catholique de Louvain (http://www.uclouvain.be)
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
##############################################################################
import datetime
from django.apps import apps
from django.db.models import DateTimeField, DateField

from osis_common.models.serializable_model import SerializableModel
from osis_common.models.exception import MigrationPersistanceError

def deserialize(serialized_data):
    if isinstance(serialized_data, dict):
        _deserialize(serialized_data)
    else:
        raise TypeError('Serialized data must be a dict')


def _deserialize(dict):
    body = dict.get('body')
    model_class = apps.get_model(body.get('model'))
    fields = body.get('fields')

    if dict.get('to_delete'):
        _delete_instance_by_uuid(model_class, fields.get('uuid'))
    else:
        _persist(model_class, fields, dict.get('last_sync'))


def _delete_instance_by_uuid(cls, uuid):
    cls.objects.filter(uuid=uuid).delete()


def _persist(cls, data_to_persist, last_sync=None):
    for field_name, value in data_to_persist.items():
        if isinstance(value, dict):
            data_to_persist[field_name] = _persist(value.get('model'), value)

    query_set = cls.objects.filter(uuid=data_to_persist.get('uuid'))
    if query_set.count() == 0:
        return _make_insert(cls, data_to_persist)
    else:
        instance = query_set.first()
        if _changed_since_last_synchronization(data_to_persist, {'last_sync': last_sync}):
            return _make_update(cls, data_to_persist, instance, query_set)
        return instance.id


def _make_update(model_class, fields, persisted_obj, query_set):
    kwargs = _build_kwargs(fields, model_class)
    kwargs['id'] = persisted_obj.id
    query_set.update(**kwargs)
    return persisted_obj.id


def _make_insert(model_class, fields):
    kwargs = _build_kwargs(fields, model_class)
    if 'id' in kwargs:
        del kwargs['id']
    obj = model_class(**kwargs)
    super(SerializableModel, obj).save(force_insert=True)
    if obj.id:
        return obj.id
    else:
        raise MigrationPersistanceError


def _build_kwargs(fields, model_class):
    return {_get_field_name(f): _get_value(fields, f) for f in model_class._meta.fields if f.name in fields.keys()}


def _changed_since_last_synchronization(fields, structure):
    last_sync = _convert_long_to_datetime(structure.get('last_sync'))
    changed = _convert_long_to_datetime(fields.get('changed'))
    return not last_sync or not changed or changed > last_sync


def _get_field_name(field):
    if field.is_relation:
        return '{}_id'.format(field.name)
    return field.name


def _get_value(fields, field):
    attribute = fields.get(field.name)
    if isinstance(field, DateTimeField) or isinstance(field, DateField):
        return _convert_long_to_datetime(attribute)
    return attribute


def _convert_long_to_datetime(date_as_long):
    return datetime.datetime.fromtimestamp(date_as_long) if date_as_long else None