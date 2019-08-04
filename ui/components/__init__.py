# -*- coding: utf-8 -*-
import uuid
from django.utils.text import slugify
from djangoplus.utils.http import ReportResponse
from django.utils.deprecation import MiddlewareMixin
from django.template.loader import render_to_string
from djangoplus.utils import http
from jinja2.utils import Markup


class Component(object):

    template_name = None
    formatter_name = None

    class Media:
        css = {'all': ()}
        js = ()

    def __init__(self, uid=None, request=None, title=None):
        self.id = slugify(str(uid or uuid.uuid1().hex))
        self.as_pdf = False
        self.title = title
        self.request = request
        self.response = None
        self.mobile = http.mobile(request)

        if self.request:
            if 'pdf' in self.request.GET:
                self.as_pdf = True

    def __str__(self):
        template_name = self.template_name or '{}.html'.format(self.__class__.__name__.lower())
        return self.render(template_name)

    def process_request(self):
        if self.request:
            if self.request.GET.get('pdf') == self.id:
                raise ComponentHasResponseException(
                    ReportResponse(self.title, self.request, [self])
                )

    def render(self, template_name):
        medias = []
        media_cls = getattr(self, 'Media')
        if hasattr(media_cls, 'js'):
            for script in media_cls.js:
                medias.append('<script src="{}"></script>'.format(script))
        if hasattr(media_cls, 'css'):
            for css_media, urls in media_cls.css.items():
                for url in urls:
                    js = '$("<link/>", {{rel: "stylesheet",type: "text/css",href: "{}"}}).appendTo("head");'
                    js = js.format(url)
                    medias.append('<script>{}</script>'.format(js))
        html = render_to_string(template_name, {'component': self})
        return Markup('{}\n{}'.format(''.join(medias), html))

    @classmethod
    def subclasses(cls):
        clss = []

        def find_subclasses(superclass):
            for subclasse in superclass.__subclasses__():
                find_subclasses(subclasse)
            clss.append(superclass)
        find_subclasses(cls)

        return clss


class ComponentHasResponseException(Exception):

    def __init__(self, response):
        self.response = response
        super(ComponentHasResponseException, self).__init__()


class ComponenteResponseMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):
        if type(exception) == ComponentHasResponseException:
            return exception.response
        return None
