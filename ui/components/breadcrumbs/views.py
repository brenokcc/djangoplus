# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http.response import HttpResponseRedirect


def reset(request, path):
    stack = request.session.get('stack')
    if stack:
        for item in stack[1:]:
            stack.pop()
        request.session.save()
    return HttpResponseRedirect('/{}'.format(path))
