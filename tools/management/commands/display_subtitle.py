# -*- coding: utf-8 -*-
from djangoplus.tools.subtitle import Subtitle
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('words', nargs='*', default=None)

    def handle(self, *args, **options):
        words = options.pop('words')
        Subtitle.display(' '.join(words).replace('\\n', '\n'))
