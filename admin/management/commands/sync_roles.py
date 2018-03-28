# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from djangoplus.admin.models import User, Role
from djangoplus.cache import loader


class Command(BaseCommand):
    def handle(self, *args, **options):
        Role.objects.all().delete()
        for cls in loader.role_models:
            for o in cls.objects.all():
                o.save()
        User.objects.filter(role__group__isnull=True).exclude(is_superuser=True).delete()
