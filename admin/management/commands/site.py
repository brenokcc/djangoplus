# -*- coding: utf-8 -*-
import os
from django.core.management.base import BaseCommand
from fabric.api import *

env.user = 'root'


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--update', action='store_true', dest='update', default=False,
                            help='Updates djangoplus.net')
        parser.add_argument('--update-samples', action='store_true', dest='update_samples', default=False,
                            help='Updates samples at djangoplus.net')
        parser.add_argument('--test-samples', action='store_true', dest='test_samples', default=False,
                            help='Tests samples at djangoplus.net')

    def handle(self, *args, **options):
        if options.get('update'):
            execute(_update_site, host='djangoplus.net')
        if options.get('update_samples'):
            execute(_update_samples, host='djangoplus.net')
        if options.get('test_samples'):
            execute(_test_samples, host='djangoplus.net')


def _update_site():
    if os.path.exists('/Users/breno'):
        with lcd('/Users/breno/Documents/Workspace/djangoplus/site'):
            if 'nothing to commit' not in local('git status', capture=True):
                local('git commit -am \'.\'')
                local('git push origin master')
        with cd('/var/www/html'):
            run('git pull origin master')


def _test_samples():
    with lcd('/tmp'):
        for project_name in ('petshop', 'loja', 'biblioteca'):
            project_path = '/tmp/{}'.format(project_name)
            zip_path = '/{}.zip'.format(project_name)
            if os.path.exists(zip_path):
                local('rm {}'.format(zip_path))
            if os.path.exists(project_path):
                local('rm -r {}'.format(project_path))
            local('wget http://{}.djangoplus.net/media/{}.zip'.format(project_name, project_name))
            local('unzip {}.zip -d {}'.format(project_name, project_name))
            with lcd(project_path):
                local('/Users/breno/Envs/djangoplus/bin/python manage.py test')


def _update_samples():
    for project_name in ('petshop', 'loja', 'biblioteca'):
        if os.path.exists('/Users/breno'):
            project_path = '/Users/breno/Documents/Workspace/djangoplus/djangoplus-demos/{}'.format(project_name)
            with lcd(project_path):
                local('pwd')
                if 'nothing to commit' not in local('git status', capture=True):
                    local('git commit -am \'.\'')
                    local('git push origin master')
            with cd('/var/opt/{}'.format(project_name)):
                run('pwd')
                run('git checkout .')
                run('git pull origin master')
                if project_name == 'petshop':
                    run("sed -i 's/#:.*//g' petshop/models.py")
                run('workon {} && python manage.py zip'.format(project_name))