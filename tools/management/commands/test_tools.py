# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from djangoplus.tools.video import VideoRecorder
from djangoplus.tools.subtitle import Subtitle
from djangoplus.tools.browser import Browser


class Command(BaseCommand):

    def handle(self, *args, **options):
        recorder = VideoRecorder()
        browser = Browser('http://google.com.br')
        browser.open('/')
        recorder.start()
        Subtitle.display('This is only a test', 3)
        recorder.stop('Test')
        browser.close()
        browser.service.stop()
