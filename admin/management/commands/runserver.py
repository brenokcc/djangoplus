# -*- coding: utf-8 -*-

from django.core.management.commands import runserver

from djangoplus.admin.models import User


class Command(runserver.Command):

    def handle(self, *args, **options):
        User.objects.update(permission_mapping='{}')
        super(Command, self).handle(*args, **options)
