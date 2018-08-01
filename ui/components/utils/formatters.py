# -*- coding: utf-8 -*-

from djangoplus.ui.components.utils import Timeline, QrCode, ProgressBar


def timeline(value, **kwargs):
    return Timeline(kwargs.get('request'),  kwargs.get('verbose_name'), value)


def statistics(value, **kwargs):
    value.title = kwargs.get('verbose_name')
    return value.as_table(kwargs.get('request'))


def chart(value, **kwargs):
    value.title = kwargs.get('verbose_name')
    return value.as_chart(kwargs.get('request'))


def pie_chart(value, **kwargs):
    return chart(value, **kwargs).pie()


def donut_chart(value, **kwargs):
    return chart(value, **kwargs).donut()


def box_chart(value, **kwargs):
    return chart(value, **kwargs).box()


def bar_chart(value, **kwargs):
    return chart(value, **kwargs).bar()


def horizontal_bar_chart(value, **kwargs):
    return chart(value, **kwargs).horizontal_bar()


def stack_chart(value, **kwargs):
    return chart(value, **kwargs).stack()


def horizontal_stack_chart(value, **kwargs):
    return chart(value, **kwargs).horizontal_stack()


def line_chart(value, **kwargs):
    return chart(value, **kwargs).line()


def area_chart(value, **kwargs):
    return chart(value, **kwargs).area()


def qrcode(value, **kwargs):
    request = kwargs.get('request', None)
    return QrCode(request, value)


def progress(percentual, **kwargs):
    request = kwargs.get('request', None)
    return ProgressBar(request, percentual)

