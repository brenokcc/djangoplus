# -*- coding: utf-8 -*-

import os
import json
from os import path
from django.conf import settings
from djangoplus.test import cache
from djangoplus.docs.diagrams import Workflow
from djangoplus.docs.usecase import UseCase
from django.core.management.commands import test


class Command(test.Command):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--resume', action='store_true', dest='resume', default=False,
                            help='Resumes from the last successfull testcase')
        parser.add_argument('--continue', action='store', nargs=1, dest='continue', default=False,
                            help='Continues from a specified testcase')
        parser.add_argument('--testcase', action='store', nargs=1, dest='testcase', default=False,
                            help='Executes a specified testcase')
        parser.add_argument('--generate', action='store_true', dest='generate', default=(),
                            help='Adds test cases in test.py file')
        parser.add_argument('--watch', action='store_true', dest='watch', default=False,
                            help='Run tests in browser instead of headless mode')
        parser.add_argument('--record', action='store_true', dest='record', default=False,
                            help='Record a video for the testcase as a tutorial')
        parser.add_argument('--pause', action='store_true', dest='pause', default=False,
                            help='Pauses after the execution of the last testcase')

        parser.add_argument('--usecases', action='store_true', dest='usecases', default=False,
                            help='Lists the available testcases')
        parser.add_argument('--usecase', action='store', nargs=1, dest='usecase', default=False,
                            help='Generates the code for a specific testcase')

    def handle(self, *args, **options):
        watch = options.pop('watch', False)
        record = options.pop('record', False)
        upload = options.pop('upload', False)
        pause = options.pop('pause', False)

        usecases = options.pop('usecases', False)
        usecase = options.pop('usecase', False)

        if not watch and not record:
            cache.HEADLESS = True
        if record or upload:
            cache.RECORD = True
        cache.PAUSE = pause

        if options.pop('generate', False):
            workflow = Workflow()
            test_file_path = path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'tests.py')
            code_list = []
            file_content = open(test_file_path).read()
            try:
                for task in workflow.tasks:
                    usecase = UseCase(task)
                    code = usecase.get_test_function_code()
                    if code and usecase.get_test_function_signature() not in file_content:
                        code_list.append(code)
                if code_list:
                    new_file_content = '{}\n{}\n'.format(file_content, '\n\n'.join(code_list))
                    # print(new_file_content)
                    open(test_file_path, 'w').write(new_file_content)
                    print('Testcases succesfully generanted into file "{}/tests.py"'.format(settings.PROJECT_NAME))
            except ZeroDivisionError as e:
                print(e)

        else:
            if options.pop('resume', False):
                file_path = '/tmp/{}.test'.format(settings.PROJECT_NAME)
                file_content = path.exists(file_path) and open(file_path).read() or ''
                if file_content:
                    data = json.loads(file_content)
                    cache.RESUME = data.get('step', None)
                    print('Resuming from step #{}'.format(cache.RESUME))
            elif options.get('testcase', False):
                cache.STEP = options.get('testcase')[0]
                print('Executing step #{}'.format(cache.STEP))
            elif options.get('continue', False):
                cache.CONTINUE = options.get('continue')[0]
                print('Continuing from step #{}'.format(cache.CONTINUE))
            super(Command, self).handle(*args, **options)
