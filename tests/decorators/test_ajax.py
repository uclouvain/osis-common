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
from django.test import TestCase, RequestFactory

from osis_common.decorators.ajax import ajax_required


@ajax_required
def test_view(request):
    return True


class TestAjaxRequiredDecorator(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def test_request_is_not_ajax(self):
        a_request = self.request_factory.get('/')
        self.assertRaises(PermissionDenied, test_view, a_request)

    def test_request_is_ajax(self):
        a_request = self.request_factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(test_view(a_request))
