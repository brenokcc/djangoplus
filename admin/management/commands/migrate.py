# -*- coding: utf-8 -*-

from django.core.management.commands import migrate
from djangoplus.admin.management import sync_permissions


class Command(migrate.Command):
    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        sync_permissions()
