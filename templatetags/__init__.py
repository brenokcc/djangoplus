# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import json
import datetime
from decimal import Decimal
from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from djangoplus.utils import permissions, http
from djangoplus.utils.formatter import format_value, normalyze
from djangoplus.utils.metadata import get_metadata, find_field_by_name, getattr2, is_many_to_many
from uuid import uuid4
from django.template.defaultfilters import slugify
import base64
import cStringIO
register = template.Library()


@register.filter
def tojson(value):
    return json.dumps(value)


@register.filter
def short_username(value):
    return value.split('@')[0]


@register.filter
def displayable(value):
    return value not in [True, False, None, '']


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.simple_tag(name='uuid')
def do_uuid4():
    return uuid4()


@register.simple_tag()
def value_at(col_value, col_index, template_filters):
    import utils
    value = col_value

    # Se há um template filter com o mesmo índice da coluna, então
    # é sinal que este deverá ser o template_filter a ser utilizado.
    if col_index in template_filters:
        template_filter = template_filters[col_index]
        value = utils.apply_filter(value, template_filter)

    # Realizando a formatação padrão.
    value = utils.apply_filter(value, 'format2')
    return value


@register.simple_tag()
def tree_info(obj, queryset):
    if hasattr(obj, 'get_parent_field'):
        parent_field = obj.get_parent_field()
        if parent_field:
            parent = getattr(obj, parent_field.name)
            if not hasattr(queryset, '__pks'):
                queryset.__pks = queryset.values_list('pk', flat=True)
            if parent and parent.pk in queryset.__pks:
                return 'treegrid-{}  treegrid-parent-{}'.format(obj.pk, parent.pk)
            else:
                return 'treegrid-{}'.format(obj.pk)
    else:
        return ''


@register.simple_tag()
def paginator_icons(paginator, obj):
    edit = not paginator.readonly
    delete = not paginator.readonly
    return obj_icons(paginator.request, obj, to=paginator.to, edit=edit, delete=delete)


@register.simple_tag()
def obj_icons(request, obj, to=None, edit=True, delete=True, css='ajax'):
    l = []
    model = obj.__class__
    cls = model.__name__.lower()
    app = get_metadata(model, 'app_label')
    css = to and 'popup' or css
    parent = to and hasattr(obj, to) and getattr(obj, to) or None
    if hasattr(obj, 'get_absolute_url'):
        view_url = obj.get_absolute_url()
    else:
        view_url = '/view/{}/{}/{}/'.format(app, cls, obj.pk)
    url_id = slugify(view_url)
    url_title = 'Visualizar'

    if parent:
        from djangoplus.cache import loader
        can_spy = True
        if type(obj) in loader.actions:
            for category in loader.actions[type(obj)]:
                for action_name in loader.actions[type(obj)][category]:
                    action = loader.actions[type(obj)][category][action_name]
                    if not action['inline']:
                        can_spy = False
                        break
        fieldsets = get_metadata(obj, 'fieldsets')
        if fieldsets:
            for fieldset in fieldsets:
                if '::' in fieldset[0]:
                    can_spy = False
                    break

        l.append('<a id="{}" class="{}" href="{}?parent={}" title="{}"><i class="fa fa-search fa-lg"></i></a>'.format(url_id, 'ajax', view_url, to, url_title))
        if can_spy:
            l.append('<a id="{}" class="{}" href="{}?parent={}" title="{}"><i class="fa fa-eye fa-lg"></i></a>'.format(url_id, 'popup', view_url, to, url_title))
    else:
        l.append('<a id="{}" class="{}" href="{}" title="{}"><i class="fa fa-search fa-lg"></i></a>'.format(url_id, to and 'popup' or 'ajax', view_url, url_title))

    if edit or delete:
        if parent and is_many_to_many(parent.__class__, to):
            if edit and (not hasattr(obj, 'can_edit') or obj.can_edit()):
                delete_url = '/delete/{}/{}/{}/{}/{}/'.format(app, parent.__class__.__name__.lower(), parent.pk, to, obj.pk)
                url_id = slugify(delete_url)
                url_title = 'Remover'
                l.append(' <a id="{}" class="{}" href="{}" title="{}"><i class="fa fa-times fa-lg"></i></a>'.format(url_id, 'ajax', delete_url, url_title))
        else:
            if edit and permissions.has_edit_permission(request, type(obj)) and (not hasattr(obj, 'can_edit') or obj.can_edit()):
                if parent:
                    _app = get_metadata(parent.__class__, 'app_label')
                    _cls = parent.__class__.__name__.lower()
                    _related_field = find_field_by_name(obj.__class__, to).remote_field.get_accessor_name()
                    edit_url = '/add/{}/{}/{}/{}/{}/'.format(_app, _cls, parent.pk, _related_field, obj.pk)
                else:
                    edit_url = '/add/{}/{}/{}/'.format(app, cls, obj.pk)
                url_id = slugify(edit_url)
                url_title = 'Editar'
                l.append(' <a id="{}" class="{}" href="{}" title="{}"><i class="fa fa-edit fa-lg"></i></a>'.format(url_id, css, edit_url, url_title))

            if delete and permissions.has_delete_permission(request, type(obj)) and (not hasattr(obj, 'can_delete') or obj.can_delete()):
                delete_url = '/delete/{}/{}/{}/'.format(app, cls, obj.pk)
                url_id = slugify(delete_url)
                url_title = 'Excluir'
                l.append(' <a id="{}" class="{}" href="{}" title="{}"><i class="fa fa-trash-o fa-lg"></i></a>'.format(url_id, 'popup', delete_url, url_title))

            tree_index_field = hasattr(obj, 'get_tree_index_field') and obj.get_tree_index_field() or None
            if tree_index_field:
                add_url = '/add/{}/{}/{}/{}/'.format(app, cls, obj.pk, cls)
                url_id = slugify(view_url)
                url_title = 'Adicionar'
                l.append(' <a id="{}" class="{}" href="{}" title="{}"><i class="fa fa-plus fa-lg"></i></a>'.format(
                url_id, 'popup', add_url, url_title))

    return mark_safe(''.join(l))


@register.filter
def red_if_negative(obj):
    value = format2(obj)
    if obj < 0:
        return '<span class="text-danger">{}</span>'.format(value)
    return value


@register.filter
def children(obj):
    return getattr(obj, '{}_set'.format(obj.__class__.__name__.lower())).all()


@register.filter
def link(value):
    if value:
        app = get_metadata(value.__class__, 'app_label')
        cls = value.__class__.__name__.lower()

        return mark_safe('<a class="ajax" href="/view/{}/{}/{}/">{}</a>'.format(app, cls, value.pk, value))
    return '-'


@register.filter(name='format')
def format2(value, request=None):
    if value and hasattr(value, 'id') and hasattr(value, '_meta') and hasattr(value, 'fieldsets'):
        app = get_metadata(value.__class__, 'app_label')
        cls = value.__class__.__name__.lower()
        if request and request.user.has_perm('{}.{}'.format(app, cls)):
            return link(value)
    return mark_safe(format_value(value).replace('\n', '<br />'))


@register.filter
def print_format(value):
    return mark_safe(format_value(value).replace('\n', '<br />'))


@register.filter
def ordered_list(value):
    l = ['<ol style="padding-left:13px">']
    for obj in value:
        l.append('<li style="list-style-type:decimal">{}</li>'.format(obj))
    l.append('</ol>')
    return mark_safe(''.join(l))


@register.filter()
def mobile(request):
    return http.mobile(request)


@register.filter()
def align(value):
    position ='left'
    if isinstance(value, bool) or isinstance(value, datetime.date):
        position='center'
    elif isinstance(value, Decimal) or isinstance(value, int):
        position='right'
    elif isinstance(value, tuple):
        return align(value[0])
    return position


@register.filter
def render_paginator(paginator):
    list_template = get_metadata(paginator.qs.model, 'list_template')
    return render_to_string(list_template, {'paginator' : paginator})


@register.filter
def add_actions(paginator, obj):
    paginator.drop_down.add_actions(obj, inline=True, subset_name=paginator.get_current_tab_name() or None)
    return ''


@register.filter
def html(value):
    if value:
        value = unicode(value)
        value = value.replace('\n', '<br>').replace('  ', '&nbsp; ').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        return mark_safe(value)
    else:
        return '-'


@register.filter
def number(value):
    return unicode(value)


@register.filter
def tahoma(value):
    return mark_safe('<font style="font-family: tahoma">{}</font>'.format(html(value)))


@register.filter
def colspan(n):
    return 12/n


@register.filter
def must_hide_fieldset(tuples):
    count = 0
    for fields in tuples:
        count += len(fields)
    return count == 0


register.filter('getattr', getattr2)
register.filter('normalyze', normalyze)


@register.filter
def sorted_items(d):
    items = []
    keys = d.keys()
    keys.sort()
    for key in keys:
        items.append((re.sub('^[0-9\.\- ]+', '', key).strip(), d[key]))
    return items


@register.filter
def photo(user):
    return user and user.photo and '/media/{}'.format(user.photo) or '/static/images/user.png'


@register.filter
def toast(message):
    return mark_safe("<script>$.toast({{ text: '{}', loader: false, position : {{top: 60, right: 30}}, hideAfter: 10000}});</script>".format(message.message))


@register.simple_tag()
def set_request(obj, request):
    obj.request = request
    return ''


@register.filter
def is_image(value):
    if value:
        for ext in ('.png', '.jpg', '.jpeg', '.gif'):
            if unicode(value).lower().endswith(ext):
                return True
    return False


@register.filter
def qrcode64(text):
    import qrcode
    qr = qrcode.QRCode()
    qr.add_data(text)
    image = qr.make_image()
    buffer = cStringIO.StringIO()
    image.save(buffer, format="JPEG")
    img_str = base64.b64encode(buffer.getvalue())
    return mark_safe('<img width="100" src="data:image/jpeg;base64, {}"/>'.format(img_str))