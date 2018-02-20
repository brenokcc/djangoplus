# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django import template
from djangoplus.ui.components.breadcrumbs import Breadcrumbs

register = template.Library()


@register.simple_tag()
def breadcrumbs(request, view_title):
    return unicode(Breadcrumbs(request, view_title))
