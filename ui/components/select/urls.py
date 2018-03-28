# -*- coding: utf-8 -*-

from django.conf.urls import url
from djangoplus.ui.components.select import views

urlpatterns = [
    url(r'^autocomplete/(?P<app_name>\w+)/(?P<class_name>\w+)/$', views.autocomplete), url(
        r'^reload_options/(?P<app_name>\w+)/(?P<class_name>\w+)/(?P<current_value>\w+)/(?P<lookup>\w+)/(?P<selected_value>\w+)/(?P<lazy>\w+)/$', views.reload_options),
]