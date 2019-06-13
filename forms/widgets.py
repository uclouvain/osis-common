from django.forms.widgets import Input

from osis_common.utils.numbers import normalize_fraction


class FloatFormatInput(Input):
    input_type = 'text'
    template_name = 'django/forms/widgets/number.html'

    def __init__(self, attrs=None, render_value=False):
        super(FloatFormatInput, self).__init__(attrs)
        self.render_value = render_value

    def get_context(self, name, value, attrs):
        if value and self.render_value:
            value = normalize_fraction(value)
        return super(FloatFormatInput, self).get_context(name, value, attrs)
