# -*- coding: utf-8 -*-
from djangoplus.ui import RequestComponent
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse


class Breadcrumbs(RequestComponent):
    """Used in the dashboard to show the sequence of pages the user has visited"""
    def __init__(self, request, view_title):
        super(Breadcrumbs, self).__init__('breadcrumbs', request)
        self.referrer = None
        if view_title:
            path = request.get_full_path()
            is_popup = 'popup=1' in path
            is_csv = 'export=csv' in path
            is_static = path.startswith('/static/')
            is_media = path.startswith('/media/')

            if not is_popup and not is_csv and not is_static and not is_media:
                if 'stack' not in request.session:
                    request.session['stack'] = []
                stack = request.session['stack']

                count = 0
                index = len(stack)
                while index:
                    index -= 1
                    title, url = stack[index]
                    if view_title == title:
                        count = len(stack) - index
                        break

                while count:
                    stack.pop()
                    count -= 1

                if stack:
                    title, url = stack[-1]
                    request.REFERRER = url
                else:
                    request.REFERRER = path

                stack.append((view_title, path))

                request.session.save()
                self.referrer = len(stack) > 1 and stack[-2][1]


def httprr(request, url, message='', error=False):
    if message:
        if error:
            messages.error(request, message, extra_tags='danger')
        else:
            messages.success(request, message, extra_tags='success')

    if 'popup' in request.GET:
        return HttpResponse(url)

    if url in ('.', '..'):
        back = abs(url == '..' and -1 or 0)
        stack = request.session.get('stack', [])
        if len(stack) >= back:
            while back:
                stack.pop()
                back -= 1
            request.session.save()
            if stack:
                title, url = stack[-1]
        else:
            url = request.get_full_path()
    if request.is_ajax():
        return HttpResponse(url)
    else:
        return HttpResponseRedirect(url)

