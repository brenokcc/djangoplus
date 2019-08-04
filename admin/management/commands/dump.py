# -*- coding: utf-8 -*-
from django.db.models.deletion import Collector
from django.core import serializers
from django.core.management.base import BaseCommand
import pdb

def dump(qs):
    l = []
    c = []
    collector = Collector('default')
    def dump_related_objects(instance):
        if instance.__class__.__name__ not in ['Log', 'RegistroDiferenca'] and instance not in l:
            l.append(instance)
            if instance.__class__.__name__ not in c:
                c.append(instance.__class__.__name__)

            related_fields = [
                f for f in instance.__class__._meta.get_fields(include_hidden=True)
                if (f.one_to_many or f.one_to_one)
                and f.auto_created and not f.concrete
            ]
            
            qs = instance.__class__.objects.filter(pk=instance.pk)
            for related_field in related_fields:
                objs = collector.related_objects(related_field, qs)
                for obj in objs:
                    if obj not in l:
                        dump_related_objects(obj)
    for instance in qs:
        print('Loading', instance.pk, instance)
        dump_related_objects(instance)
    return c, l

class Command(BaseCommand):
    def handle(self, *args, **options):
        queryset = None
        print('\nPlease, instanciate the queryset to be saved and then press the key "c".\nThe models must be previously imported.\n\tEx: from djangoplus.admin.models import User\n\tqueryset = User.objects.filter(pk=1)\n\n')
        pdb.set_trace()
        c, l = dump(queryset)
        print('A "dump.json" was saved in the current directory with %s objects. In order to restore then, type:\n\n\tpython manage.py restore %s < dump.json\n\n' % (len(l) , ' '.join(c)))
        f = open('dump.json', 'w')
        f.write(serializers.serialize("json", l))
        f.close()
