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
from decimal import Decimal

from django.forms.widgets import Input

from osis_common.utils.numbers import normalize_fraction


class DecimalFormatInput(Input):
    input_type = 'text'
    template_name = 'django/forms/widgets/number.html'

    def __init__(self, attrs=None, render_value=False):
        super(DecimalFormatInput, self).__init__(attrs)
        self.render_value = render_value

    def get_context(self, name, value, attrs):
        if isinstance(value, float):
            value = Decimal(value)
        if isinstance(value, Decimal) and self.render_value:
            value = normalize_fraction(value)
        return super(DecimalFormatInput, self).get_context(name, value, attrs)


class FloatFormatInput(Input):
    input_type = 'text'
    template_name = 'django/forms/widgets/number.html'

    def __init__(self, attrs=None, render_value=False):
        super(FloatFormatInput, self).__init__(attrs)
        self.render_value = render_value

    def get_context(self, name, value, attrs):
        if isinstance(value, float):
            value = Decimal(value)
        if isinstance(value, Decimal) and self.render_value:
            value = normalize_fraction(value)
        return super(FloatFormatInput, self).get_context(name, value, attrs)
