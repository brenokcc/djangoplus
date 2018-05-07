# -*- coding: utf-8 -*-
from logging import StreamHandler


class CustomStreamHandler(StreamHandler):
    def emit(self, record):
        sql = record.getMessage()
        sql = sql.replace('\n            ', '')
        time = sql[0:8]
        if 'SELECT' in sql:
            sql = sql[8:]
            if 'COUNT' not in sql and 'FROM' in sql:
                sql = 'SELECT * {}'.format(sql[sql.index('FROM'):])
        elif 'BEGIN' in sql:
            sql = None
        elif 'UPDATE "django_session"' in sql:
            sql = None

        if sql:
            print(time, sql)
