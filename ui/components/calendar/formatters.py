# -*- coding: utf-8 -*-

from djangoplus.ui.components.calendar import AnnualCalendar


def annual_calendar(value, **kwargs):
    c = AnnualCalendar(kwargs['verbose_name'])
    if value:
        for item in value:
            c.add(*item)
    return c


def annual_compact_calendar(value, **kwargs):
    c = AnnualCalendar(kwargs['verbose_name'], True)
    if value:
        for item in value:
            c.add(*item)
    return c

