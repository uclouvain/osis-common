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
    help = "Check the quality of code (pycodestyle, pylint, ...)"

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

        failed_checks = []

        if not self.check_pycodestyle(target_branch, target_app):
            failed_checks.append('pycodestyle')

        if not self.check_pylint(target_branch, target_app):
            failed_checks.append('pylint')

        if failed_checks:
            self.stdout.write(
                self.style.ERROR(
                    "QUALITY CHECKS FAILED : {}".format(', '.join(failed_checks))
                )
            )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS("QUALITY CHECKS PASSED")
        )

    def check_pycodestyle(self, target_branch: str, target_app: str) -> utils.SUCCESS_RESULT:
        return self.run_command(
            [
                "diff-quality",
                "--violations=pycodestyle",
                "--compare-branch={}".format(target_branch),
                "--fail-under=100"
            ],
            cwd=self.compute_app_path(target_app) if target_app != ALL_APPS else None
        )

    def check_pylint(self, target_branch: str, target_app: str) -> utils.SUCCESS_RESULT:
        return self.run_command(
            [
                "diff-quality",
                "--violations=pylint",
                "--compare-branch={}".format(target_branch),
                "--fail-under=90"
            ],
            cwd=self.compute_app_path(target_app) if target_app != ALL_APPS else None
        )
