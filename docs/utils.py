# -*- coding: utf-8 -*-

import re
import inspect
from django.apps import apps
from django.utils.translation import ugettext as _
from djangoplus.utils.metadata import get_metadata, get_fiendly_name


def extract_documentation(model):
    s = ''
    if model.__doc__:
        if not model.__doc__.startswith('{}('.format(model.__name__)):
            s = model.__doc__
            s = s.replace('\t', '').replace('\n', '').replace('  ', ' ').strip()
    return s


def extract_exception_messages(function):
    messages = []
    if function:
        code = ''.join([x for x in inspect.getsourcelines(function)[0]])
        for message in re.findall('ValidationError.*\(.*\)', code):
            messages.append(
                message[message.index('(') + 1:message.index(')') - 1].replace('u\'', '').replace('"', ''))
    return messages


def get_search_fields(model):
    l = []
    lookups = get_metadata(model, 'search_fields', [])
    if lookups:
        for i, lookup in enumerate(lookups):
            l.append('"{}"'.format(get_fiendly_name(model, lookup).lower()))
            if i > 0 and i == len(lookups) - 2:
                l.append(_(' or '))
            elif i < len(lookups) - 2:
                l.append(',')
    return ''.join(l)


def get_list_filter(model):
    l = []
    lookups = get_metadata(model, 'list_filter', [])
    if lookups:
        for i, lookup in enumerate(lookups):
            l.append('"{}"'.format(get_fiendly_name(model, lookup).lower()))
            if i > 0 and i == len(lookups) - 2:
                l.append(_(' or '))
            elif i < len(lookups) - 2:
                l.append(', ')
    return ''.join(l)


def get_list_display(model):
    l = []
    lookups = get_metadata(model, 'list_display', [])
    for i, lookup in enumerate(lookups):
        if i > 0:
            if i == len(lookups) - 1:
                l.append(_(' and '))
            else:
                l.append(', ')
        l.append('"{}"'.format(get_fiendly_name(model, lookup).lower()))
    return ''.join(l)


def documentation(as_json=False):

    for app_config in apps.get_app_configs():
        description = app_config.module.__doc__
