# ##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2024 Université catholique de Louvain (http://www.uclouvain.be)
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
# ##############################################################################

import cProfile
import functools
import io
import logging
import os
import pstats
import sys

from django.conf import settings

logger = logging.getLogger(settings.DEFAULT_LOGGER)


def profile_db(func):
    """
        Decorator to profile execution time and number of queries of a function.
    """
    @functools.wraps(func)
    def _func(*args, **kwarg):
        from django.db import connection
        import time
        initial_number_queries = len(connection.queries)
        initial_time = time.time()
        result = func(*args, **kwarg)
        logger.debug(f"Function {func.__name__}")
        logger.debug(f"- Number of queries: {len(connection.queries) - initial_number_queries}")
        logger.debug(f"- Time of execution: {time.time() - initial_time} sec")
        return result
    return _func


def profile(only_project_and_native_method=False):
    """
        A decorator that uses cProfile to profile a function or method.

        This decorator profiles the execution time of the decorated function or method
        and prints the results to the standard output, sorted by cumulative time.

        Args:
            only_project_and_native_method (bool): If True, keep only calls from the project's source code
                                                   and built-in methods (e.g., {method 'count' of 'str' objects}).

        Usage:
            @profile(only_project_and_native_method=True)
            def my_function():

            @profile()
            def my_function():
    """
    def decorator(func):
        @functools.wraps(func)
        def _func(*args, **kwargs):
            pr = cProfile.Profile()
            pr.enable()
            result = func(*args, **kwargs)
            pr.disable()

            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats()

            output = s.getvalue()
            if only_project_and_native_method:
                project_path = os.getcwd()
                venv_path = sys.prefix
                filtered_lines = [
                    line for line in output.splitlines()
                    if (project_path in line or "{method" in line) and venv_path not in line
                ]
                output = "\n".join(filtered_lines)

            print(output)
            return result
        return _func
    return decorator
