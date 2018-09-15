# -*- coding: utf-8 -*-
import time
import djangoplus
from djangoplus.tools.video import VideoRecorder
from django.core.management.base import BaseCommand
from djangoplus.tools.editor import EditorSimulator


BASE_DIR = djangoplus.__path__[0]


def test1():
    editor = EditorSimulator('{}/tutorial/tools.py'.format(BASE_DIR))
    editor.proccess_lines()
    editor.write('Breno! =)', 11)
    editor.write('# OK', 20)
    editor.write(', muito massa', 11, 5)
    editor.write('# primeira linha', 1)
    editor.write('# linha 40', 40)
    editor.save('/tmp/output.txt')
    editor.close()


def test2():
    editor = EditorSimulator('{}/tutorial/files/sample.txt'.format(BASE_DIR))
    editor.simulate(3, 5, pause=False)
    time.sleep(3)
    editor.simulate(8, 9, pause=True)


def test3():
    editor = EditorSimulator()
    editor.write('linha 1', 1)
    editor.write('linha 2', 2)
    editor.write('complemento da linha 2', 2, 8)
    editor.write('linha 3', 3)
    editor.write('linha 4', 4)
    for i in range(5, 25):
        editor.write('linha {}'.format(i), i)
    editor.write('Nova linha 2', 2)
    editor.write('Nova linha 20', 20)
    editor.write('Nova linha 13', 13)
    editor.write('Nova linha 14', 14)
    editor.write('Nova linha 15', 15)
    editor.close()


def test4():
    editor = EditorSimulator('{}/tutorial/tools.py'.format(BASE_DIR), slow=False)
    editor.simulate()
    editor.save('/tmp/output.txt')


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('file_path', default=None)
        parser.add_argument('start', type=float, nargs='?', default=None)
        parser.add_argument('end', type=float, nargs='?', default=None)
        parser.add_argument('--record', action='store_true', dest='record', default=False)
        parser.add_argument('--fast', action='store_true', dest='fast', default=False)

    def handle(self, *args, **options):
        recorder = VideoRecorder()
        file_path = options.pop('file_path')
        start = options.pop('start')
        end = options.pop('end')
        record = options.pop('record', False)
        fast = options.pop('fast', False)

        if record:
            recorder.start()
        try:
            if file_path == '1':
                test1()
            elif file_path == '2':
                test2()
            elif file_path == '3':
                test3()
            elif file_path == '4':
                test4()
            else:
                editor = EditorSimulator(file_path, slow=not fast)
                editor.simulate(start_step=start, end_step=end)
        finally:
            if record:
                recorder.stop(file_path.split('/')[-1])

