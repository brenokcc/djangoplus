# -*- coding: utf-8 -*-
import os
import psycopg2
import sqlite3
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        dbinfo = settings.DATABASES.get('postgres')
        username, password = dbinfo['USER'], dbinfo['PASSWORD']

        # (re)creating postgres database
        conn = psycopg2.connect('user={} password={}'.format(username, password))
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute('{} {};'.format('drop database if exists', settings.PROJECT_NAME))
        cur.execute('{} {};'.format('create database', settings.PROJECT_NAME))
        cur.close()
        conn.close()

        # creating tables
        call_command('migrate', database='postgres', ignore_sync_permissions=True)

        # reseting permission mapping on admin_users to avoid error on data loading
        conn = sqlite3.connect('sqlite.db')
        cur = conn.cursor()
        cur.execute('update admin_user set permission_mapping = "{}";')
        conn.commit()
        conn.close()

        # deleting content types to avoid error on data loading
        conn = psycopg2.connect('dbname={} user={} password={}'.format(settings.PROJECT_NAME, username, password))
        cur = conn.cursor()
        cur.execute('delete from django_content_type;')
        conn.commit()
        conn.close()

        # dumping data in temporary file
        with open('/tmp/output.json', 'w+') as f:
            call_command('dumpdata', database='sqlite', stdout=f)
            f.close()

        # loading data
        call_command('loaddata', '/tmp/output.json', database='postgres')

        # deleting temporary file
        os.unlink('/tmp/output.json')

