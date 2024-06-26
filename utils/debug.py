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
import pstats

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


def profile(func):
    """
        A decorator that uses cProfile to profile a function or method.

        This decorator profiles the execution time of the decorated function or method
        and prints the results to the standard output, sorted by cumulative time.
    """
    @functools.wraps(func)
    def _func(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        print(s.getvalue())
        return result
    return _func
