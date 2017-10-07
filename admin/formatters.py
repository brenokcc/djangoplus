# -*- coding: utf-8 -*-


def log_tags(value):
    l = []
    for item in value:
        if len(item) == 3:
            l.append(u'<span class="tag"><span>%s:&nbsp;&nbsp;</span>%s <i class="fa fa-arrow-right" aria-hidden="true"></i> %s</span>' % (item[0], item[1], item[2]))
        else:
            l.append(u'<span class="tag"><span>%s:&nbsp;&nbsp;</span>%s</span>' % (item[0], item[1]))
    return u''.join(l)


def progress(percentual):
    percentual = int(percentual)
    return '<div class="progress" data-toggle="tooltip" data-placement="top" title="" data-original-title="%s%%"><div class="progress-bar" style="width: %s%%;"></div></div>'%(percentual, percentual)

