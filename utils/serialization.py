# -*- coding: utf-8 -*-

import zlib
import base64
import _pickle as cpickle
from django.apps import apps
from django.core import signing


def dumps_qs_query(qs):
    serialized_str = base64.b64encode(zlib.compress(cpickle.dumps(qs.query))).decode()
    payload = {
        'model_label': getattr(qs.model, '_meta').label,
        'query': serialized_str,
    }
    return signing.dumps(payload)


def loads_qs_query(data):
    payload = signing.loads(data)
    model = apps.get_model(payload['model_label'])
    queryset = model.objects.none()
    queryset.query = cpickle.loads(zlib.decompress(base64.b64decode(payload['query'])))
    return queryset
