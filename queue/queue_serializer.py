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
import json
import time
from django.utils.encoding import force_text
from django.db.models import DateTimeField, DateField

def serialize(obj, last_syncs=None):
    if obj:
        dict = {}
        for f in obj.__class__._meta.fields:
            attribute = getattr(obj, f.name)
            if f.is_relation:
                try:
                    if attribute and getattr(attribute, 'uuid'):
                        dict[f.name] = serialize(attribute, last_syncs=last_syncs)
                except AttributeError:
                    pass
            else:
                try:
                    json.dumps(attribute)
                    dict[f.name] = attribute
                except TypeError:
                    if isinstance(f, DateTimeField) or isinstance(f, DateField):
                        dt = attribute
                        dict[f.name] = _convert_datetime_to_long(dt)
                    else:
                        dict[f.name] = force_text(attribute)
        class_label = obj.__class__._meta.label
        last_sync = None
        if last_syncs:
            last_sync = _convert_datetime_to_long(last_syncs.get(class_label))
        return {"model": class_label, "fields": dict, 'last_sync': last_sync}
    else:
        return None


def _convert_datetime_to_long(dtime):
    return time.mktime(dtime.timetuple()) if dtime else None