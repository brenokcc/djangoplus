# -*- coding: utf-8 -*-

import json
from django.apps import apps
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from djangoplus.utils.serialization import dumps_qs_query, loads_qs_query
from djangoplus.utils.metadata import get_metadata


@login_required
@csrf_exempt
def autocomplete(request, app_name, class_name):
    results = []
    q = request.POST.get('q')
    qs = loads_qs_query(request.POST['qs[qs]'])
    search_fields = get_metadata(qs.model, 'search_fields', [])
    select_template = get_metadata(qs.model, 'select_template')
    select_display = get_metadata(qs.model, 'select_display')
    queryset = None
    if q:
        for i, search_field in enumerate(search_fields):
            if i == 0:
                queryset = qs.filter(**{'{}__icontains'.format(search_field): q})
            else:
                queryset = queryset | qs.filter(**{'{}__icontains'.format(search_field): q})
        if queryset is None:
            raise ValueError('The class {} does not have any search field.'.format(class_name))
    else:
        queryset = qs

    # queryset = queryset.all(request.user)
    for obj in queryset[0:25]:
        html = (select_template or select_display) and render_to_string(select_template or 'select_template.html', dict(obj=obj, select_display=select_display)) or str(obj)
        results.append(dict(id=obj.id, text=str(obj), html=html))
    s = json.dumps(dict(q=q, results=results))

    return HttpResponse(s)


@login_required
@csrf_exempt
def reload_options(request, app_name, class_name, current_value, lookup, selected_value, lazy):
    l = []
    pks = []
    if not current_value == '0':
        for pk in current_value.split('_'):
            pks.append(int(pk))
    selected_value = int(selected_value)
    lazy = int(lazy)
    cls = apps.get_model(app_name, class_name)
    select_template = get_metadata(cls, 'select_template')
    select_display = get_metadata(cls, 'select_display')
    queryset = cls.objects.filter(**{lookup: selected_value})

    data = dict(selected_value=selected_value, results=[], qs=lazy and dumps_qs_query(queryset) or None)
    if lazy:
        if pks:
            for obj in cls.objects.filter(pk__in=pks):
                html = (select_template or select_display) and render_to_string(select_template or 'select_template.html', dict(obj=obj, select_display=select_display)) or str(obj)
                data['results'].append(dict(id=obj.id, text=str(obj), html=html))
    else:
        for obj in queryset:
            html = (select_template or select_display) and render_to_string(select_template or 'select_template.html', dict(obj=obj, select_display=select_display)) or str(obj)
            data['results'].append(dict(id=obj.id, text=str(obj), html=html))
    s = json.dumps(data)

    return HttpResponse(s)