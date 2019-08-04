import sys
from collections import OrderedDict
from django.db import connection
from django.core import serializers
from django.db.transaction import atomic

from django.core.management.base import BaseCommand


def update_sequence_value(model):
    last_value = (model.objects.exists() and model.objects.values_list('pk', flat=True).order_by('-id')[0] or 0)
    cursor = connection.cursor()
    cursor.execute('select last_value from %s_id_seq' % model._meta.db_table)
    value = cursor.fetchone()[0]
    if value <= last_value:
        cursor.execute('ALTER SEQUENCE %s_id_seq RESTART WITH %s' % (model._meta.db_table, last_value+1))
        print('Updating sequence for %s to %s' % (model.__name__, last_value+1))


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('models', nargs='*', type=str)
        parser.add_argument('--add', action='store_true', dest='add', default=())

    @atomic
    def handle(self, models, **options):
        data = OrderedDict()
        l = []
        for arg in models:
            data[arg] = []
        s = sys.stdin.read()
        for obj in serializers.deserialize("json", s):
            if obj.object.__class__.__name__ in data:
                data[obj.object.__class__.__name__].append(obj.object)
                if obj.object.__class__ not in l:
                    l.append(obj.object.__class__)

        for key in data:
            print(key, len(data[key]))
            for obj in data[key]:
                obj.save()

        if options.pop('add', False):
            for model in l:
                update_sequence_value(model)