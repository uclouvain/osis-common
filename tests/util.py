##############################################################################
#
# OSIS stands for Open Student Information System. It's an application
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
import os
from datetime import datetime
from itertools import chain

from django.apps import apps
from django.core.serializers import serialize
from backoffice.settings import BASE_DIR

dump_exlcude_models = []


def dump_data_after_tests(apps_name_list, fixture_name):
    """
    Save the data after the tests as a fixture
    :param apps_name_list: List of apps of which we want to save the data
    :param fixture_name: The name of the produced fixture
    """
    query_sets = [list(model.objects.all()) for app_name in apps_name_list
                  for model in apps.get_app_config(app_name).get_models()
                  if model._meta.label_lower not in dump_exlcude_models]
    query_sets_jsonable = chain.from_iterable(query_sets)
    fixture = serialize('json', query_sets_jsonable)
    file_path = os.path.join(BASE_DIR,
                             "osis_common/tests/data_after_tests/{}_{}.json"
                             .format(fixture_name, datetime.now()
                                     .strftime("%d_%m_%H_%M")))
    with open(file_path, 'w') as file:
        file.write(fixture)
