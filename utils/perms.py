##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2019 Université catholique de Louvain (http://www.uclouvain.be)
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
from django.core.exceptions import PermissionDenied
from django.utils.functional import cached_property


class BasePerm:
    predicates = None

    def __init__(self, **kwargs):
        self.predicates_arguments = kwargs

    @cached_property
    def errors(self):
        predicates_errors = (self._call_predicate(p) for p in self.predicates)
        return [e for e in predicates_errors if e]

    @property
    def as_ul(self):
        html = "<ul><li>{}</li></ul>".format("</li><li>".join(self.errors))
        return html if self.errors else ""

    def _call_predicate(self, predicate):
        try:
            predicate(**self.predicates_arguments)
        except PermissionDenied as e:
            return str(e)
        return ""

    def is_valid(self):
        return not self.errors


def conjunction(*predicates):

    def conjunction_method(*args, **kwargs):
        return all(
            p(*args, **kwargs) for p in predicates
        )

    return conjunction_method


def disjunction(*predicates):

    def disjunction_method(*args, **kwargs):
        return any(
            p(*args, **kwargs) for p in predicates
        )

    return disjunction_method


def negation(predicate):

    def negation_method(*args, **kwargs):
        return not predicate(*args, **kwargs)

    return negation_method
