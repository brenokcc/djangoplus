# -*- coding: utf-8 -*-

from . import views
from django.conf.urls import url


urlpatterns = [

    url(r'^list/(?P<app>\w+)/(?P<cls>\w+)/$', views.listt),
    url(r'^list/(?P<app>\w+)/(?P<cls>\w+)/(?P<subset>\w+)/$', views.listt),

    url(r'^add/(?P<app>\w+)/(?P<cls>\w+)/$', views.add),
    url(r'^add/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/$', views.add),
    url(r'^add/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/(?P<related_field_name>\w+)/$', views.add),
    url(r'^add/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/(?P<related_field_name>\w+)/(?P<related_pk>\d+)/$', views.add),

    url(r'^view/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/$', views.view),
    url(r'^view/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/(?P<tab>[-\w]+)/$', views.view),

    url(r'^action/(?P<app>\w+)/(?P<cls>\w+)/(?P<action_name>\w+)/(?P<pk>\d+)/$', views.action),
    url(r'^action/(?P<app>\w+)/(?P<cls>\w+)/(?P<action_name>\w+)/$', views.action),

    url(r'^delete/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/$', views.delete),
    url(r'^delete/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/(?P<related_field_name>\w+)/(?P<related_pk>\d+)/$', views.delete),

    url(r'^log/(?P<app>\w+)/(?P<cls>\w+)/(?P<pk>\d+)/$', views.log),
    url(r'^log/(?P<app>\w+)/(?P<cls>\w+)/$', views.log),

    url(r'^(?P<app>\w+)/(?P<view_name>\w+)/(?P<params>.*)$', views.dispatcher),

]
