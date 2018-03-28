# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
import os
import zipfile
from django.conf import settings


class Command(BaseCommand):
    def handle(self, *args, **options):
        zip_file_name = '{}.zip'.format(settings.PROJECT_NAME)

        def zipdir(file_path, ziph):
            for dirname, subdirs, files in os.walk(file_path):
                for filename in files:
                    absname = os.path.abspath(os.path.join(dirname, filename))
                    arcname = absname[len(settings.BASE_DIR) + 1:]
                    ignore = ('.git', 'gunicorn_start.sh', zip_file_name, 'logs', 'static')
                    add_file = True
                    for word in ignore:
                        if word in arcname:
                            add_file = False
                    if add_file:
                        ziph.write(absname, arcname)

        zip_file_path = os.path.join(settings.MEDIA_ROOT, zip_file_name)
        zipf = zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED)
        zipdir(settings.BASE_DIR, zipf)
        zipf.close()
