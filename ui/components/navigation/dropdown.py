# -*- coding: utf-8 -*-
import copy
from datetime import datetime
from djangoplus.utils import http
from collections import OrderedDict
from djangoplus.ui import RequestComponent
from django.utils.translation import ugettext as _
from djangoplus.utils.metadata import check_condition
from djangoplus.utils import permissions, should_add_action
from djangoplus.utils.metadata import get_metadata, get_can_execute, count_parameters_names


class GroupDropDown(RequestComponent):
    def __init__(self, request, style=None):
        super(GroupDropDown, self).__init__('groupdropdown', request)
        self.actions = OrderedDict()
        self.mobile = http.mobile(self.request)
        self.actions[_('Actions')] = []
        self.style = style

    def add_action(self, label, url, css='popup', icon=None, category=None):
        if category is None:
            category = label
        if self.mobile:
            category = _('Actions')
        if category not in self.actions:
            self.actions[category] = []
        item = dict(label=label, url=url, css=css, icon=icon)
        self.actions[category].append(item)

    def has_items(self):
        for category in self.actions:
            if self.actions[category]:
                return True
        return False


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

            for category in loader.instance_actions[self.model]:
                for view_name in loader.instance_actions[self.model][category]:
                    form_action = loader.instance_actions[self.model][category][view_name]
                    if not self.has_inline_action:
                        self.has_inline_action = form_action.get('inline') or form_action.get('subsets')

            if not self.has_inline_action:
                self.has_inline_action = self.model in loader.add_inline_actions

        super(ModelDropDown, self).__init__(request)
        # adding the actions defined in the model class
        for category in loader.instance_actions[self.model]:
            if category not in self.actions:
                self.actions[category] = []

    def add_action(self, label, url, css='popup', icon=None, category=None):
        if category is None:
            category = _('Actions')
        if category not in self.actions:
            self.actions[category] = []
        if self.obj:
            if '{}' in url:
                url = url.format(self.obj.pk)
            else:
                url = '{}{}/'.format(url, self.obj.pk)
        super(ModelDropDown, self).add_action(label, url, css, icon, category)

    def add_actions(self, obj, inline=False, fieldset=None, subset_name=None, category=None, action_names=None):
        from djangoplus.cache import loader
        obj.request = self.request
        if not self.actions_cache:
            self.actions_cache = self.actions
        if not action_names:
            action_names = []
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

        for action_category in loader.instance_actions[self.model]:

            for view_name in loader.instance_actions[self.model][action_category]:
                action = loader.instance_actions[self.model][action_category][view_name]
                action_function = action.get('function')
                action_title = action['title']
                action_can_execute = get_can_execute(action)
                action_condition = action['condition']
                action_style = action['style']
                action_input = action['input']
                action_inline = action['inline']
                action_subsets = action['subsets']
                action_icon = action['icon']
                action_display = action['display']

                action_name = action_function.__name__
                is_action_view = not hasattr(self.model, action_name)

                if action_name and action_style == 'popup' and not is_action_view:
                    func = getattr(self.model, action_name)
                    action_style = (count_parameters_names(func) > 1 or action_input or action_display) and \
                                   action_style or 'ajax'

                # it is a dropdown in a model panel
                if fieldset is not None:
                    if fieldset:
                        if action_name not in loader.fieldset_actions[self.model][fieldset]:
                            continue
                    else:
                        # if the action was included in any fieldset it can not be displayed in page's action panel
                        add_action = True
                        for title, action_names in list(loader.fieldset_actions[self.model].items()):
                            if action_name in action_names:
                                add_action = False
                                break
                        if not add_action:
                            continue
                else:
                    # it is a dropdown in a paginator
                    if action_names:
                        # it is a relation paginator
                        if view_name not in action_names:
                            continue
                    else:
                        # it is a list view paginator
                        add_action = view_name in action_names or should_add_action(action_inline, action_subsets, subset_name)
                        # #print(action_title, action_inline, action_subsets, subset_name, add_action, 666)
                        if not add_action:
                            continue

                lookups = self.request.user.get_permission_mapping(self.model, obj).get(action_name)
                if lookups:
                    forbidden = True
                    for key, value in lookups:
                        if self.model.objects.filter(pk=obj.pk, **{'{}__in'.format(key): value}).exists():
                            forbidden = False
                            break
                    if forbidden:
                        continue

                if not permissions.check_group_or_permission(self.request, action_can_execute):
                    continue

                if not check_condition(self.request.user, action_condition, obj):
                    continue

                if is_action_view:
                    action_url = '/{}/{}/'.format(get_metadata(self.model, 'app_label'), action_name)
                else:
                    action_url = '/action/{}/{}/{}/'.format(get_metadata(self.model, 'app_label'), self.model.__name__.lower(), view_name)

                self.add_action(action_title, action_url, action_style, action_icon, category or action_category)
