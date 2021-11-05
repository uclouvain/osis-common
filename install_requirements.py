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
import glob
import subprocess
import sys
from typing import List
import argparse


DEFAULT_CORE_REQUIREMENTS_FILE = './dev-requirements.txt'

parser = argparse.ArgumentParser(description="A utility to install OSIS project requirements.")
parser.add_argument(
    "-c",
    "--core",
    help="core requirements file (default: dev-requirements.txt)",
    default=DEFAULT_CORE_REQUIREMENTS_FILE,
    type=str,
    metavar="FILE"
)

args = parser.parse_args()


def install(core_file: str) -> None:
    install_requirement(core_file)
    install_app_requirements()


def install_app_requirements():
    app_requirements = find_app_requirements()
    for requirement in app_requirements:
        install_requirement(requirement)


def find_app_requirements() -> List[str]:
    return [file for file in glob.glob("./*/requirements.txt")]


def install_requirement(path: str) -> None:
    subprocess.run(
        ["pip", "install", "-r",  path],
        stdout=sys.stdout,
        stderr=sys.stderr,
        universal_newlines=True,
    )


install(args.core)
