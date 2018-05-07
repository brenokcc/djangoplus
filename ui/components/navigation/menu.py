# -*- coding: utf-8 -*-
from django.conf import settings
from djangoplus.ui import RequestComponent
from djangoplus.utils import permissions
from django.utils.safestring import mark_safe


class Menu(RequestComponent):
    def __init__(self, request, app_settings=None):
        super(Menu, self).__init__('menu', request)
        self.subitems = dict()
        self.settings = app_settings
        self._load()

    def _add(self, description, url, icon=None, style='ajax'):
        url = '/breadcrumbs/reset{}'.format(url)
        levels = description.split('::')
        for i, level in enumerate(levels):
            levels[i] = level.strip()

        if levels[0] not in self.subitems:
            self.subitems[levels[0]] = dict(urls=[], subitems=dict(), icon=None)
        if not self.subitems[levels[0]]['icon']:
            self.subitems[levels[0]]['icon'] = icon

        if len(levels) == 1:
            self.subitems[levels[0]]['urls'].append((url, style))
        else:
            if levels[1] not in self.subitems[levels[0]]['subitems']:
                self.subitems[levels[0]]['subitems'][levels[1]] = dict(urls=[], subitems=dict())
            if len(levels) == 2:
                self.subitems[levels[0]]['subitems'][levels[1]]['urls'].append((url, style))
            else:
                if levels[2] not in self.subitems[levels[0]]['subitems'][levels[1]]['subitems']:
                    self.subitems[levels[0]]['subitems'][levels[1]]['subitems'][levels[2]] = dict(urls=[], subitems=dict())
                if len(levels) == 3:
                    self.subitems[levels[0]]['subitems'][levels[1]]['subitems'][levels[2]]['urls'].append((url, style))
                else:
                    if levels[3] not in self.subitems[levels[0]]['subitems'][levels[1]]['subitems'][levels[2]]['subitems']:
                        self.subitems[levels[0]]['subitems'][levels[1]]['subitems'][levels[2]]['subitems'][levels[3]] = dict(urls=[])
                    self.subitems[levels[0]]['subitems'][levels[1]]['subitems'][levels[2]]['subitems'][levels[3]]['urls'].append((url, style))

    def _load(self):
        if settings.DEBUG or 'side_menu' not in self.request.session:
            from djangoplus.cache import loader
            for item in loader.views:
                if item['menu']:
                    can_view = permissions.check_group_or_permission(self.request, item['can_view'])
                    if can_view and 'groups' in item:
                        can_view = permissions.check_group_or_permission(self.request, item['groups'])
                    if can_view:
                        self._add(item['menu'], item['url'], item['icon'], item.get('style', 'ajax'))

            for cls, itens in list(loader.subsets.items()):
                for item in itens:
                    if permissions.check_group_or_permission(self.request, item['can_view']):
                        if False:  # TODO False
                            self._add(item['menu'], item['url'], item['icon'], 'ajax')

            self.request.session['side_menu'] = super(Menu, self).__str__()
            self.request.session['side_menu_size'] = len(list(self.subitems.keys()))
            self.request.session.save()

    def __str__(self):
        return mark_safe(self.request.session['side_menu'])