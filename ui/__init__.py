# -*- coding: utf-8 -*-
from djangoplus.utils.http import ReportResponse
from django.utils.deprecation import MiddlewareMixin
from django.template.loader import render_to_string
import random


class Component(object):

    def __init__(self, request=None):
        self.id = self.id = str(abs(random.randint(0, 900)))
        self.title = None
        self.request = request
        self.response = None
        self.as_pdf = False

    def render(self, template_name):
        if self.request:
            if 'pdf' in self.request.GET:
                self.as_pdf = True
        return render_to_string(template_name, {'self': self})

    def check_http_response(self):
        if self.request and self.request.GET.get('pdf') == self.id:
            response = ReportResponse(self.title, self.request, [self])
            raise ComponentHasResponseException(response)


class ComponentHasResponseException(Exception):

    def __init__(self, response):
        self.response = response
        super(ComponentHasResponseException, self).__init__()


class ComponenteResponseMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):
        if type(exception) == ComponentHasResponseException:
            return exception.response
        return None
