# -*- coding: utf-8 -*-
import datetime, json
from django.http.response import HttpResponse
from djangoplus.templatetags import obj_icons
from djangoplus.ui.components.dropdown import ModelDropDown
from django.views.decorators.csrf import csrf_exempt
from djangoplus.utils.serialization import loads_qs_query


@csrf_exempt
def populate(request):
    items = []
    queryset = loads_qs_query(request.POST['queryset'])
    start_field = request.POST['start_field']
    end_field = request.POST['end_field']
    start = datetime.datetime.strptime(request.POST['start'], '%Y-%m-%d')
    end = datetime.datetime.strptime(request.POST['end'], '%Y-%m-%d')
    action_names = request.POST['action_names'].split(',')

    request.session['calendar_default_date'] = (start + datetime.timedelta(days=10)).strftime('%Y-%m-%d')
    request.session.save()

    filters = dict()
    filters['%s__gte' % start_field] = start
    filters['%s__lte' % start_field] = end
    queryset = queryset.filter(**filters)

    for obj in queryset.all():
        title = unicode(obj)
        start = getattr(obj, start_field)
        end = end_field and getattr(obj, end_field) or None
        if end:
            end= end + datetime.timedelta(days=1)
        icons = obj_icons(request, obj, css='popup')
        drop_down = ModelDropDown(request, obj.__class__, action_names=action_names)
        drop_down.add_actions(obj, inline=True)
        html_id = hash(obj)
        html = list()
        html.append(u'<div id="%s">' % html_id)
        html.append(u'<div class="pull-right">%s</div><br/><br/>' % icons)
        html.append(u'<dl>')
        html.append(u'<dt>Início</dt><dd>%s</dd>' % start)
        if end:
            html.append(u'<dt>Fim</dt><dd>%s</dd>' % end)
        html.append(u'</dl>')
        html.append(u'<hr/>')
        html.append(unicode(drop_down))
        html.append(u'</div>')
        html.append(u'<script>initialize("%s");</script>' % html_id)
        item = dict(id=html_id, title=title, start=str(start), end=end and str(end) or None, allDay=False, url='javascript:', html=''.join(html))
        items.append(item)

    return HttpResponse(json.dumps(items))
