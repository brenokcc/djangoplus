# -*- coding: utf-8 -*-
from django.core.management.commands import test
from djangoplus.test import cache
from django.conf import settings
from os import path
import json

from djangoplus.test.utils import TestCaseGenerator


class Command(test.Command):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--continue', action='store_true', dest='continue', default=False,
                            help='Continues from the last successfull login')
        parser.add_argument('--add', action='store_true', dest='add', default=(),
                            help='Adds test cases in test.py file')

    def handle(self, *args, **options):
        if options.pop('add', False):
            test_generator = TestCaseGenerator()
            test_generator.generate(args)
            test_generator.save()
        else:
            if options.pop('continue', False):
                file_path = '/tmp/%s.test' % settings.PROJECT_NAME
                file_content = path.exists(file_path) and open(file_path).read() or ''
                if file_content:
                    data = json.loads(file_content)
                    cache.LOGIN_COUNT = data.get('login_count', None)
                    username = data.get('username', None)
                    password = data.get('password', None)
                    print 'Continuing from login #%s with user "%s" and password "%s"' % (cache.LOGIN_COUNT, username, password)

            super(Command, self).handle(*args, **options)
