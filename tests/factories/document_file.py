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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
import factory.fuzzy

from osis_common.models.document_file import CONTENT_TYPE_CHOICES
from osis_common.models.enum import storage_duration

CONTENT_TYPE_LIST = [x for (x, y) in CONTENT_TYPE_CHOICES]


class DocumentFileFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'osis_common.DocumentFile'

    file_name = factory.fuzzy.FuzzyText(prefix='file_')
    content_type = factory.fuzzy.FuzzyChoice(CONTENT_TYPE_LIST)
    creation_date = factory.Faker('date_time_this_year', before_now=True, after_now=False)
    storage_duration = storage_duration.FIVE_YEARS
    file = factory.django.FileField(filename='document_file')
    description = factory.fuzzy.FuzzyText(prefix='File description ')
    update_by = 'system'
    application_name = factory.Faker('text', max_nb_chars=100)
    size = factory.fuzzy.FuzzyInteger(45, 200)
