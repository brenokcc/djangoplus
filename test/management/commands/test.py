# -*- coding: utf-8 -*-
import json
from os import path
from django.conf import settings
from djangoplus.test import cache
from djangoplus.docs.doc import Workflow, UseCase
from django.core.management.commands import test


class Command(test.Command):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--continue', action='store_true', dest='continue', default=False,
                            help='Continues from the last successfull login')
        parser.add_argument('--generate', action='store_true', dest='generate', default=(),
                            help='Adds test cases in test.py file')

    def handle(self, *args, **options):
        if options.pop('generate', False):
            workflow = Workflow()
            function_definitions = []
            function_calls = []
            test_file_path = path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'tests.py')
            file_content = open(test_file_path).read().decode('utf-8')
            try:
                for task in workflow.tasks:
                    usecase = UseCase(task)
                    function_calls.append(u'\n'.join(usecase.get_test_flow_code()))
                    if usecase.get_test_function_code():
                        function_definitions.append(u'\n'.join(usecase.get_test_function_code()))
                function_definitions_code = u'\n\n'.join(function_definitions)
                file_content = file_content.replace(u'(TestCase):', u'(TestCase):\n\n%s' % function_definitions_code, 1)
                file_content = '%s\n%s' % (file_content, u'\n'.join(function_calls))
                file_content = file_content.replace('\t', '    ')
                open(test_file_path, 'w').write(file_content.encode('utf-8'))
            except ZeroDivisionError, e:
                print e

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
