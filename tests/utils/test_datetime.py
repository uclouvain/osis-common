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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    A copy of this license - GNU General Public License - is available
#    at the root of the source code of this program.  If not,
#    see http://www.gnu.org/licenses/.
#
##############################################################################
import datetime
import factory
import factory.fuzzy

from django.test import TestCase

from utils.datetime import get_tzinfo, strictly_ordered_dates


class DateTimeUtils(TestCase):
    def setUp(self):
        now = datetime.datetime.now()
        datetimes = [now + datetime.timedelta(days=x*365) for x in range(4)]

        self.datetime_low = factory.fuzzy.FuzzyDateTime(datetime.datetime(datetimes[0].year,
                                                                          datetimes[0].month,
                                                                          datetimes[0].day,
                                                                          tzinfo=get_tzinfo()),
                                                        datetime.datetime(datetimes[1].year,
                                                                          datetimes[1].month,
                                                                          datetimes[1].day,
                                                                          tzinfo=get_tzinfo())
                                                        ).fuzz()

        self.datetime_high = factory.fuzzy.FuzzyDateTime(datetime.datetime(datetimes[2].year,
                                                                           datetimes[2].month,
                                                                           datetimes[2].day,
                                                                           tzinfo=get_tzinfo()),
                                                         datetime.datetime(datetimes[3].year,
                                                                           datetimes[3].month,
                                                                           datetimes[3].day,
                                                                           tzinfo=get_tzinfo())
                                                        ).fuzz()

    def test_strictly_ordered_dates_2_datetimes(self):
        self.assertTrue(strictly_ordered_dates(self.datetime_low, self.datetime_high))
        self.assertFalse(strictly_ordered_dates(self.datetime_high, self.datetime_low))

    def test_strictly_ordered_dates_2_dates(self):
        self.assertTrue(strictly_ordered_dates(self.datetime_low.date(), self.datetime_high.date()))
        self.assertFalse(strictly_ordered_dates(self.datetime_high.date(), self.datetime_low.date()))

    def test_strictly_ordered_dates_1_date_1_datetime(self):
        self.assertTrue(strictly_ordered_dates(self.datetime_low.date(), self.datetime_high))
        self.assertTrue(strictly_ordered_dates(self.datetime_low, self.datetime_high.date()))

    def test_strictly_ordered_dates_bad_arguments_type(self):
        text = factory.fuzzy.FuzzyText(length=12).fuzz()
        integer = factory.fuzzy.FuzzyInteger(0).fuzz()
        with self.assertRaises(TypeError):
            strictly_ordered_dates(text, integer)
        with self.assertRaises(TypeError):
            strictly_ordered_dates(integer, integer)
        with self.assertRaises(TypeError):
            strictly_ordered_dates(text, text)
