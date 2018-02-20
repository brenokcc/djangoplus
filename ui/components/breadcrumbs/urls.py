# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf.urls import url
from djangoplus.ui.components.breadcrumbs import views

urlpatterns = [
    url(r'^breadcrumbs/reset/(?P<path>.*)$', views.reset),
]