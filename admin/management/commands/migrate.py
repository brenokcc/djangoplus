# -*- coding: utf-8 -*-

from django.core.management.commands import migrate
from djangoplus.admin.management import sync_permissions


class Command(migrate.Command):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--ignore_sync_permissions', action='store_true', dest='ignore_sync_permissions')

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        if not options.get('ignore_sync_permissions'):
            sync_permissions()
