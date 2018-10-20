# -*- coding: utf-8 -*-
from decimal import Decimal
from djangoplus.ui import RequestComponent
from django.utils.text import slugify
from djangoplus.utils import permissions
from django.template.loader import render_to_string
from djangoplus.ui.components.paginator import Paginator
from djangoplus.ui.components.navigation.dropdown import ModelDropDown, GroupDropDown
from djangoplus.utils.metadata import get_metadata, get_fieldsets, find_field_by_name, get_fiendly_name, \
    check_condition, is_one_to_one, is_many_to_one, should_filter_or_display


class Panel(RequestComponent):

    def __init__(self, request, title=None, text=None, icon=None):
        super(Panel, self).__init__(title, request)
        self.title = title
        self.text = text
        self.labels = []
        self.icon = icon


class ModelPanel(RequestComponent):
    def __init__(self, request, obj, current_tab=None, parent=None, fieldsets=None, complete=True, readonly=False, printable=True):

        super(ModelPanel, self).__init__(obj.pk, request)

        self.obj = obj
        self.title = obj.pk and str(obj) or get_metadata(type(obj), 'verbose_name')
        self.id = self.title
        self.tabs = []
        self.current_tab = current_tab
        self.message = None
        self.complete = complete
        self.readonly = readonly
        self.printable = printable
        self.drop_down = None
        fieldsets = fieldsets or get_metadata(type(obj), 'view_fieldsets', [])
        if not fieldsets:
            fieldsets = get_fieldsets(type(obj))

        if self.complete:
            self.drop_down = ModelDropDown(self.request, type(self.obj))
            self.drop_down.add_actions(self.obj, fieldset_title='')
            if self.printable:
                self.drop_down.add_action('Imprimir', url='?pdf={}&pk='.format(self.id), css='ajax', icon='fa-print', category='Imprimir')
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
            fieldset_image = info.get('image')

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
                            if attr_name != parent and attr_name != fieldset_image:
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
                    from djangoplus.utils.relations import Relation
                    for relation_name in relations + inlines:
                        component = Relation(self.obj, relation_name).get_component(self.request, self.as_pdf)
                        fieldset_dict['paginators'].append(component)

                else:
                    for relation_name in relations + inlines:
                        if relation_name in [field.name for field in get_metadata(model, 'get_fields')]:
                            relation_field = find_field_by_name(model, relation_name)
                            if is_one_to_one(model, relation_name) or is_many_to_one(model, relation_name):
                                fieldset_dict['fields'].append(
                                    [dict(verbose_name=relation_field.verbose_name, name=relation_name)]
                                )

                if 'extra' in fieldset[1]:
                    fieldset_dict['extra'] = []
                    for info in fieldset[1]['extra']:
                        fieldset_dict['extra'].append(info)

    def get_active_fieldsets(self):
        return self.fieldsets_without_tab_name + self.fieldsets_with_tab_name


class IconPanel(RequestComponent):

    def __init__(self, request, title, icon=None):
        super(IconPanel, self).__init__('iconpanel', request)
        self.title = title
        self.icon = icon
        self.items = []

    def add_item(self, label, url, icon=None, css='ajax'):
        item = dict(label=label, url=url, css=css, icon=icon or self.icon)
        self.items.append(item)


class ShortcutPanel(RequestComponent):

    def __init__(self, request):
        from djangoplus.cache import loader
        super(ShortcutPanel, self).__init__('shortcutpanel', request)
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


class CardPanel(RequestComponent):

    class Media:
        pass
        # css = {'all': ('/static/css/cardpanel.css',)}

    def __init__(self, request):
        super(CardPanel, self).__init__('cardpanel', request)

        self.items = []

        from djangoplus.cache import loader
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
                            attr_name = item['function'].__func__.__name__
                            qs = model.objects.all(self.request.user)
                            qs = getattr(qs, attr_name)()
                            count = qs.count()
                            if count:
                                url = '/list/{}/{}/{}/'.format(app_label, model_name, attr_name)
                                self.add(icon, title, count, url, '', None, item['title'])

        for item in loader.views:
            if False:  # TODO False
                if permissions.check_group_or_permission(request, item['can_view']):
                    self.add(item['icon'], item['menu'], None, item['url'], '', item['can_view'], item['style'])

    def add(self, icon, title, count=None, url=None, css='', perm_or_group=None, description=''):
        if permissions.check_group_or_permission(self.request, perm_or_group):
            item = dict(icon=icon, title=title, count=count, url=url, css=css, description=description)
            self.items.append(item)

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
            self.add(icon, title, None, url, '', permission)


class DashboardPanel(RequestComponent):

    def __init__(self, request):

        super(DashboardPanel, self).__init__('dashboard', request)
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
                notify = item['notify']
                if notify is True or notify and permissions.check_group_or_permission(request, notify):
                    attr_name = item['function'].__func__.__name__
                    qs = model.objects.all(request.user)
                    qs = getattr(qs, attr_name)()
                    count = qs.count()
                    if count:
                        url = '/list/{}/{}/{}/'.format(app_label, model_name, attr_name)
                        notification_panel = NotificationPanel(request, title, count, url, description, icon)
                        self.right.append(notification_panel)
        for model in loader.list_dashboard:
            title = get_metadata(model, 'verbose_name_plural')
            position = get_metadata(model, 'dashboard')
            paginator = Paginator(request, model.objects.all(request.user), title)
            self.add(paginator, position)

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
                for position, group_names in list(dashboard.items()):
                    group_names = type(group_names) == tuple and group_names or (group_names,)
                    l.append((position, group_names))
            else:
                l.append((dashboard, item['can_view']))

            for position, group_names in l:
                if permissions.check_group_or_permission(request, group_names, ignore_superuser=True):
                    qs = model.objects.all(request.user)
                    f_return = getattr(qs, function)()
                    html = ''

                    if type(f_return) in (int, Decimal):
                        verbose_name = get_metadata(model, 'verbose_name_plural')
                        icon = get_metadata(model, 'icon')
                        panel = NumberPanel(request, verbose_name, f_return, title, icon)
                        html = str(panel)

                    if type(f_return).__name__ == 'QueryStatistics' and not formatter:
                        formatter = 'statistics'

                    if formatter:
                        func = loader.formatters[formatter]
                        if len(func.__code__.co_varnames) == 1:
                            html = str(func(f_return))
                        else:
                            html = str(func(f_return, request=self.request, verbose_name=title))
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
                        html = str(paginator)

                    self.add(html, position)

        for item in loader.widgets:
            if permissions.check_group_or_permission(request, item['can_view'], ignore_superuser=True):
                function = item['function']
                position = item['position']
                f_return = function(request)
                html = render_to_string(['{}.html'.format(function.__name__), 'dashboard.html'], f_return, request)
                self.add(html, position)

    def add(self, component, position):
        if position == 'top':
            self.top.append(component)
        elif position == 'center':
            self.center.append(component)
        elif position == 'left':
            self.left.append(component)
        elif position == 'right':
            self.right.append(component)
        elif position == 'bottom':
            self.bottom.append(component)


class NumberPanel(RequestComponent):

    def __init__(self, request, title, number, description, icon=None):
        super(NumberPanel, self).__init__(title, request)
        self.title = title
        self.number = number
        self.description = description
        self.icon = icon or 'fa-comment-o'


class NotificationPanel(RequestComponent):

    def __init__(self, request, title, count, url, description, icon=None):
        super(NotificationPanel, self).__init__(title, request)
        self.title = title
        self.count = count
        self.url = url
        self.description = description
        self.icon = icon or 'fa-bell-o'
