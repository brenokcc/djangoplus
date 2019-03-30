# -*- coding: utf-8 -*-
from djangoplus.ui.components.panel import ImagePanel


def imagepanel(images, **kwargs):
    if images:
        return ImagePanel(kwargs['request'], kwargs['verbose_name'], images=images, icon=kwargs['icon'])