##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2017 Université catholique de Louvain (http://www.uclouvain.be)
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
import functools

from osis_common.models.exception import OverrideMethodError


def override(SuperClass):
    """This decorator can be use to ensure that an override method really exists in the superClass"""
    def method(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not _check_super_class_method(args[0].__class__.__bases__, func.__name__):
                raise OverrideMethodError(func.__name__,
                                          ' - '.join([superclass.__name__
                                                      for superclass in args[0].__class__.__bases__]),
                                          args[0].__class__.__name__)
            return func(*args, **kwargs)
        return wrapper
    return method


def _check_super_class_method(base_classes, function_name):
    return [True for superclass in base_classes if hasattr(superclass, function_name)]
