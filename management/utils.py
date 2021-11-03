#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2021 Université catholique de Louvain (http://www.uclouvain.be)
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
import subprocess
import sys
from typing import List

from django.core.management.base import OutputWrapper

SUCCESS_RESULT = bool


class RunCommandMixin:
    """
        Mixin for running shell commands for django manage.py commands.
    """

    stdout = None  # type: OutputWrapper

    def run_command(
            self,
            cmd_args: List[str],
            stdout=sys.stdout,
            stderr=sys.stdout,
            **kwargs
            ) -> SUCCESS_RESULT:
        """
            Run a command via subprocess.run().
            Remove empty string and non value from cmd_args before executing command.

        :param cmd_args: subprocess.run args value
        :param stdout: standard output
        :param stderr: standard error
        :param kwargs: subprocess.run parameters
        :return: a success result that is true if the command was successful
        """
        success = True
        cleaned_cmd_args = [argument for argument in cmd_args if argument]

        self.stdout.write(
            self.style.MIGRATE_HEADING(" ".join(cleaned_cmd_args))
        )

        try:
            completed_process = subprocess.run(
                cleaned_cmd_args,
                stdout=stdout,
                stderr=stderr,
                **kwargs
            )
            completed_process.check_returncode()
        except subprocess.CalledProcessError:
            success = False

        self.stdout.write("\n\n")
        return success

    def compute_app_path(self, app_name: str) -> str:
        return "./{}".format(app_name)
