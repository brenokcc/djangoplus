# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def log_tags(value):
    l = []
    for item in value:
        if len(item) == 3:
            l.append('<span class="tag"><span>{}:&nbsp;&nbsp;</span>{} <i class="fa fa-arrow-right" aria-hidden="true"></i> {}</span>'.format(item[0], item[1], item[2]))
        else:
            l.append('<span class="tag"><span>{}:&nbsp;&nbsp;</span>{}</span>'.format(item[0], item[1]))
    return ''.join(l)


def progress(percentual):
    percentual = int(percentual)
    return '<div class="progress" data-toggle="tooltip" data-placement="top" title="" data-original-title="{}%"><div class="progress-bar" style="width: {}%;"></div></div>'.format(percentual, percentual)

