# -*- coding: utf-8 -*-

import os
from djangoplus import test
from django.conf import settings


def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer


@parametrized
def testcase(func, title, username=settings.DEFAULT_SUPERUSER, password=settings.DEFAULT_PASSWORD, record=True):
    def wrapper(self):

        if username:
            if username != self.current_username:
                self.login(username, password)
            self.back()

        if test.CACHE['RECORD'] and record:
            print('Start recording {}'.format(func.__name__))
            self.recorder.start()
            if title:
                self.subtitle.display(title)

        func(self)

        if test.CACHE['RECORD'] and record:
            self.wait(6)
            output_dir = os.path.join(settings.BASE_DIR, 'videos')
            self.recorder.stop(title, output_dir, self.AUDIO_FILE_PATH)
            print('Stoped recording {}'.format(func.__name__))

        self.dump(func.__name__)

    test.CACHE['SEQUENCE'] += 1
    wrapper._sequence = test.CACHE['SEQUENCE']
    wrapper._funcname = func.__name__
    test.CACHE['RECORDING'] = False
    return wrapper
