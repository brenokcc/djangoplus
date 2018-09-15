# -*- coding: utf-8 -*-
import os
import signal
from time import sleep
from subprocess import Popen, PIPE, DEVNULL
from djangoplus.tools.terminal import simulate_type


class HttpServer(object):
    def __init__(self, base_dir, verbose=True, python='python'):
        self.process = None
        self.base_dir = base_dir
        self.verbose = verbose
        self.python = python

    def start(self):
        command = 'cd {} && {} manage.py runserver'.format(self.base_dir, self.python)
        if self.verbose:
            os.system('clear')
            simulate_type('python manage.py runserver', shell=True)
            stdout = PIPE
        else:
            stdout = DEVNULL
        self.process = Popen(command, stdout=stdout, stderr=PIPE, shell=True, preexec_fn=os.setsid)
        sleep(5)

    def stop(self):
        if self.verbose:
            print('^C')
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

