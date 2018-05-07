# -*- coding: utf-8 -*-
import uuid
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from djangoplus.utils.http import ReportResponse
from django.utils.deprecation import MiddlewareMixin
from django.template.loader import render_to_string


class Component(object):

    class Media:
        css = {'all': ()}
        js = ()

    def __init__(self, uid=None):
        self.id = slugify(str(uid or uuid.uuid1().hex))
        self.as_pdf = False

    def __str__(self):
        return self.render('{}.html'.format(self.__class__.__name__.lower()))

    def render(self, template_name):
        medias = []
        media_cls = getattr(self, 'Media')
        if hasattr(media_cls, 'js'):
            for script in media_cls.js:
                medias.append('<script src="{}"></script>'.format(script))
        if hasattr(media_cls, 'css'):
            for css_media, urls in media_cls.css.items():
                for url in urls:
                    script = '$("<link/>", {{rel: "stylesheet",type: "text/css",href: "{}"}}).appendTo("head");'.format(url)
                    medias.append('<script>{}</script>'.format(script))
        html = render_to_string(template_name, {'self': self})
        return mark_safe('{}\n{}'.format(''.join(medias), html))


class RequestComponent(Component):

    def __init__(self, uid, request):
        self.title = None
        self.request = request
        self.response = None

        super(RequestComponent, self).__init__(uid)

        if self.request:
            if 'pdf' in self.request.GET:
                self.as_pdf = True

    def process_request(self):
        if self.request:
            if self.request.GET.get('pdf') == self.id:
                raise ComponentHasResponseException(ReportResponse(self.title, self.request, [self]))


class ComponentHasResponseException(Exception):

    def __init__(self, response):
        self.response = response
        super(ComponentHasResponseException, self).__init__()


class ComponenteResponseMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):
        if type(exception) == ComponentHasResponseException:
            return exception.response
        return None
