# -*- coding: utf-8 -*-

from django.conf.urls import url
from djangoplus.ui.components.navigation import views

urlpatterns = [
    url(r'^breadcrumbs/reset/(?P<path>.*)$', views.reset),
]