# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf.urls import url
from djangoplus.ui.components.calendar import views

urlpatterns = [
    url(r'^calendar/populate/$', views.populate),
]