# -*- coding: utf-8 -*-

import zlib
import base64
import pickle
from django.apps import apps


def dumps_qs_query(qs):
    query = base64.b64encode(zlib.compress(pickle.dumps(qs.query)))[::-1].decode('utf-8')
    return '{}:::{}:::{}'.format(qs.model._meta.app_label, qs.model.__name__, query)


def loads_qs_query(s):
    app_label, model_name, query = s.split(':::')
    query = pickle.loads(zlib.decompress(base64.b64decode(query[::-1])))
    qs = apps.get_model(app_label, model_name).objects.all()
    qs.query = query
    return qs