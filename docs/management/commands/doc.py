# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from djangoplus.docs.doc import Workflow, UseCase


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('task', nargs='*', help='...')

    def handle(self, *args, **options):
        workflow = Workflow()

        input_task = (u' '.join([x.decode('utf-8') for x in options['task']])).strip()

        if input_task.isdigit():
            index = int(input_task)
            if len(workflow.tasks) > index > 0:
                input_task = workflow.tasks[index]

        if input_task:
            usecase = None
            for task in workflow.tasks:
                if input_task == task:
                    usecase = UseCase(task)
            if usecase:
                print unicode(usecase)
            else:
                if input_task.isdigit():
                    print u'There is no task with index %s' % input_task
                else:
                    print u'There is no task named %s' % input_task
        else:
            for i, task in enumerate(workflow.tasks):
                print u'%s. %s' % (i+1, task)
