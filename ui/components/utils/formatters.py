# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from djangoplus.ui.components.utils import Timeline, StatisticsTable, QrCode, ProgressBar


def timeline(value, **kwargs):
    return Timeline(kwargs.get('request'),  kwargs.get('verbose_name'), value)


def statistics(value, **kwargs):
    return StatisticsTable(kwargs.get('request'), kwargs.get('verbose_name'), value)


def chart(value, **kwargs):
    return StatisticsTable(kwargs.get('request'), kwargs.get('verbose_name'), value).as_chart()


def pie_chart(value, **kwargs):
    return chart(value, **kwargs).pie()


def donut_chart(value, **kwargs):
    return chart(value, **kwargs).donut()


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


def box_chart(value, **kwargs):
    return chart(value, **kwargs).box()


def qrcode(value, **kwargs):
    return QrCode(value)


def progress(percentual):
    return ProgressBar(percentual)

