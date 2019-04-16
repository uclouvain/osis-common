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
from django.contrib import admin

NON_UPDATABLE_FIELDS = ["id", "uuid", "external_id", "changed", "deleted"]


class OsisModelAdmin(admin.ModelAdmin):

    def __init__(self, model, admin_site):
        self.readonly_fields = self.readonly_fields or []
        self.readonly_fields += tuple([field.name for field in model._meta.fields if field.name in NON_UPDATABLE_FIELDS])
        self.raw_id_fields = [field.name for field in model._meta.fields if field.is_relation]
        super(OsisModelAdmin, self).__init__(model, admin_site)
