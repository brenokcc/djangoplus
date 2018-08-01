# -*- coding: utf-8 -*-
import re
import json
import locale
import qrcode
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from djangoplus.utils import http
from djangoplus.utils.formatter import format_value, normalyze
from djangoplus.utils.metadata import get_metadata, getattr2
from uuid import uuid4
import base64
import tempfile
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


@register.filter
def full_date_format(value):
    locale.setlocale(locale.LC_ALL, "pt_BR")
    return value.strftime('%d de %B de %Y')


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


@register.simple_tag()
def value_at(col_value, col_index, template_filters):
    from . import utils
    value = col_value

    # Se há um template filter com o mesmo índice da coluna, então
    # é sinal que este deverá ser o template_filter a ser utilizado.
    if col_index in template_filters:
        template_filter = template_filters[col_index]
        value = utils.apply_filter(value, template_filter)

    # Realizando a formatação padrão.
    value = utils.apply_filter(value, 'format2')
    return value


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


@register.filter()
def mobile(request):
    return http.mobile(request)





@register.filter
def html(value):
    if value:
        value = str(value)
        value = value.replace('\n', '<br>').replace('  ', '&nbsp; ').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        return mark_safe(value)
    else:
        return '-'


@register.filter
def number(value):
    return str(value)


@register.filter
def tahoma(value):
    return mark_safe('<font style="font-family: tahoma">{}</font>'.format(html(value)))


@register.filter
def colspan(n):
    return int(12/n)


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
    keys = list(d.keys())
    keys.sort()
    for key in keys:
        items.append((re.sub('^[0-9\.\- ]+', '', key).strip(), d[key]))
    return items


@register.filter
def photo(user):
    if user and user.is_authenticated:
        if user.photo and 'static' not in user.photo.name:
            return '/media/{}'.format(user.photo)
    return '/static/images/user.png'


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
            if str(value).lower().endswith(ext):
                return True
    return False


@register.filter
def image(value, attrs="width='100px'", zoom=False):
    return mark_safe('<img class="{}" {} src="{}">'.format(zoom and 'materialboxed' or '', attrs, image_url(value)))


@register.filter
def zoom_image(value, attrs="width='100px'"):
    return image(value, attrs=attrs, zoom=True)


@register.filter
def image_url(value):
    value = str(value)
    return '/static/' in value and value or '/media/{}'.format(value)


@register.filter
def qrcode64(text):
    qr = qrcode.QRCode()
    qr.add_data(text)
    image = qr.make_image()
    file_path = tempfile.mktemp()
    buffer = open(file_path, 'wb')
    image.save(buffer, format="JPEG")
    img_str = base64.b64encode(open(file_path, 'rb').read()).decode('utf-8')
    return mark_safe('<img width="100" src="data:image/jpeg;base64, {}"/>'.format(img_str))


@register.simple_tag()
def captcha(form):
    return form.captcha and mark_safe('''
        <div align="center">
            <script src="https://www.google.com/recaptcha/api.js?hl={}"></script>
            <div style="width: 100%" class="g-recaptcha" data-sitekey="{}"></div>
        </div>
        <hr/>
    '''.format(settings.LANGUAGE_CODE, settings.CAPTCHA_KEY)) or ''
