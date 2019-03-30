# -*- coding: utf-8 -*-
import json
import zlib
import base64
import types
import _pickle as cpickle
from django.apps import apps
from django.core import signing
from django.db.models import QuerySet, Model
from django.utils.text import slugify

from djangoplus.utils import get_fieldsets, iterable
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


def serialize(attr_value, recursive=False):
    if isinstance(attr_value, types.MethodType) or isinstance(attr_value, types.FunctionType):
        attr_value = attr_value()
    if isinstance(attr_value, QuerySet) or hasattr(attr_value, 'all'):
        serialized_value = []
        for obj in attr_value.all():
            serialized_value.append(serialize(obj))
    elif isinstance(attr_value, Model):
        obj = attr_value
        obj_dict = dict(id=obj.pk)
        if recursive:
            obj_dict['text'] = str(obj)
        else:
            for attr_name in get_metadata(type(attr_value), 'list_display'):
                obj_dict[attr_name] = serialize(getattr(obj, attr_name), recursive=True)
        serialized_value = obj_dict
    elif type(attr_value).__name__ == 'QueryStatistics':
        query_statistics_table = attr_value.as_table()
        serialized_value = dict(
            header=query_statistics_table.header,
            rows=query_statistics_table.rows,
            footer=query_statistics_table.footer
        )
    else:
        serialized_value = format_value(attr_value, False)
    return serialized_value


def json_serialize(value, query_params, **extras):
    if isinstance(value, Model):
        serialized_value = dict()
        model = type(value)
        only = query_params.get('fields', [])
        fieldsets = get_metadata(model, 'fieldsets', get_fieldsets(model))
        for title, data in fieldsets:
            title = slugify(title.split('::')[-1]).replace('-', '_')
            if not only or title in only:
                serialized_value[title] = dict()
                fields = data.get('fields', [])
                for field_or_truple in fields:
                    for attr_name in iterable(field_or_truple):
                        if len(fields) == 1:
                            serialized_value[title] = serialize(getattr(value, attr_name), True)
                        else:
                            serialized_value[title][attr_name] = serialize(getattr(value, attr_name), True)
                relations = data.get('relations', [])
                for attr_name in relations:
                    if len(relations) == 1 and not fields:
                        serialized_value[title] = serialize(getattr(value, attr_name))
                    else:
                        serialized_value[title][attr_name] = serialize(getattr(value, attr_name))
    else:
        serialized_value = serialize(value)

    output_data = dict(result=serialized_value)
    for key, value in extras.items():
        output_data[key] = value
    try:
        return json.dumps(output_data, indent=4, sort_keys=True, ensure_ascii=False)
    except TypeError as e:
        return json.dumps(dict(error=str(e)))
