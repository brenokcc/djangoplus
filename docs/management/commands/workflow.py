# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from djangoplus.docs.utils import workflow_as_string


class Command(BaseCommand):
    def handle(self, *args, **options):
        print workflow_as_string()
