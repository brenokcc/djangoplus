# -*- coding: utf-8 -*-
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('title', nargs='?')
        parser.add_argument('--upload', nargs='?', type=bool, default=False, const=True)

    def handle(self, *args, **options):
        title = options.pop('title', None)
        upload = options.pop('upload', False)
        call_command('test', record=True, upload=upload)
