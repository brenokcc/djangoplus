# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.management.base import BaseCommand
from djangoplus.admin.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        User.objects.all()
        for user in User.objects.all():
            user.set_password(settings.DEFAULT_PASSWORD)
            user.save()
