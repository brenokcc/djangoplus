# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.management.base import BaseCommand
from djangoplus.cache import loader


class Command(BaseCommand):
    def handle(self, *args, **options):
        for model in loader.role_models:
            for obj in model.objects.all():
                obj.save()
