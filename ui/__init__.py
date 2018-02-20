# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.template.loader import render_to_string
import random


class Component(object):

    def __init__(self, request=None):
        self.id = self.id = abs(random.randint(0, 900))
        self.request = request
        self.response = None
        self.as_pdf = False

    def render(self, template_name):
        self.as_pdf = self.request and self.request.GET.get('pdf', False) or self.as_pdf
        return render_to_string(template_name, {'self': self})
