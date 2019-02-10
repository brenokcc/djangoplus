# -*- coding: utf-8 -*-

from django.conf import settings
from djangoplus.docs.views import doc
from django.views.static import serve
from djangoplus.core.views import cloud
from django.conf.urls import include, url
from djangoplus.docs.views import homologate

urlpatterns = [

    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    url(r'^cloud/(?P<path>.*)$', cloud, {'document_root': settings.MEDIA_ROOT}),

    url(r'^doc/$', doc),
    url(r'^homologate/$', homologate),

    url(r'', include('djangoplus.ui.components.calendar.urls')),
    url(r'', include('djangoplus.ui.components.navigation.urls')),
    url(r'', include('djangoplus.ui.components.select.urls')),

    url(r'', include('djangoplus.core.urls')),

]
