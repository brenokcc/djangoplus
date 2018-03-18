# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from decimal import Decimal

from djangoplus.ui import Component
from django.utils.text import slugify
from djangoplus.ui.components.forms import ModelForm, ValidationError
from djangoplus.utils import permissions
from djangoplus.ui.components.paginator import Paginator
from djangoplus.ui.components.dropdown import ModelDropDown, GroupDropDown
from django.template.loader import render_to_string
from djangoplus.utils.metadata import get_metadata, list_related_objects,\
    find_field_by_name, get_fiendly_name, check_condition, is_one_to_one, is_one_to_many, is_many_to_many, \
    is_one_to_many_reverse, is_many_to_one, should_filter_or_display


class Panel(Component):

    def __init__(self, request, title=None, text=None):
        super(Panel, self).__init__(request)
        self.title = title
        self.text = text
        self.labels = []
        self.icon = None

    def add_label(self, description, css='label-info'):
        label = dict(description=description, css=css)
        self.labels.append(label)

    def set_icon(self, name, css='text-info', align='right'):
        self.icon = dict(name=name, css=css, align=align)

    def __unicode__(self):
        return self.render('panel.html')


class ModelPanel(Component):
    def __init__(self, request, obj, current_tab=None, parent=None, fieldsets=None, complete=True):

        super(ModelPanel, self).__init__(request=request)

        self.obj = obj
        self.request = request
        self.title = unicode(obj)
        self.tabs = []
        self.current_tab = current_tab
        self.message = None
        self.complete = complete
        self.drop_down = None
        fieldsets = fieldsets or get_metadata(type(obj), 'view_fieldsets', [])
        if not fieldsets:
            fields = []
            for field in get_metadata(type(obj), 'fields')[1:]:
                fields.append(field.name)

            for field in get_metadata(type(obj), 'local_many_to_many'):
                fields.append(field.name)

            fieldsets = (('Dados Gerais', dict(fields=fields)),)

        if self.complete:
            self.drop_down = ModelDropDown(self.request, type(self.obj))
            self.drop_down.add_actions(self.obj, fieldset_title='')
        else:
            self.drop_down = GroupDropDown(self.request)

        self.fieldsets_with_tab_name = []
        self.fieldsets_without_tab_name = []

        model = type(self.obj)
        obj.as_pdf = self.as_pdf

        for fieldset in fieldsets:
            title, info = fieldset
            tab_name = None

            drop_down = ModelDropDown(self.request, model)
            fieldset_actions = info.get('actions', [])

            if fieldset_actions:
                drop_down.add_actions(self.obj, fieldset_title=title)

            if 'condition' in fieldset[1]:
                condition = fieldset[1]['condition']
                self.obj.request = self.request
                if not check_condition(condition, self.obj):
                    continue

            if '::' in title:
                tab_name, title = title.split('::')
                url = '/view/{}/{}/{}/{}/'.format(get_metadata(model, 'app_label'), model.__name__.lower(), self.obj.pk, slugify(tab_name))
                tab = (tab_name, url)
                if not self.tabs and not self.current_tab:
                    self.current_tab = slugify(tab_name)
                if tab not in self.tabs:
                    self.tabs.append(tab)

            if not tab_name or slugify(tab_name) == self.current_tab or self.as_pdf:

                fieldset_dict = dict(title=title or 'Dados Gerais', tab_name=tab_name, fields=[], paginators=[], drop_down=drop_down, image=None)
                relations = list(fieldset[1].get('relations', []))
                inlines = list(fieldset[1].get('inlines', []))

                if tab_name or self.as_pdf:
                    self.fieldsets_with_tab_name.append(fieldset_dict)
                else:
                    self.fieldsets_without_tab_name.append(fieldset_dict)

                if 'can_view' in fieldset[1]:
                    can_view = fieldset[1]['can_view']
                    if not permissions.check_group_or_permission(self.request, can_view):
                        continue

                if 'image' in fieldset[1]:
                    fieldset_dict['image'] = fieldset[1]['image']

                if 'fields' in fieldset[1]:
                    for name_or_tuple in fieldset[1]['fields']:

                        if not type(name_or_tuple) == tuple:
                            name_or_tuple = (name_or_tuple,)
                        attr_names = []

                        for attr_name in name_or_tuple:
                            if attr_name != parent:
                                attr = getattr(model, attr_name)
                                field = None
                                if hasattr(attr, 'field_name'):
                                    field = getattr(model, '_meta').get_field(attr.field_name)
                                elif hasattr(attr, 'field'):
                                    field = attr.field
                                if not field or not hasattr(field, 'display') or field.display:
                                    verbose_name, lookup, sortable, to = get_fiendly_name(model, attr_name, as_tuple=True)
                                    if to and not should_filter_or_display(self.request, model, to):
                                        continue
                                    attr_names.append(dict(verbose_name=verbose_name, name=attr_name))
                        if attr_names:
                            fieldset_dict['fields'].append(attr_names)

                if self.complete:

                    for relation_name in relations + inlines:
                        if relation_name in [field.name for field in get_metadata(model, 'get_fields')]:
                            relation_field = find_field_by_name(model, relation_name)
                            relation = getattr(self.obj, relation_name)
                            if is_one_to_one(model, relation_name) or is_many_to_one(model, relation_name):
                                if relation:
                                    fieldset_title = relation_field.verbose_name
                                    panel_fieldsets = get_metadata(type(relation), 'view_fieldsets', [])
                                    panel_fieldsets = ((fieldset_title, panel_fieldsets[0][1]), )
                                    panel = ModelPanel(request, relation, fieldsets=panel_fieldsets, complete=False)

                                    if is_one_to_one(model, relation_name):
                                        app_label = get_metadata(model, 'app_label')
                                        model_name = model.__name__.lower()
                                        related_model_name = type(relation).__name__.lower()
                                        add_url = '/add/{}/{}/{}/{}'.format(app_label, model_name, self.obj.pk, relation_name)
                                        delete_url = None
                                        if relation.pk:
                                            add_url = '{}/{}/'.format(add_url, relation.pk)
                                            app_label = get_metadata(type(relation), 'app_label')
                                            delete_url = '/delete/{}/{}/{}/'.format(app_label, related_model_name, relation.pk)
                                        if permissions.has_add_permission(self.request, model) or permissions.has_edit_permission(self.request, model):
                                            if delete_url:
                                                panel.drop_down.add_action('Excluir {}'.format(relation_field.verbose_name),
                                                                           delete_url, 'popup', 'fa-close', None)
                                            panel.drop_down.add_action('Atualizar {}'.format(relation_field.verbose_name),
                                                                       add_url, 'popup', 'fa-edit')

                                else:
                                    panel = Panel(request, relation_field.verbose_name, text='')
                                fieldset_dict['paginators'].append(panel)
                            else:
                                fieldset_title = len(relations) > 1 and title or relation_field.verbose_name

                                if is_one_to_many(model, relation_name) or is_many_to_many(model, relation_name):
                                    to = model.__name__.lower()
                                else:
                                    to = relation_name

                                related_paginator = Paginator(self.request, relation.all(), title=fieldset_title, to=to, list_subsets=[])

                                if not is_one_to_many(model, relation_name):
                                    add_url = '/add/{}/{}/{}/{}/'.format(get_metadata(model, 'app_label'), model.__name__.lower(), self.obj.pk, relation_name)
                                    if permissions.has_add_permission(self.request, model) or permissions.has_relate_permission(self.request, model):
                                        related_paginator.add_action('Adicionar {}'.format(unicode(get_metadata(relation.model, 'verbose_name'))), add_url, 'popup', 'fa-plus')
                                fieldset_dict['paginators'].append(related_paginator)
                        else:
                            is_object_set = False
                            for related_object in list_related_objects(model):
                                if hasattr(related_object, 'get_accessor_name') and relation_name == related_object.get_accessor_name():
                                    is_object_set = True
                                    break
                            relation = getattr(self.obj, relation_name)
                            if hasattr(relation, 'all'):
                                qs = relation.all()
                            elif hasattr(relation, '__call__'):
                                qs = relation()
                            else:
                                qs = relation
                            to = is_object_set and related_object.field.name or None

                            fieldset_title = len(relations) > 1 and get_metadata(qs.model, 'verbose_name_plural') or title

                            if hasattr(relation, '_metadata'):
                                fieldset_title = relation._metadata['{}:verbose_name'.format(relation_name)]

                            exclude = [is_object_set and related_object.field.name or '']

                            related_paginator = Paginator(self.request, qs, fieldset_title, exclude=exclude, list_subsets=[], to=to, readonly=not is_object_set)
                            if is_object_set and (permissions.has_add_permission(self.request, qs.model) or permissions.has_relate_permission(self.request, qs.model)):
                                instance = qs.model()
                                setattr(instance, related_object.field.name, self.obj)
                                if permissions.can_add(self.request, instance):
                                    if relation_name in inlines:
                                        form_name = get_metadata(qs.model, 'add_form')
                                        if form_name:
                                            fromlist = get_metadata(qs.model, 'app_label')
                                            forms_module = __import__('{}.forms'.format(fromlist), fromlist=list(map(str, [fromlist])))
                                            Form = getattr(forms_module, form_name)
                                        else:
                                            class Form(ModelForm):
                                                class Meta:
                                                    model = qs.model
                                                    fields = get_metadata(qs.model, 'form_fields', '__all__')
                                                    exclude = get_metadata(qs.model, 'exclude_fields', ())
                                                    submit_label = 'Adicionar'
                                                    title = 'Adicionar {}'.format(get_metadata(qs.model, 'verbose_name'))
                                        form = Form(self.request, instance=instance, inline=True)
                                        if related_object.field.name in form.fields:
                                            del(form.fields[related_object.field.name])
                                        related_paginator.form = form
                                        if form.is_valid():
                                            try:
                                                form.save()
                                                self.message = 'Ação realizada com sucesso'
                                            except ValidationError, e:
                                                form.add_error(None, unicode(e.message))
                                    else:
                                        add_url = '/add/{}/{}/{}/{}/'.format(
                                        get_metadata(model, 'app_label'), model.__name__.lower(), self.obj.pk,
                                        relation_name.replace('_set', ''))
                                        add_label = 'Adicionar {}'.format(get_metadata(qs.model, 'verbose_name'))
                                        add_label = get_metadata(qs.model, 'add_label', add_label)
                                        related_paginator.add_action(add_label, add_url,
                                                                     'popup', 'fa-plus')

                            fieldset_dict['paginators'].append(related_paginator)

                if 'extra' in fieldset[1]:
                    fieldset_dict['extra'] = []
                    for info in fieldset[1]['extra']:
                        fieldset_dict['extra'].append(info)

    def get_active_fieldsets(self):
        return self.fieldsets_without_tab_name + self.fieldsets_with_tab_name

    def __unicode__(self):
        return self.render('model_panel.html')


class IconPanel(Component):

    def __init__(self, request, title, icon=None):
        super(IconPanel, self).__init__(request)
        self.title = title
        self.icon = icon
        self.items = []

    def add_item(self, label, url, icon=None, css='ajax'):
        item = dict(label=label, url=url, css=css, icon=icon or self.icon)
        self.items.append(item)

    def __unicode__(self):
        return self.render('icon_panel.html')


class ShortcutPanel(Component):

    def __init__(self, request):
        from djangoplus.cache import loader
        super(ShortcutPanel, self).__init__(request)
        self.items = []

        for model, add_shortcut in loader.icon_panel_models:

            if type(add_shortcut) == bool:
                add_model = add_shortcut
            else:
                if not type(add_shortcut) in (list, tuple):
                    add_shortcut = add_shortcut,
                add_model = request.user.in_group(*add_shortcut)

            if add_model or request.user.is_superuser:
                if permissions.has_add_permission(request, model):
                    self.add_model(model)
        for item in loader.views:
            if item['add_shortcut']:
                if permissions.check_group_or_permission(request, item['can_view']):
                    self.add(item['icon'], item['title'], None, item['url'], item['can_view'], item['style'])

    def add(self, icon, description, count=None, url=None, perm_or_group=None, style='ajax'):
        if permissions.check_group_or_permission(self.request, perm_or_group):
            item = dict(icon=icon, description=description, count=count, url=url or '#', style=style)
            self.items.append(item)

    def __unicode__(self):
        return self.render('shortcut_panel.html')

    def add_model(self, model):
        icon = get_metadata(model, 'icon')
        prefix = get_metadata(model, 'verbose_female') and 'Nova' or 'Novo'
        description = '{} {}'.format(prefix, get_metadata(model, 'verbose_name'))
        description = get_metadata(model, 'add_label', description)
        url = '/add/{}/{}/'.format(get_metadata(model, 'app_label'), model.__name__.lower())
        permission = '{}.list_{}'.format(get_metadata(model, 'app_label'), model.__name__.lower())
        self.add(icon, description, None, url, permission)

    def add_models(self, *models):
        for model in models:
            self.add_model(model)


class CardPanel(Component):

    def __init__(self, request):
        from djangoplus.cache import loader
        super(CardPanel, self).__init__(request)
        self.items = []

        for model, list_shortcut in loader.card_panel_models:

            if type(list_shortcut) == bool:
                add_model = list_shortcut
            else:
                if not type(list_shortcut) in (list, tuple):
                    list_shortcut = list_shortcut,
                add_model = request.user.in_group(*list_shortcut)

            if add_model or request.user.is_superuser:
                if permissions.has_list_permission(request, model):
                    self.add_model(model)

                if model in loader.subsets:
                    icon = get_metadata(model, 'icon')
                    title = get_metadata(model, 'verbose_name_plural')
                    app_label = get_metadata(model, 'app_label')
                    model_name = model.__name__.lower()
                    for item in loader.subsets[model]:
                        can_view = item['can_view']
                        # TODO False
                        if False and permissions.check_group_or_permission(self.request, can_view):
                            attr_name = item['function'].im_func.func_name
                            qs = model.objects.all(self.request.user)
                            qs = getattr(qs, attr_name)()
                            count = qs.count()
                            if count:
                                url = '/list/{}/{}/{}/'.format(app_label, model_name, attr_name)
                                self.add(icon, title, count, url, 'bg-info', None, item['title'])

        for item in loader.views:
            if False:  # TODO False
                if permissions.check_group_or_permission(request, item['can_view']):
                    self.add(item['icon'], item['menu'], None, item['url'], 'bg-info', item['can_view'], item['style'])

    def add(self, icon, title, count=None, url=None, css='bg-info', perm_or_group=None, description=''):
        if permissions.check_group_or_permission(self.request, perm_or_group):
            item = dict(icon=icon, title=title, count=count, url=url, css=css, description=description)
            self.items.append(item)

    def __unicode__(self):
        return self.render('card_panel.html')

    def add_model(self, model):
        self.add_models(model)

    def add_models(self, *models):
        for model in models:
            icon = get_metadata(model, 'icon')
            title = get_metadata(model, 'verbose_name_plural')
            app_label = get_metadata(model, 'app_label')
            model_name = model.__name__.lower()
            url = '/list/{}/{}/'.format(app_label, model_name)
            permission = '{}.list_{}'.format(app_label, model_name)
            self.add(icon, title, None, url, 'bg-info', permission)


class DashboardPanel(Component):

    def __init__(self, request):

        super(DashboardPanel, self).__init__(request)
        self.top = []
        self.center = []
        self.left = []
        self.right = []
        self.bottom = []

        from djangoplus.cache import loader
        for model in loader.subsets:
            icon = get_metadata(model, 'icon', 'fa-bell-o')
            title = get_metadata(model, 'verbose_name_plural')
            app_label = get_metadata(model, 'app_label')
            model_name = model.__name__.lower()
            for item in loader.subsets[model]:
                description = item['title']
                can_view = item['can_view']
                notify = item['notify']
                if notify and permissions.check_group_or_permission(request, can_view):
                    attr_name = item['function'].im_func.func_name
                    qs = model.objects.all(request.user)
                    qs = getattr(qs, attr_name)()
                    count = qs.count()
                    if count:
                        url = '/list/{}/{}/{}/'.format(app_label, model_name, attr_name)
                        notification_panel = NotificationPanel(request, title, count, url, description, icon)
                        self.right.append(notification_panel)

        icon_panel = ShortcutPanel(request)
        card_panel = CardPanel(request)

        self.top.append(icon_panel)
        self.center.append(card_panel)

        for item in loader.subset_widgets:

            model = item['model']
            title = item['title']
            function = item['function']
            dashboard = item['dashboard']
            formatter = item['formatter']
            list_display = item.get('list_display')
            link = item['link']

            l = []
            if type(dashboard) == dict:
                for position, group_names in dashboard.items():
                    group_names = type(group_names) == tuple and group_names or (group_names,)
                    l.append((position, group_names))
            else:
                l.append((dashboard, item['can_view']))

            for position, group_names in l:
                if permissions.check_group_or_permission(request, group_names, ignore_superuser=True):
                    qs = model.objects.all()
                    qs.user = request.user
                    f_return = getattr(qs, function)()
                    html = ''

                    if type(f_return) in (int, Decimal):
                        verbose_name = get_metadata(model, 'verbose_name_plural')
                        icon = get_metadata(model, 'icon')
                        panel = NumberPanel(request, verbose_name, f_return, title, icon)
                        html = unicode(panel)

                    if type(f_return).__name__ == 'QueryStatistics' and not formatter:
                        formatter = 'statistics'

                    if formatter:
                        func = loader.formatters[formatter]
                        if len(func.func_code.co_varnames) == 1:
                            html = unicode(func(f_return))
                        else:
                            html = unicode(func(f_return, request=self.request, verbose_name=title))
                    elif hasattr(f_return, 'model'):
                        compact = position in ('left', 'right')
                        app_label = get_metadata(model, 'app_label')
                        model_name = model.__name__.lower()
                        verbose_name_plural = get_metadata(model, 'verbose_name_plural')
                        if link:
                            title = '{} {}'.format(verbose_name_plural, title)
                        url = '/list/{}/{}/{}/'.format(app_label, model_name, function)
                        paginator = Paginator(self.request, f_return, title, readonly=compact, list_display=list_display, list_filter=(), search_fields=(), list_subsets=[function], url=link and url or None)
                        if compact:
                            paginator.column_names = paginator.column_names[0:1]
                        html = unicode(paginator)

                    if position == 'top':
                        self.top.append(html)
                    elif position == 'center':
                        self.center.append(html)
                    elif position == 'left':
                        self.left.append(html)
                    elif position == 'right':
                        self.right.append(html)
                    elif position == 'bottom':
                        self.bottom.append(html)

        for item in loader.widgets:
            if permissions.check_group_or_permission(request, item['can_view'], ignore_superuser=True):
                function = item['function']
                position = item['position']
                f_return = function(request)
                html = render_to_string(['{}.html'.format(function.func_name), 'widget.html'], f_return, request)
                if position == 'top':
                    self.top.append(html)
                elif position == 'center':
                    self.center.append(html)
                elif position == 'left':
                    self.left.append(html)
                elif position == 'right':
                    self.right.append(html)
                elif position == 'bottom':
                    self.bottom.append(html)

    def __unicode__(self):
        return self.render('dashboard_panel.html')


class NumberPanel(Component):

    def __init__(self, request, title, number, description, icon=None):
        super(NumberPanel, self).__init__(request)
        self.title = title
        self.number = number
        self.description = description
        self.icon = icon or 'fa-comment-o'

    def __unicode__(self):
        return self.render('number_panel.html')


class NotificationPanel(Component):

    def __init__(self, request, title, count, url, description, icon=None):
        super(NotificationPanel, self).__init__(request)
        self.title = title
        self.count = count
        self.url = url
        self.description = description
        self.icon = icon or 'fa-bell-o'

    def __unicode__(self):
        return self.render('notification_panel.html')