# -*- coding: utf-8 -*-

from django import template
from djangoplus.ui.components.navigation.breadcrumbs import Breadcrumbs

register = template.Library()


@register.simple_tag()
def breadcrumbs(request, view_title):
    return str(Breadcrumbs(request, view_title))
