# -*- coding: utf-8 -*-
from djangoplus.test import cache


def breakpoint(function):
    def decorate(self):
        cache.BREAKPOINT = function.func_name
        if cache.CONTINUE in [None, function.func_name]:
            if cache.CONTINUE == function.func_name and cache.USERNAME and cache.PASSWORD:
                cache.IGNORE_LOGIN = False
                self.login(cache.USERNAME, cache.PASSWORD)
            function(self)
    return decorate
