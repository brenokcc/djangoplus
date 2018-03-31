# -*- coding: utf-8 -*-
from djangoplus.ui import Component
from djangoplus.utils import terminal
from django.core.management.base import BaseCommand
from djangoplus.docs.utils import extract_documentation


class Command(BaseCommand):

    def handle(self, *args, **options):
        for cls in Component.__subclasses__():
            name = terminal.bold(cls.__name__)
            description = extract_documentation(cls)
            print('{}: {}'.format(name, description))