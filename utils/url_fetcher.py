##############################################################################
#
#    OSIS stands for Open Student Information System. It's an application
#    designed to manage the core business of higher education institutions,
#    such as universities, faculties, institutes and professional schools.
#    The core business involves the administration of students, teachers,
#    courses, programs and so on.
#
#    Copyright (C) 2015-2023 Université catholique de Louvain (http://www.uclouvain.be)
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
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from django.urls import get_script_prefix


def django_url_fetcher(url):  # pragma: no cover
    """
    Django URL fetcher to prevent network requests

    @see https://github.com/fdemmer/django-weasyprint/blob/main/django_weasyprint/utils.py
    """
    from weasyprint import default_url_fetcher

    # load static files directly from disk
    if url.startswith('file:'):
        mime_type, encoding = mimetypes.guess_type(url)
        url_path = urlparse(url).path
        data = {
            'mime_type': mime_type,
            'encoding': encoding,
            'filename': Path(url_path).name,
        }

        default_media_url = settings.MEDIA_URL in ('', get_script_prefix())
        if not default_media_url and url_path.startswith(settings.MEDIA_URL):
            media_root = settings.MEDIA_ROOT
            if isinstance(settings.MEDIA_ROOT, Path):
                media_root = f'{settings.MEDIA_ROOT}/'
            path = url_path.replace(settings.MEDIA_URL, media_root, 1)
            data['file_obj'] = default_storage.open(path)
            return data

        elif settings.STATIC_URL and url_path.startswith(settings.STATIC_URL):
            path = url_path.replace(settings.STATIC_URL, '', 1)
            try:
                data['file_obj'] = staticfiles_storage.open(path)
            except ImproperlyConfigured:
                data['file_obj'] = open(find(path), 'rb')
            return data

    # Fall back to weasyprint default fetcher
    return default_url_fetcher(url)
