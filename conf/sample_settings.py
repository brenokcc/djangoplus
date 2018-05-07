# -*- coding: utf-8 -*-

from os import sep
from djangoplus.conf.base_settings import *
from os.path import abspath, dirname, join, exists

BASE_DIR = abspath(dirname(dirname(__file__)))
PROJECT_NAME = __file__.split(sep)[-2]

STATIC_ROOT = join(BASE_DIR, 'static')
MEDIA_ROOT = join(BASE_DIR, 'media')

DROPBOX_TOKEN = '' # disponível em https://www.dropbox.com/developers/apps
DROPBOX_LOCALDIR = MEDIA_ROOT
DROPBOX_REMOTEDIR = '/'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': join(BASE_DIR, 'sqlite.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

WSGI_APPLICATION = '{}.wsgi.application'.format(PROJECT_NAME)

INSTALLED_APPS += (
    PROJECT_NAME,
    'djangoplus.ui.themes.default',
)

ROOT_URLCONF = '{}.urls'.format(PROJECT_NAME)

if exists(join(BASE_DIR, 'logs')):
    DEBUG = False
    ALLOWED_HOSTS = ['*']

    HOST_NAME = ''
    DIGITAL_OCEAN_TOKEN = ''

    SERVER_EMAIL = 'root@djangoplus.net'
    ADMINS = [('Admin', 'root@djangoplus.net')]

    DROPBOX_TOKEN = ''
    BACKUP_FILES = ['media', 'sqlite.db']


EXTRA_JS = ['/static/js/$PROJECT_NAME.js']
EXTRA_CSS = ['/static/css/$PROJECT_NAME.css']

