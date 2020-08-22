# -*- coding: utf-8 -*-

import tempfile
import qrcode
import base64
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from djangoplus.ui.components import forms
from djangoplus.utils.dateutils import DAY_NAMES
from djangoplus.utils.http import ComponentResponse
from djangoplus.ui.components import Component, ComponentHasResponseException
from djangoplus.utils.metadata import get_fiendly_name, get_field, get_metadata, getattr2


PERCENT_SYMBOL = '%'
DOLLAR_SYMBOL = '$'
REAIS_SYMBOL = 'R$'


class Chart(Component):

    def __init__(self, request, labels, series, groups=None, symbol=None, title=None, type=None):

        super(Chart, self).__init__(None, request)

        self.type = type or 'bar'
        self.labels = labels
        self.series = series
        self.groups = groups or []
        self.symbol = symbol or ''
        self.title = title
        self.color_index = 0
        self.display = False
        self.clickable = False

    def __str__(self):
        for i, serie in enumerate(self.series):
            for j, valor in enumerate(serie):
                if type(valor) == Decimal:
                    self.series[i][j] = float(valor)
                if valor:
                    self.display = True

        self.colors = []
        for color in settings.GRADIENT:
            self.colors.append(color)
        for i in range(len(self.colors), 16):
            self.colors.append('#FFFFFF')

        return super(Chart, self).__str__()

    def get_box_series(self):
        l = []
        serie = self.series[0]
        total = sum(serie)
        for i, label in enumerate(self.labels):
            percentage = int(total and serie[i]*100/total or 0)
            l.append((label, serie[i], percentage))
        return l

    def next_color(self):
        color = self.colors[self.color_index]
        self.color_index += 1
        return color

    def change_type(self, chart_type):
        self.type = chart_type
        return self

    def pie(self):
        return self.change_type('pie')

    def donut(self):
        return self.change_type('donut')

    def bar(self):
        return self.change_type('bar')

    def horizontal_bar(self):
        return self.change_type('horizontalbar')

    def stack(self):
        return self.change_type('stack')

    def horizontal_stack(self):
        return self.change_type('horizontalstack')

    def line(self):
        return self.change_type('line')

    def area(self):
        return self.change_type('area')

    def box(self):
        return self.change_type('box')


class QueryStatisticsChart(Chart):

    formatter_name = 'chart'
    template_name = 'chart.html'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None, type=None):

        groups = []
        labels = []
        series = []

        if queryset_statistics.groups:
            for label in queryset_statistics.labels:
                labels.append(label)
            for group in queryset_statistics.groups:
                groups.append(group)
        else:
            for label in queryset_statistics.labels:
                labels.append(label)

        for serie in queryset_statistics.series:
            series.append(serie)
    
        super(QueryStatisticsChart, self).__init__(request, labels, series, groups, symbol, title, type)

        self.clickable = self.request is not None
        self.queryset_statistics = queryset_statistics
        self.process_request()

    def process_request(self):
        super(Chart, self).process_request()
        if self.request and 'uuid' in self.request.GET and self.request.GET['uuid'] == self.title:
            note = None
            i, j = self.request.GET['position'].split('x')
            qs = self.queryset_statistics.querysets[int(i)][int(j)]
            title = get_metadata(qs.model, 'verbose_name_plural')
            if qs.count() > 25:
                qs = qs[0:25]
                note = u'Apenas uma amostra com 25 registros está sendo exibida.'
            component = ModelTable(self.request, title, qs, note=note)
            raise ComponentHasResponseException(ComponentResponse(component))


class QueryStatisticsLineChart(QueryStatisticsChart):
    formatter_name = 'line_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'line')


class QueryStatisticsAreaChart(QueryStatisticsChart):
    formatter_name = 'area_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'area')


class QueryStatisticsStackChart(QueryStatisticsChart):
    formatter_name = 'stack_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'stack')


class QueryStatisticsHorizontalStackChart(QueryStatisticsChart):
    formatter_name = 'horizontal_stack_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'horizontalstack')


class QueryStatisticsHorizontalBarChart(QueryStatisticsChart):
    formatter_name = 'horizontal_bar_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'horizontalbar')


class QueryStatisticsBarChart(QueryStatisticsChart):
    formatter_name = 'bar_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'bar')


class QueryStatisticsBoxChart(QueryStatisticsChart):
    formatter_name = 'box_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'box')


class QueryStatisticsDonutChart(QueryStatisticsChart):
    formatter_name = 'donut_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None):
        super().__init__(queryset_statistics, request, title, icon, symbol, 'donut')


class QueryStatisticsPieChart(QueryStatisticsChart):
    formatter_name = 'pie_chart'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None, symbol=None, type='pie'):
        super().__init__(queryset_statistics, request, title, icon, symbol)


class Timeline(Component):

    class Media:
        css = {'all': ('/static/css/timeline.css',)}

    def __init__(self, items, request=None, title=None):
        super(Timeline, self).__init__(title, request)
        self.items = items or []
        self.title = title
        self.width = 0

    def add(self, status, date):
        self.items.append((status, date))

    def __str__(self):
        self.width = str(100.0/len(self.items))
        return self.render('timeline.html')

class VerticalTimeline(Component):
    formatter_name = 'vertical_timeline'

    def __init__(self, items, request=None, title=None):
        super().__init__(title, request)
        self.items = items or []
        self.title = title

    def add(self, title, date, detail, url):
        self.items.append((title, date, detail, url))

class RoleSelector(Component):

    def __init__(self, request):
        super(RoleSelector, self).__init__('roleselector', request)
        self.groups = []
        self.process_request()
        self.display_button = False
        self.scopes = request.user.is_authenticated and request.user.get_appliable_scopes() or []
        self._load()

    def _load(self):
        if self.request.user.is_authenticated:
            from djangoplus.admin.models import Group, Role
            pks = self.request.user.role_set.values_list('group', flat=True).distinct()
            for group in Group.objects.filter(pk__in=pks).distinct():
                group.has_active_roles = self.request.user.role_set.filter(group=group, active=True).exists()
                group.scope_roles = self.request.user.role_set.filter(group=group, scope__isnull=False)
                self.groups.append(group)

    def process_request(self):
        if 'scope' in self.request.GET:
            from djangoplus.admin.models import Group
            self.request.user.role_set.update(active=False)
            self.request.user.permission_mapping = {}
            self.request.user.scope_id = self.request.GET['scope'] or None
            self.request.user.save()

            for group in Group.objects.filter(pk__in=self.request.GET.getlist('groups[]')):
                group.active_scope_roles = []
                for role in self.request.user.role_set.filter(group=group):
                    if role.scope and self.request.user.scope:
                        active = role.scope == self.request.user.scope
                        if not active:
                            organization = role.scope.is_organization()
                            if organization:
                                active = organization.get_units().filter(pk=self.request.user.scope.id).exists()
                        role.active = active
                    else:
                        role.active = True
                    role.save()
            
            self.request.user.check_role_groups()
            # if self.request.user.is_authenticated:
            #     print(self.request.user.permission_mapping.get('Diario:Diario'))
            raise ComponentHasResponseException(HttpResponse())


class QrCode(Component):
    def __init__(self, text, request=None, width=200, height=200):
        super(QrCode, self).__init__(text, request)
        self.text = text
        self.width = width
        self.height = height
        self.base64 = None

    def __str__(self):
        if self.as_pdf:
            qr = qrcode.QRCode()
            qr.add_data(self.text)
            image = qr.make_image()
            file_path = tempfile.mktemp()
            buffer = open(file_path, 'wb')
            image.save(buffer, format="JPEG")
            self.base64 = base64.b64encode(open(file_path, 'rb').read()).decode('utf-8')
        return super(QrCode, self).__str__()


class ProgressBar(Component):
    def __init__(self, percentual, request=None):
        self.percentual = percentual
        super(ProgressBar, self).__init__(None, request)


class Table(Component):
    def __init__(self, request, title, header=None, rows=None, footer=None, enumerable=True, note=None, icon=None):
        super(Table, self).__init__(title, request)
        self.title = title
        self.header = header or []
        self.rows = rows or []
        self.footer = footer or []
        self.enumerable = enumerable
        self.note = note
        self.icon = icon


class ModelTable(Table):
    def __init__(self, request, title, qs, list_display=(), note=None):

        header = []
        rows = []

        if not list_display:
            list_display = get_metadata(qs.model, 'list_display')

        for lookup in list_display:
            column_name = get_fiendly_name(qs.model, lookup, as_tuple=False)
            header.append(column_name)

        for obj in qs:
            row = []
            for lookup in list_display:
                row.append(getattr2(obj, lookup))
            rows.append(row)

        super(ModelTable, self).__init__(request, title, header, rows, note=note)


class QueryStatisticsTable(Table):

    formatter_name = 'statistics'

    def __init__(self, queryset_statistics, request=None, title=None, icon=None):
        if queryset_statistics.groups:
            header = []
            rows = []
            footer = []
            if queryset_statistics.series:
                add_xtotal = False
                for i, group in enumerate(queryset_statistics.groups):
                    row = [group]
                    for value in queryset_statistics.series[i]:
                        row.append(value)
                    if len(queryset_statistics.series) > 1:
                        if i < len(queryset_statistics.xtotal):
                            row.append(queryset_statistics.xtotal[i])
                            add_xtotal = True
                    rows.append(row)
                if add_xtotal:
                    footer = [' '] + queryset_statistics.ytotal + [queryset_statistics.total()]
                    header = [' '] + queryset_statistics.labels + [' ']
                else:
                    header = [' '] + queryset_statistics.labels
        else:
            header = []
            rows = []
            footer = []
            if queryset_statistics.series:
                for i, serie in enumerate(queryset_statistics.series[0]):
                    rows.append([queryset_statistics.labels[i], queryset_statistics.series[0][i]])
                if len(queryset_statistics.series[0]) > 1:
                    footer.append('')
                    footer.append(queryset_statistics.total())
        super(QueryStatisticsTable, self).__init__(request, title, header, rows, footer, enumerable=False)
        self.queryset_statistics = queryset_statistics
        self.symbol = queryset_statistics.symbol


class ModelReport(Component):
    def __init__(self, request, title, qs, list_display=(), list_filter=(), distinct=False):
        super(ModelReport, self).__init__(title, request)
        self.title = title
        self.qs = qs
        self.components = []
        self.filters = []

        if list_filter:
            form = forms.Form(request, method='GET')
            form.icon = 'fa-file-text-o'
            form.title = ''
            form.submit_label = 'Gerar Relatório'
            for field_name in list_filter:
                field = get_field(qs.model, field_name)
                if hasattr(field, 'choices') and field.choices:
                    form.fields[field_name] = forms.ChoiceField(
                        choices=[['', '']]+field.choices,
                        label=field.verbose_name,
                        required=False
                    )
                else:
                    form.fields[field_name] = forms.ModelChoiceField(
                        field.remote_field.model.objects.all(),
                        label=field.verbose_name,
                        required=False
                    )
            if form.is_valid():
                for field_name in list_filter:
                    value = form.cleaned_data[field_name]
                    if value:
                        qs = qs.filter(**{field_name : value})
                        self.filters.append((form.fields[field_name].label, value))
            self.form = form
        if distinct:
            pks = qs.values_list('pk', flat=True).order_by('pk').distinct()
            qs = qs.model.objects.filter(pk__in=pks)

        order_by = get_metadata(qs.model, 'order_by', iterable=True)
        if order_by:
            qs = qs.order_by(*order_by)
        table_description = get_metadata(qs.model, 'verbose_name_plural')
        self.table = ModelTable(request, table_description, qs, list_display)

    def count(self, vertical_key, horizontal_key=None, symbol=None, add_table=True, add_chart=False):
        statistics = self.qs.count(vertical_key, horizontal_key)
        statistics.title = 'Resumo'
        statistics.symbol = symbol
        if add_table:
            self.components.append(statistics.as_table(self.request))
        if add_chart:
            self.components.append(statistics.as_chart(self.request))

class MultiScheduleTable(Component):
    def __init__(self, data=(), request=None, title=None, icon=None, form_prefix=None):
        self.schedule_tables = []
        for shift, shift_data in data:
            self.schedule_tables.append(ScheduleTable(shift_data, request=request, title=shift, form_prefix=form_prefix))


class ScheduleTable(Component):
    WEEK_DAYS = DAY_NAMES

    def __init__(self, data=(), request=None, title=None, icon=None, form_prefix=None):
        super().__init__(title, request)
        self.title = title
        self.icon = icon
        self.rows = []
        self.form_prefix = form_prefix
        self.has_item = False

        if data:
            intervals, scheduled_times = data
            for interval in intervals:
                self.add_interval(str(interval))
            for scheduled_time in scheduled_times:
                self.add(*scheduled_time)

    def add_interval(self, interval):
        self.rows.append((str(interval), [], [], [], [], [], [], []))

    def add(self, week_day, interval, value='X', hint=None):
        week_day_index = None
        for i, wd in enumerate(ScheduleTable.WEEK_DAYS):
            if wd == week_day:
                week_day_index = i + 1
                break
        if week_day_index:
            for row in self.rows:
                if row[0] == str(interval):
                    row[week_day_index].append(value)
                    self.has_item = True
                    break


class ColorBox(Component):

    def __init__(self, color):
        super().__init__()
        self.color = color

