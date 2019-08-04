# -*- coding: utf-8 -*-

import copy
from collections import OrderedDict
from djangoplus.ui.components import forms
from django.db.models.aggregates import Sum
from djangoplus.utils.tabulardata import tolist
from djangoplus.utils.formatter import normalyze
from djangoplus.ui.components.forms import factory
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from djangoplus.utils import permissions, should_add_action, get_role_values_for_condition
from djangoplus.ui.components.navigation.breadcrumbs import httprr
from djangoplus.ui.components import Component, ComponentHasResponseException
from djangoplus.utils.http import CsvResponse, XlsResponse, ReportResponse, return_response
from djangoplus.ui.components.navigation.dropdown import ModelDropDown, GroupDropDown
from djangoplus.utils.metadata import get_metadata, get_field, get_fiendly_name, should_filter_or_display, getattr2, \
    get_parameters_names, count_parameters_names


class Paginator(Component):
    def __init__(self, request, qs, title=None, list_display=None, list_filter=None, search_fields=None,
                 list_per_page=25, list_subsets=None, exclude=None, relation=None, readonly=False, is_list_view=False,
                 help_text=None, url=None, template=None, uid=None):

        super(Paginator, self).__init__(is_list_view and '_' or abs(hash(title)), request)
        if relation:
            qs = qs.model.objects.filter(pk__in=qs.values_list('pk', flat=True))
        else:
            qs = qs.all()
        self.qs = qs
        self.title = title
        self.list_display = list_display
        self.list_filter = list_filter
        self.search_fields = search_fields
        self.list_per_page = list_per_page
        self.subsets = None
        self.exclude = exclude
        self.relation = relation
        self.readonly = readonly
        self.is_list_view = is_list_view
        self.icon = get_metadata(qs.model, 'icon', None)
        self.list_total = get_metadata(qs.model, 'list_total', None)
        self.ordering = get_metadata(qs.model, 'ordering', None)
        self.template = template or get_metadata(self.qs.model, 'list_template', 'datagrid.html')
        self.help_text = help_text
        self.url = url
        self.display_checkboxes = False
        self.action_names = None

        self.filters = []
        self.pagination = ''

        self.original_qs = qs
        self.count = None

        # tabs
        self.tabs = []
        self.current_tab = self._get_from_request('tab', None)
        if list_subsets is not None:
            self.subsets = OrderedDict()
            for subset_name in list_subsets:
                self.subsets[subset_name] = {}
        self._load_tabs()

        # list display
        self._configure_list_display()

        # column names
        self.column_names = []
        self._configure_column_names()

        # drop down
        self.class_dropdown = GroupDropDown(request, style='class-action')
        self.queryset_dropdown = GroupDropDown(request, style='queryset-action disabled')
        self.drop_down = ModelDropDown(request, qs.model)

        if hasattr(self.qs, 'permission_map'):
            self.permission_map = self.qs.permission_map
        self.qs = self._filter_queryset(self.qs)

    def get_current_tab_name(self):
        if len(self.tabs) > 1:
            if self.current_tab and self.current_tab != 'all':
                return self.current_tab
        if len(self.tabs) > 0:
            return self.tabs[0][0]
        return ''
    
    def get_tab(self):
        return self._get_from_request('tab', '')
    
    def get_search_fields(self):
        if self.search_fields is not None:
            return self.search_fields
        return get_metadata(self.qs.model, 'search_fields', [])
    
    def get_list_filter(self):
        if self.list_filter is None:
            self.list_filter = copy.deepcopy(get_metadata(self.qs.model, 'list_filter', None))
            if self.list_filter is None:
                self.list_filter = []
                for field in get_metadata(self.qs.model, 'fields'):
                    if field.remote_field and field.remote_field.model:
                        if not field.name.endswith('_ptr') and field.name != self.rel:
                            self.list_filter.append(field.name)
                    elif hasattr(field, 'choices') and field.choices:
                        self.list_filter.append(field.name)
                    elif type(field).__name__ in ['BooleanField', 'NullBooleanField', 'DateField', 'DateTimeField']:
                        self.list_filter.append(field.name)
        return self.list_filter

    def get_filter_form(self):
        form = forms.Form(self.request)
        form.title = 'Filtros'
        form.icon = 'fa-filter'
        form.partial = True
        self.filters = []
        for list_filter in self.get_list_filter():
            if type(list_filter) in (tuple, list):
                field_names = list_filter
            else:
                field_names = list_filter,
            for field_name in field_names:
                if self.relation and field_name == self.relation.hidden_field_name:
                    continue
                field = get_field(self.qs.model, field_name)
                form_field_name = '{}{}'.format(field_name, self.id)
                if hasattr(field, 'auto_now'):
                    initial = (self._get_from_request(field_name, None, '_0'), self._get_from_request(field_name, None, '_1'))
                    form.fields[form_field_name] = forms.DateFilterField(label=normalyze(field.verbose_name), initial=initial, required=False)
                else:
                    initial = self._get_from_request(field_name)
                    if type(field).__name__ in ['BooleanField', 'NullBooleanField']:
                        form.fields[form_field_name] = forms.ChoiceField(
                            choices=[['', ''], ['sim', 'Sim'], ['nao', 'Não'], ], label=normalyze(field.verbose_name), initial=initial, required=False)
                    elif hasattr(field, 'choices') and field.choices:
                        form.fields[form_field_name] = forms.ChoiceField(choices=[['', '']] + field.choices, label=normalyze(field.verbose_name), initial=initial, required=False)
                    else:
                        if hasattr(field.remote_field.model, 'unit_ptr_id') and self.request.user.role_set.filter(scope__unit__isnull=False).values_list('scope__unit', flat=True).count() == 1:
                            continue
                        if hasattr(field.remote_field.model, 'organization_ptr_id') and self.request.user.role_set.filter(scope__organization__isnull=False).values_list('scope__organization', flat=True).count() == 1:
                            continue
                        if field.remote_field and not should_filter_or_display(self.request, self.qs.model, field.remote_field.model):
                            continue
                        if initial:
                            if self.original_qs.query.can_filter():
                                pks = self.original_qs.order_by(field_name).values_list(field_name, flat=True).distinct()
                            else:
                                pks = self.original_qs.model.objects.all().order_by(field_name).values_list(field_name, flat=True).distinct()
                            qs = field.remote_field.model.objects.get_queryset().filter(pk__in=pks)
                            qs = qs | field.remote_field.model.objects.get_queryset().filter(pk=initial)
                        else:
                            if self.qs.query.can_filter():
                                pks = self.qs.order_by(field_name).values_list(field_name, flat=True).distinct()
                            else:
                                pks = self.qs.model.objects.all().order_by(field_name).values_list(field_name, flat=True).distinct()
                            qs = field.remote_field.model.objects.get_queryset().filter(pk__in=pks)
                        empty_label = ''

                        form.fields[form_field_name] = forms.ModelChoiceField(qs, label=normalyze(field.verbose_name), initial=initial, empty_label=empty_label, required=False, lazy=True, ignore_lookup=True, minimum_input_length=0)
                    form.fields[form_field_name].widget.attrs['data-placeholder'] = field.verbose_name
                    if initial:
                        label = form.fields[form_field_name].label
                        value = form.fields[form_field_name].clean(initial)
                        if type(form.fields[form_field_name]) == forms.ChoiceField:
                            for x, y in form.fields[form_field_name].choices:
                                if str(x) == str(value):
                                    value = y
                                    break
                        self.filters.append((label, value))
        return form

    def get_selected_ids(self):
        ids = self.request.GET.get('ids', None)
        if ids:
            ids = ids.split(',')
            ids = 0 not in ids and ids or None
        return ids

    def add_action(self, label, url, css, icon=None, category=None):
        self.class_dropdown.add_action(label, url, 'class-action {}'.format(css), icon, category)

    def add_queryset_action(self, label, url, css, icon=None, category=None, subset=None):
        if not subset or self.get_tab() == subset:
            if not self.mobile:
                self.queryset_dropdown.add_action(label, url, 'queryset-action disabled {}'.format(css), icon, category)

    def load_actions(self, action_names=None):

        from djangoplus.cache import CACHE
        export_url = self.request.get_full_path()
        list_csv = get_metadata(self.qs.model, 'list_csv')
        list_xls = get_metadata(self.qs.model, 'list_xls')
        log = get_metadata(self.qs.model, 'log')
        app_label = get_metadata(self.qs.model, 'app_label')
        list_pdf = get_metadata(self.qs.model, 'list_pdf')
        self.action_names = action_names or []

        subset = self.subsets and list(self.subsets.keys())[0] or None
        subsetp = self.request.GET.get('tab{}'.format(self.request.GET.get('tid')))
        subset_name = subsetp or subset

        # class actions defined in the manager
        if self.qs.model in CACHE['CLASS_ACTIONS']:
            for group in CACHE['CLASS_ACTIONS'][self.qs.model]:
                for view_name in CACHE['CLASS_ACTIONS'][self.qs.model][group]:
                    _action = CACHE['CLASS_ACTIONS'][self.qs.model][group][view_name]
                    action_verbose_name = _action['verbose_name']
                    action_inline = _action['inline']
                    action_subsets = _action['subsets']
                    action_can_execute = _action['can_execute']
                    action_category = _action['group']
                    action_expose = _action['expose']
                    action_style = _action['style'] or 'popup'
                    if 'popup' not in action_style:
                        action_style = '{} popup'.format(action_style)
                    if self.is_list_view or view_name in self.action_names:
                        add_action = should_add_action(action_inline, action_subsets, subset_name)
                        add_action = add_action and (True in action_expose or 'web' in action_expose)
                        if add_action and permissions.check_group_or_permission(self.request, action_can_execute):
                            func = getattr(self.qs, view_name)
                            ignore_pdf = False
                            if count_parameters_names(func) > 0:
                                action_style = action_style.replace('pdf', '')
                                ignore_pdf = True
                            char = '?' in self.request.get_full_path() and '&' or '?'
                            url = '{}{}{}'.format(self.request.get_full_path(), char, '{}='.format(view_name))
                            self.add_action(action_verbose_name, url, action_style, None, action_category)
                            if view_name in self.request.GET:
                                self._proccess_request(func, _action, ignore_pdf)

        # subset actions defined in the manager
        if self.qs.model in CACHE['QUERYSET_ACTIONS']:
            for group in CACHE['QUERYSET_ACTIONS'][self.qs.model]:
                for view_name in CACHE['QUERYSET_ACTIONS'][self.qs.model][group]:
                    _action = CACHE['QUERYSET_ACTIONS'][self.qs.model][group][view_name]
                    action_verbose_name = _action['verbose_name']
                    action_can_execute = _action['can_execute']
                    action_inline = _action['inline']
                    action_icon = _action['icon']
                    action_subsets = _action['subsets']
                    action_condition = _action['condition']
                    action_source = _action['source']
                    action_category = _action['group']
                    action_expose = _action['expose']
                    action_style = _action['style'] or 'popup'
                    if 'popup' not in action_style:
                        action_style = '{} popup'.format(action_style)
                    if view_name in self.action_names or (self.is_list_view and action_inline) or (self.current_tab in action_subsets):
                        add_action = should_add_action(action_inline, action_subsets, subset_name)
                        add_action = add_action and (True in action_expose or 'web' in action_expose)
                        if add_action and permissions.check_group_or_permission(self.request, action_can_execute):
                            self.display_checkboxes = self.display_checkboxes or not action_source == 'view'
                            func = getattr(self.qs, view_name)
                            ignore_pdf = False
                            char = '?' in self.request.get_full_path() and '&' or '?'
                            url = '{}{}{}'.format(self.request.get_full_path(), char, '{}='.format(view_name))
                            if count_parameters_names(func) > 0:
                                ignore_pdf = True
                                action_style = action_style.replace('pdf', '')
                            self.add_queryset_action(
                                action_verbose_name, url, action_style, action_icon, action_category, action_condition
                            )

                            if view_name in self.request.GET:
                                ids = self.get_selected_ids()
                                if ids:
                                    qs = self.get_queryset(paginate=False).filter(id__in=ids)
                                else:
                                    break
                                func = getattr(qs, view_name)
                                self._proccess_request(func, _action, ignore_pdf)

        # class actions defined in views module
        if self.qs.model in CACHE['CLASS_VIEW_ACTIONS']:
            for group in CACHE['CLASS_VIEW_ACTIONS'][self.qs.model]:
                for view_name in CACHE['CLASS_VIEW_ACTIONS'][self.qs.model][group]:
                    _action = CACHE['CLASS_VIEW_ACTIONS'][self.qs.model][group][view_name]
                    action_verbose_name = _action['verbose_name']
                    action_inline = _action['inline']
                    action_subsets = _action['subsets']
                    action_can_execute = _action['can_execute']
                    action_category = _action['group']
                    action_expose = _action['expose']
                    action_style = _action['style'] or 'popup'
                    url = '/{}/{}/'.format(get_metadata(self.qs.model, 'app_label'), view_name)
                    action_style = action_style.replace('popup', '')
                    if self.is_list_view or view_name in self.action_names:
                        add_action = should_add_action(action_inline, action_subsets, subset_name)
                        add_action = add_action and (True in action_expose or 'web' in action_expose)
                        if add_action and permissions.check_group_or_permission(self.request, action_can_execute):
                            self.add_action(action_verbose_name, url, action_style, None, action_category)

        if self.is_list_view:
            # utility actions
            if list_csv:
                export_url = '?' in export_url and '{}&export=csv'.format(export_url) or '{}?export=csv'.format(export_url)
                self.add_action('Exportar CSV', export_url, 'ajax', 'fa-table')

            if list_xls:
                export_url = '?' in export_url and '{}&export=excel'.format(export_url) or '{}?export=excel'.format(export_url)
                self.add_action('Exportar Excel', export_url, 'ajax', 'fa-file-excel-o')

            if log:
                log_url = '/log/{}/{}/'.format(app_label, self.qs.model.__name__.lower())
                if self.request.user.has_perm('admin.list_log'):
                    self.add_action('Visualizar Log', log_url, 'ajax', 'fa-history')

            if list_pdf:
                pdf_url = '?' in export_url and '{}&export=pdf'.format(export_url) or '{}?export=pdf'.format(export_url)
                self.add_action('Imprimir', pdf_url, 'ajax', 'fa-print')

            # registration action
            subclasses = self.qs.model.__subclasses__()
            if not subclasses and not self.subsets and permissions.has_add_permission(self.request, self.qs.model):
                instance = self.qs.model()
                instance._user = self.request.user
                if not hasattr(instance, 'can_add') or instance.can_add():
                    if self.relation:
                        verbose_name = get_metadata(self.qs.model, 'verbose_name')
                        add_label = get_metadata(self.qs.model, 'add_label', '{} {}'.format(_('Add'), verbose_name))
                    else:
                        add_label = get_metadata(self.qs.model, 'add_label', _('Add'))
                    add_url = '/add/{}/{}/'.format(app_label, self.qs.model.__name__.lower())
                    self.add_action(add_label, add_url, 'ajax', 'fa-plus')

            for subclass in subclasses:
                app = get_metadata(subclass, 'app_label')
                verbose_name = get_metadata(subclass, 'verbose_name')
                cls = subclass.__name__.lower()
                if permissions.has_add_permission(self.request, subclass):
                    self.add_action(verbose_name, '/add/{}/{}/'.format(app, cls), False, 'fa-plus')

    def _proccess_request(self, func, _action, ignore_pdf):

        form = None
        f_return = None
        redirect_url = None

        if count_parameters_names(func) > 0:
            form = factory.get_class_action_form(self.request, self.qs.model, _action, func)
            if form.is_valid():
                params = []
                for param in get_parameters_names(func):
                    if param in form.cleaned_data:
                        params.append(form.cleaned_data[param])
                try:
                    f_return = func(*params)
                    ignore_pdf = False
                    if f_return is None:
                        redirect_url = '..'
                except ValidationError as e:
                    form.add_error(None, str(e.message))
        else:
            f_return = func()
            ignore_pdf = False
            if f_return is None:
                redirect_url = '.'

        if redirect_url:
            self.request.GET._mutable = True
            if 'ids' in self.request.GET:
                del self.request.GET['ids']
            del self.request.GET[_action['view_name']]
            self.request.GET._mutable = False
            raise ComponentHasResponseException(
                httprr(self.request, redirect_url, _action['message'])
            )
        else:
            action_style = _action['style']
            if f_return is None:
                f_return = dict(form=form)
                template_name = 'default.html'
            else:
                template_name = '{}.html'.format(_action['view_name'])
            return_response(
                f_return, self.request, None, action_style, template_name,
                raise_response=True, ignore_pdf=ignore_pdf
            )

    def get_total(self):
        if self.list_total:
            return self.qs.aggregate(sum=Sum(self.list_total)).get('sum')
        else:
            return None

    def can_show_actions(self):
        return permissions.has_view_permission(self.request, self.qs.model)

    def get_queryset(self, paginate=True):
        queryset = self.qs
        self.count = queryset.count()
        if self.ordering:
            if not type (self.ordering) == tuple:
                self.ordering = self.ordering,
            queryset = queryset.order_by(*self.ordering)
        if self.get_list_filter():
            queryset = queryset.distinct()
        if paginate:
            l = []

            list_per_page = self._get_list_per_page()
            page_numer = int(self.count / list_per_page + (((self.count % list_per_page) > 0 or self.count < list_per_page) and 1 or 0))
            current_page = int(self._get_from_request('page', 1))
            start = current_page * list_per_page - list_per_page
            end = start + list_per_page
            queryset = queryset[start:end]
            if page_numer > 1:
                l.append(
                    '<ul class="pagination pagination-xs m-top-none pull-right pagination-split">'
                    '<li class="disabled"><a href="#!"><i class="fa fa-chevron-left"></i></a></li>')
                for i in range(current_page-10, current_page+10):
                    if page_numer >= i > 0 and i:
                        onclick = "$('#page{}').val({});$('#{}').submit();".format(self.id, i, self.id)
                        if i == current_page:
                            css = 'active'
                        else:
                            css = 'waves-effect'
                        l.append('<li class="{}"><a href="javascript:" onclick="{}">{}</a></li>'.format(css, onclick, i))
                l.append('<li class="disabled"><a href="#!"><i class="fa fa-chevron-right"></i></a></li></ul>')
            self.pagination = ''.join(l)

        select_related = get_metadata(queryset.model, 'select_related')
        if select_related:
            queryset = queryset.select_related(*select_related)
        return queryset
    
    def get_q(self):
        return self._get_from_request('q', '')

    def _configure_list_display(self):
        hidden_fields = []
        if not self.list_display:
            self.list_display = list(get_metadata(self.qs.model, 'list_display', []))
        if not self.list_display:
            fields = []
            for field in get_metadata(self.qs.model, 'fields'):
                if not hasattr(field, 'display') or field.display:
                    fields.append(field)
            for field in get_metadata(self.qs.model, 'local_many_to_many'):
                if not hasattr(field, 'display') or field.display:
                    fields.append(field)
            for field in fields[1:6]:
                if not field.name.endswith('_ptr') and not field.name == 'ascii' and not type(field).__name__ == 'TreeIndexField':
                    if not hasattr(field, 'display') or field.display:
                        self.list_display.append(field.name)

        for field_name in self.list_display:
            if '__' in field_name:
                attr = getattr2(self.qs.model, field_name)
            else:
                attr = getattr(self.qs.model, field_name)
            if hasattr(attr, 'field_name'):
                field = getattr(self.qs.model, '_meta').get_field(attr.field_name)
                if hasattr(field, 'display') and not field.display:
                    hidden_fields.append(field_name)

            if self.relation and (field_name == self.relation.hidden_field_name or field_name.startswith('{}__'.format(self.relation.hidden_field_name))):
                hidden_fields.append(field_name)

        if self.exclude:
            for field_name in self.exclude:
                if field_name in self.list_display:
                    hidden_fields.append(field_name)

        for field_name in hidden_fields:
            self.list_display.remove(field_name)

    def _configure_column_names(self):
        for lookup in self.list_display:
            hide_field = False
            attr = getattr(self.qs.model, lookup.split('__')[0])
            if hasattr(attr, 'field') and attr.field.remote_field and attr.field.remote_field.model:
                if hasattr(attr.field.remote_field.model, 'unit_ptr_id') and self.request.user.role_set.filter(scope__unit__isnull=False).values_list('scope__unit', flat=True).count() == 1:
                    continue
                if hasattr(attr.field.remote_field.model, 'organization_ptr_id') and self.request.user.role_set.filter(scope__organization__isnull=False).values_list('scope__organization', flat=True).count() == 1:
                    continue
                if not should_filter_or_display(self.request, self.qs.model, attr.field.remote_field.model):
                    hide_field = True
            if not hide_field:
                self.column_names.append(get_fiendly_name(self.qs.model, lookup, as_tuple=True))

    def _load_tabs(self):
        from djangoplus.cache import CACHE

        subsets = []
        if self.subsets is None:
            subsets = CACHE['SUBSETS'][self.qs.model]
        elif self.subsets:
            for subset_name in self.subsets.keys():
                for subset in CACHE['SUBSETS'][self.qs.model]:
                    if subset['name'] == subset_name:
                        subsets.append(subset)

        tab_qs = None
        active_queryset = None
        create_default_tab = True
        for subset in subsets:
            tab_title = subset['verbose_name']
            tab_function = subset['function']
            tab_can_view = subset['can_view']
            tab_name = subset['name']
            tab_help_text = subset['help_text']
            tab_order = subset['order']
            tab_list_display = subset['list_display']
            tab_list_filter = subset['list_filter']
            tab_search_fields = subset['search_fields']
            tab_active = False
            tab_expose = subset['expose']
            if True not in tab_expose and 'web' not in tab_expose:
                continue
            if permissions.check_group_or_permission(self.request, tab_can_view):
                func = getattr(self.qs, tab_function.__func__.__name__)
                params = get_role_values_for_condition(func, self.request.user)
                tab_qs = func(*params)
                tab_active = self.current_tab == tab_name
                self.tabs.append([tab_name, tab_title, tab_qs, tab_active, tab_order, tab_help_text])
                if (tab_active or len(subsets) == 1) and tab_help_text:
                    self.help_text = tab_help_text
            if tab_name == 'all':
                create_default_tab = False
            if tab_active:
                active_queryset = tab_qs
                self.drop_down = ModelDropDown(self.request, self.qs.model)
                self.list_display = tab_list_display
                self.list_filter = tab_list_filter
                self.search_fields = tab_search_fields

        self.tabs = sorted(self.tabs, key=lambda k: k[4])
        if (self.subsets is None or self.relation) and create_default_tab:
            tab_title = get_metadata(self.qs.model, 'verbose_female') and 'Todas' or 'Todos'
            tab_qs = self.original_qs.all()
            tab_active = self.current_tab == 'all'
            if tab_active:
                active_queryset = tab_qs
            tab_order = 0
            self.tabs.insert(0, ['', tab_title, tab_qs, tab_active, tab_order, None])
        if active_queryset is not None:
            self.qs = active_queryset
        elif self.tabs:
            self.tabs[0][3] = True
            self.qs = self.tabs[0][2]

    def _get_from_request(self, param_name, default='', suffix=''):
        key = '{}{}{}'.format(param_name, self.id, suffix)
        value = self.request.GET.get(str(self.id)) and self.request.GET.get(key) or default
        return value

    def _get_order_by(self):
        return self._get_from_request('order_by', '')

    def _get_page(self):
        return self._get_from_request('page', 1)

    def _get_list_per_page(self):
        return get_metadata(self.qs.model, 'list_per_page', self.list_per_page)

    def _filter_queryset(self, qs):
        distinct = False
        queryset = None
        search_fields = self.get_search_fields()
        q = self.get_q()
        if q:
            for i, search_field in enumerate(search_fields):
                if i == 0:
                    queryset = qs.filter(**{'{}__icontains'.format(search_field): q})
                else:
                    queryset = queryset | qs.filter(**{'{}__icontains'.format(search_field): q})
        else:
            queryset = qs
        for field_name in self.get_list_filter():
            field = get_field(queryset.model, field_name)
            if type(field).__name__ == 'DateField':
                filter_value = self._get_from_request(field_name, None, '_0')
                if filter_value:
                    date, month, year = filter_value.split('/')
                    filter_value = '{}-{}-{}'.format(year, month, date)
                    queryset = queryset.filter(**{'{}__gte'.format(field_name): filter_value})
                filter_value = self._get_from_request(field_name, None, '_1')
                if filter_value:
                    date, month, year = filter_value.split('/')
                    filter_value = '{}-{}-{}'.format(year, month, date)
                    queryset = queryset.filter(**{'{}__lte'.format(field_name): filter_value})
            elif type(field).__name__ in ['BooleanField', 'NullBooleanField']:
                filter_value = self._get_from_request(field_name)
                if filter_value:
                    filter_value = filter_value == 'sim'
                    queryset = queryset.filter(**{field_name: filter_value})
            else:
                filter_value = self._get_from_request(field_name)
                if filter_value:
                    queryset = queryset.filter(**{field_name: filter_value})
                if type(field).__name__ == 'ManyToManyField':
                    distinct = True
        order_by = self._get_from_request('order_by')

        tree_index_field = hasattr(self.qs.model, 'get_tree_index_field') and self.qs.model().get_tree_index_field() or None
        if tree_index_field:
            queryset = queryset.order_by(tree_index_field.name)
        else:
            if order_by:
                queryset = queryset.order_by(order_by.replace('0', ''))
            else:
                order_by = get_metadata(self.qs.model, 'order_by', iterable=True)
                try:
                    queryset = queryset.order_by(*order_by)
                except AssertionError:
                    # if the querycet was sliced
                    pass
        if distinct:
            queryset = queryset.distinct()
        return queryset.all(self.request.user)

    def process_request(self):
        export = self.request.GET.get('export', None)
        if export == 'pdf':
            raise ComponentHasResponseException(self._get_pdf_response())
        if export == 'csv':
            raise ComponentHasResponseException(self._get_csv_response(self.get_selected_ids()))
        elif export == 'excel':
            raise ComponentHasResponseException(self._get_xls_response(self.get_selected_ids()))

    def _get_csv_response(self, ids=()):
        list_csv = get_metadata(self.qs.model, 'list_csv')
        qs = self.get_queryset(False)
        if ids:
            qs = qs.filter(id__in=ids)
        return CsvResponse(tolist(qs, list_display=list_csv))

    def _get_xls_response(self, ids=()):
        list_xls = get_metadata(self.qs.model, 'list_xls')
        qs = self.get_queryset(False)
        if ids:
            qs = qs.filter(id__in=ids)
        return XlsResponse([('Dados', tolist(qs, list_display=list_xls))])

    def _get_pdf_response(self):
        self.as_pdf = True
        landscape = len(self.list_display) > 4
        return ReportResponse(self.title, self.request, [self], landscape)

    def __str__(self):
        return self.render('base/paginator.html')
