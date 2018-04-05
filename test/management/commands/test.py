# -*- coding: utf-8 -*-

import os
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
        parser.add_argument('--add', action='store_true', dest='add', default=(),
                            help='Adds test cases in test.py file')
        parser.add_argument('--watch', action='store_true', dest='watch', default=False,
                            help='Run test in browser intead of headless mode')

    def handle(self, *args, **options):
        if not options.pop('watch', False):
            os.environ['HEADLESS'] = '1'
        if options.pop('add', False):
            workflow = Workflow()
            function_definitions = []
            function_calls = []
            test_file_path = path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'tests.py')
            file_content = open(test_file_path).read()
            try:
                for task in workflow.tasks:
                    usecase = UseCase(task)
                    function_calls.append('\n'.join(usecase.get_test_flow_code()))
                    if usecase.get_test_function_code():
                        function_definitions.append('\n'.join(usecase.get_test_function_code()))
                function_definitions_code = '\n\n'.join(function_definitions)
                file_content = file_content.replace('(TestCase):', '(TestCase):\n\n{}'.format(function_definitions_code), 1)
                file_content = '{}\n{}'.format(file_content, '\n'.join(function_calls))
                file_content = file_content.replace('\t', '    ')
                open(test_file_path, 'w').write(file_content)
            except ZeroDivisionError as e:
                print(e)

        else:
            if options.pop('continue', False):
                file_path = '/tmp/{}.test'.format(settings.PROJECT_NAME)
                file_content = path.exists(file_path) and open(file_path).read() or ''
                if file_content:
                    data = json.loads(file_content)
                    cache.LOGIN_COUNT = data.get('login_count', None)
                    username = data.get('username', None)
                    password = data.get('password', None)
                    print('Continuing from login #{} with user "{}" and password "{}"'.format(cache.LOGIN_COUNT, username, password))

            super(Command, self).handle(*args, **options)
