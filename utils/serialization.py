# -*- coding: utf-8 -*-
import json
import zlib
import base64
import _pickle as cpickle
from django.apps import apps
from django.core import signing
from django.db.models import QuerySet, Model
from djangoplus.utils.formatter import format_value
from djangoplus.utils.metadata import get_metadata, getattr2


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


def json_serialize(value, **extras):
    if isinstance(value, Model):
        list_display = list(get_metadata(value, 'list_display'))
        list_display.insert(0, 'id')
        serialized_value = dict()
        for attr in list_display:
            attr_value = getattr2(value, attr)
            if isinstance(attr_value, QuerySet):
                attr_value = list(attr_value.values_list('pk', flat=True))
            elif isinstance(attr_value, Model):
                attr_value = attr_value.pk
            else:
                attr_value = format_value(attr_value, False)
            serialized_value[attr] = attr_value
    elif isinstance(value, QuerySet):
        list_display = list(get_metadata(value.model, 'list_display'))
        list_display.insert(0, 'id')
        serialized_value = []
        for item in value.values(*list_display):
            instance = dict()
            for key, value in item.items():
                instance[key] = value
            serialized_value.append(instance)
    elif type(value).__name__ == 'QueryStatistics':
        query_statistics_table = value.as_table(None)
        serialized_value = dict(
            header=query_statistics_table.header,
            rows=query_statistics_table.rows,
            footer=query_statistics_table.footer
        )
    elif value is not None:
        serialized_value = format_value(value, False)
    else:
        serialized_value = None

    output_data = dict(result=serialized_value)
    for key, value in extras.items():
        output_data[key] = value
    try:
        return json.dumps(output_data, indent=4, sort_keys=True, ensure_ascii=False)
    except TypeError as e:
        return json.dumps(dict(error=str(e)))
