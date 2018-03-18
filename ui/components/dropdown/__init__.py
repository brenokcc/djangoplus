# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import copy
from collections import OrderedDict
from datetime import datetime
from djangoplus.ui import Component
from djangoplus.utils import permissions
from djangoplus.utils.metadata import get_metadata
from djangoplus.utils.metadata import check_condition
from djangoplus.utils import http


class GroupDropDown(Component):
    def __init__(self, request):
        super(GroupDropDown, self).__init__(request)
        self.actions = OrderedDict()
        self.mobile = http.mobile(self.request)
        self.actions['Ações'] = []

    def add_action(self, label, url, css='popup', icon=None, category='Ações'):
        if self.mobile:
            category = 'Ações'
        if category not in self.actions:
            self.actions[category] = []
        item = dict(label=label, url=url, css=css, icon=icon)
        self.actions[category].append(item)

    def has_items(self):
        for category in self.actions:
            if self.actions[category]:
                return True
        return False

    def __unicode__(self):
        return self.render('dropdown.html')


class ModelDropDown(GroupDropDown):
    def __init__(self, request, model, action_names=()):
        from djangoplus.cache import loader
        self.model = model
        self.action_names = action_names
        self.actions_cache = None
        self.hash = abs(datetime.now().__hash__())
        self.obj = None

        self.has_inline_action = False
        if action_names and len(action_names) > 0:
            self.has_inline_action = True
        else:

            for category in loader.actions[self.model]:
                for view_name in loader.actions[self.model][category]:
                    form_action = loader.actions[self.model][category][view_name]
                    if not self.has_inline_action:
                        self.has_inline_action = form_action.get('inline')

            if not self.has_inline_action:
                self.has_inline_action = self.model in loader.add_inline_actions

        super(ModelDropDown, self).__init__(request)
        # adding the actions defined in the model class
        for category in loader.actions[self.model]:
            if category not in self.actions:
                self.actions[category] = []

    def add_action(self, label, url, css='popup', icon=None, category='Ações'):
        if category not in self.actions:
            self.actions[category] = []
        if self.obj:
            if '{}' in url:
                url = url.format(self.obj.pk)
            else:
                url = '{}{}/'.format(url, self.obj.pk)
        item = dict(label=label, url=url, css=css, icon=icon)
        self.actions[category].append(item)

    def add_actions(self, obj, inline=False, fieldset_title=None, subset_name=None):
        from djangoplus.cache import loader
        obj.request = self.request
        if not self.actions_cache:
            self.actions_cache = self.actions

        self.hash = abs(datetime.now().__hash__())
        self.actions = copy.deepcopy(self.actions_cache)
        self.obj = obj

        if inline:
            if self.model in loader.add_inline_actions:
                for add_inline_action in loader.add_inline_actions[self.model]:
                    if add_inline_action['subset'] is True or add_inline_action['subset'] == subset_name:
                        if permissions.check_group_or_permission(self.request, add_inline_action['can_execute']):
                            self.add_action(
                                add_inline_action['title'], add_inline_action['url'], 'popup', 'fa fa-plus'
                            )
        else:
            if get_metadata(type(obj), 'pdf'):
                self.add_action('Imprimir', '?pdf=', 'ajax', 'fa fa-print')

        for category in loader.actions[self.model]:
            for view_name in loader.actions[self.model][category]:
                action = loader.actions[self.model][category][view_name]
                action_function = action.get('function')
                action_title = action['title']
                action_can_execute = action['can_execute']
                action_condition = action['condition']
                action_css = action['css']
                action_input = action['input']
                action_inline = action['inline']
                action_icon = action['icon']

                action_name = action_function.func_name
                is_action_view = not hasattr(self.model, action_name)

                if action_name and action_css == 'popup' and not is_action_view:
                    func = getattr(self.model, action_name)
                    action_css = (func.func_code.co_argcount > 1 or action_input) and action_css or 'ajax'

                # it is a dropdown in a model panel
                if fieldset_title is not None:
                    if fieldset_title:
                        if action_name not in loader.fieldset_actions[self.model][fieldset_title]:
                            continue
                    else:
                        # if the action was included in any fieldset it can not be displayed in page's action panel
                        add_action = True
                        for fieldset_title2, action_names in loader.fieldset_actions[self.model].items():
                            if action_name in action_names:
                                add_action = False
                                break
                        if not add_action:
                            continue
                else:
                    # it is a dropdown in a paginator
                    if action_inline is not True and (subset_name not in loader.subset_actions[self.model] or action_name not in loader.subset_actions[self.model][subset_name]):
                        continue

                if not permissions.check_group_or_permission(self.request, action_can_execute):
                    continue

                if not check_condition(action_condition, obj):
                    continue

                if is_action_view:
                    action_url = '/{}/{}/'.format(get_metadata(self.model, 'app_label'), action_name)
                else:
                    action_url = '/action/{}/{}/{}/'.format(get_metadata(self.model, 'app_label'), self.model.__name__.lower(), view_name)
                self.add_action(action_title, action_url, action_css, action_icon, category)
