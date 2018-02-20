# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import zlib
import base64
import cPickle
from django.apps import apps

def dumps_qs_query(qs):
    query = base64.b64encode(zlib.compress(cPickle.dumps(qs.query)))[::-1]
    return '{}:::{}:::{}'.format(qs.model._meta.app_label, qs.model.__name__, query)


def loads_qs_query(s):
    app_label, model_name, query = s.split(':::')
    query = cPickle.loads(zlib.decompress(base64.b64decode(query[::-1])))
    qs = apps.get_model(app_label, model_name).objects.all()
    qs.query = query
    return qs