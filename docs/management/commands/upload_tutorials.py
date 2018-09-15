# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from djangoplus.tools.video import VideoUploader


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('file_path')
        parser.add_argument('title')

    def handle(self, *args, **options):
        file_path = options.pop('file_path')
        title = options.pop('title')
        VideoUploader.upload_video(file_path, title)
