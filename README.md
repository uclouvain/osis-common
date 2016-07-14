=====
Osis-Common
=====

All common functionalitites to all Osis apps

Quick start
-----------

1. Add "common" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'common',
    ]

2. Include the polls URLconf in your project urls.py like this::

    url(r'^comm/', include('common.urls')),

3. Run `python manage.py migrate` to create the common models.

4. Start the development server and visit http://127.0.0.1:8000
