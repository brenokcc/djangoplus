# -*- coding: utf-8 -*-

from importlib import import_module
from django.conf import settings


modules = list()

modules.append(import_module('django.template.defaultfilters'))
for item in settings.TEMPLATES:
    for builtins in item['OPTIONS']['builtins']:
        modules.append(import_module(builtins))


def apply_filter(obj, filter_name, **kwargs):
    for module in modules:
        if hasattr(module, filter_name):
            func = getattr(module, filter_name)
            return func(obj, **kwargs)
    return obj
