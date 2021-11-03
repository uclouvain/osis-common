# ############################################################################
#  OSIS stands for Open Student Information System. It's an application
#  designed to manage the core business of higher education institutions,
#  such as universities, faculties, institutes and professional schools.
#  The core business involves the administration of students, teachers,
#  courses, programs and so on.
#
#  Copyright (C) 2015-2020 Université catholique de Louvain (http://www.uclouvain.be)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  A copy of this license - GNU General Public License - is available
#  at the root of the source code of this program.  If not,
#  see http://www.gnu.org/licenses/.
# ############################################################################

from django.core.management import BaseCommand

from osis_common.management import utils
from osis_common.management.utils import RunCommandMixin


ALL_APPS = 'ALL'
DEFAULT_TARGET_BRANCH = "origin/dev"


class Command(BaseCommand, RunCommandMixin):
    help = "Launch tests and show diff coverage."

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "-t",
            "--target_branch",
            help="target branch to compare with",
            default=DEFAULT_TARGET_BRANCH,
            type=str,
            metavar="BRANCH"
        )

        parser.add_argument(
            "-a",
            "--app",
            help="limit to app",
            default=ALL_APPS,
            type=str,
            metavar="APP"
        )

    def handle(self, *args, **options):
        target_branch = options['target_branch']
        target_app = options['app']

        success = self.run_tests(target_app)
        self.show_diff_coverage(target_branch, target_app)

        if not success:
            self.stdout.write(
                self.style.ERROR("TESTS FAILED")
            )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS("TESTS PASSED")
        )

    def run_tests(self, target_app: str) -> utils.SUCCESS_RESULT:
        return self.run_command(
            [
                "coverage",
                "run",
                "--rcfile=osis_common/.coveragerc",
                "--source={}/".format(target_app) if target_app != ALL_APPS else "",
                "manage.py",
                "test",
                target_app if target_app != ALL_APPS else "",
                "--parallel",
                "--no-logs",
                "--noinput"
            ]
        )

    def show_diff_coverage(self, target_branch: str, target_app):
        self.run_command(
            ["coverage", "combine"],
        )

        self.run_command(
            ["coverage", "xml"],
        )

        self.run_command(
            [
                "diff-cover",
                "../coverage.xml" if target_app != ALL_APPS else "coverage.xml",
                "--compare-branch={}".format(target_branch)
            ],
            cwd=self.compute_app_path(target_app) if target_app != ALL_APPS else None
        )
