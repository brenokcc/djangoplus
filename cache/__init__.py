# -*- coding: utf-8 -*-
from __future__ import unicode_literals
function_views = []
widget_views = []
count = 0


def next_number():
    global count
    if count > 1000:
        count = 0
    count = count + 1
    return count
