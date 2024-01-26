#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2020 Université catholique de Louvain (http://www.uclouvain.be)
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
from django.urls import path, include, re_path

from assessments.api.views.assessment_mail import AssessmentMailView
from assessments.api.views.assessments import CurrentSessionExamView, NextSessionExamView, PreviousSessionExamView
from assessments.api.views.attendance_mark.calendar import AttendanceMarkCalendarListView
from assessments.api.views.attendance_mark.request import RequestAttendanceMarkView
from assessments.api.views.progress_overview import ProgressOverviewTutorView
from assessments.api.views.score_responsibles import ScoreResponsibleList
from assessments.api.views.score_sheet_xls_export import ScoreSheetXLSExportAPIView
from osis_common.api.views.status_check import StatusCheckView

app_name = "osis_common_api_v1"
urlpatterns = [
    path('status_check/', StatusCheckView.as_view(), name=StatusCheckView.name),
]
