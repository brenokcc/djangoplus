# -*- coding: utf-8 -*-


def formatter(name=None):
    def decorate(func):
        func._formatter = name
        return func
    return decorate
