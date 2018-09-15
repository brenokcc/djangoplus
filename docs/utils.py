# -*- coding: utf-8 -*-

import re
import inspect
from django.utils.translation import ugettext as _
from djangoplus.utils.metadata import get_metadata, get_fiendly_name


def extract_documentation(model):
    s = None
    if model.__doc__:
        if not model.__doc__.startswith('{}('.format(model.__name__)):
            s = model.__doc__
            s = s.replace('\t', '').replace('\n', '').replace('  ', ' ').strip()
    return s or ''


def extract_exception_messages(func):
    messages = []
    if func:
        code = ''.join([x for x in inspect.getsourcelines(func)[0]])
        for message in re.findall('ValidationError.*\(.*\)', code):
            messages.append(
                message[message.index('(') + 1:message.index(')') - 1].replace('u\'', '').replace('"', ''))
    return messages


def get_search_fields(model):
    output = []
    lookups = get_metadata(model, 'search_fields', [])
    if lookups:
        for i, lookup in enumerate(lookups):
            output.append('"{}"'.format(get_fiendly_name(model, lookup).lower()))
            if i > 0 and i == len(lookups) - 2:
                output.append(_(' or '))
            elif i < len(lookups) - 2:
                output.append(',')
    return ''.join(output)


def get_list_filter(model):
    output = []
    lookups = get_metadata(model, 'list_filter', [])
    if lookups:
        for i, lookup in enumerate(lookups):
            output.append('"{}"'.format(get_fiendly_name(model, lookup).lower()))
            if i > 0 and i == len(lookups) - 2:
                output.append(_(' or '))
            elif i < len(lookups) - 2:
                output.append(', ')
    return ''.join(output)


def get_list_display(model):
    output = []
    lookups = get_metadata(model, 'list_display', [])
    for i, lookup in enumerate(lookups):
        if i > 0:
            if i == len(lookups) - 1:
                output.append(_(' and '))
            else:
                output.append(', ')
        output.append('"{}"'.format(get_fiendly_name(model, lookup).lower()))
    return ''.join(output)

