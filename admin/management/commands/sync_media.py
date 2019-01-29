# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from djangoplus.utils.storage.dropbox import DropboxStorage


class Command(BaseCommand):
    def handle(self, *args, **options):
        DropboxStorage().sync()
