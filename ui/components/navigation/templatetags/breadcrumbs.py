# -*- coding: utf-8 -*-

from djangoplus.ui.components.navigation.breadcrumbs import Breadcrumbs
from django_jinja import library as register


@register.global_function
def breadcrumbs(request, view_title):
    return str(Breadcrumbs(request, view_title))
