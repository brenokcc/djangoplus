# -*- coding: utf-8 -*-

import os
from djangoplus.conf import base_settings
from django.conf import settings
from django.utils import termcolors
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


def print_and_call(command, *args, **kwargs):
    kwargs.setdefault('interactive', True)
    print(termcolors.make_style(fg='cyan', opts=('bold',))('>>> {} {}{}'.format(
        command, ' '.join(args), ' '.join(['{}={}'.format(k, v) for k, v in list(kwargs.items())]))))
    call_command(command, *args, **kwargs)


class Command(BaseCommand):
    def handle(self, *args, **options):

        app_labels = []
        for app_label in settings.INSTALLED_APPS:
            if app_label not in base_settings.INSTALLED_APPS and '.' not in app_label:
                app_labels.append(app_label)

        print_and_call('makemigrations', *app_labels)
        print_and_call('migrate')

        # if there's no user, lets create admin user
        User = get_user_model()
        if not User.objects.exists():
            user = User.objects.create_superuser(settings.DEFAULT_SUPERUSER, None, settings.DEFAULT_PASSWORD)
            user.name = 'Admin'
            user.save()

        # if it is the production enverinoment, lets collect static files
        if os.path.exists(os.path.join(settings.BASE_DIR, 'logs')):
            print_and_call('collectstatic', clear=True, verbosity=0, interactive=False)
