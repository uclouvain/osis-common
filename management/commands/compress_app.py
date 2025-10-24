import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.test.utils import override_settings

class Command(BaseCommand):
    help = "Compression ciblée sur une app Django depuis un management command"

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            required=True,
            help='Nom de l\'application Django à compresser',
        )

    def handle(self, *args, **options):
        app_name = options['app']

        template_dir = os.path.join(settings.BASE_DIR, app_name, 'templates', app_name)
        static_dir = os.path.join(settings.BASE_DIR, app_name, 'static')
        new_templates = [{
            **settings.TEMPLATES[0],
            'DIRS': [template_dir],
            'OPTIONS': {}
        }]
        extra_settings = {
            'TEMPLATES': new_templates,
            'COMPRESS_ROOT': static_dir,
            'STATIC_ROOT': static_dir,
            'COMPRESS_ENABLED': True,
            'STATICFILES_FINDERS': [
                "django.contrib.staticfiles.finders.FileSystemFinder",
                "django.contrib.staticfiles.finders.AppDirectoriesFinder",
                "django_components.finders.ComponentsFileSystemFinder",
                "compressor.finders.CompressorFinder",
            ]
        }

        with override_settings(**extra_settings):
            self.stdout.write(self.style.WARNING(f"Template DIRS temporaire: {template_dir}"))
            self.stdout.write(self.style.WARNING(f"COMPRESS_ROOT temporaire: {static_dir}"))

            call_command('compress', force=True, verbosity=options.get('verbosity', 1))
            self.stdout.write(self.style.SUCCESS("Compression terminée avec succès."))
