# -*- coding: utf-8 -*-

from django.conf.urls import url
from djangoplus.ui.components.calendar import views

urlpatterns = [
    url(r'^calendar/populate/$', views.populate),
]