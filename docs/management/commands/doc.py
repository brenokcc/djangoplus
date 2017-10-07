# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from djangoplus import docs


class Command(BaseCommand):
    def handle(self, *args, **options):
        print docs.documentation(as_json=True)
