# -*- coding: utf-8 -*-
import tempfile
import qrcode
import base64
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from djangoplus.ui.components import forms
from djangoplus.utils.http import ComponentResponse
from djangoplus.ui import RequestComponent, ComponentHasResponseException
from djangoplus.utils.metadata import get_fiendly_name, get_field, get_metadata, getattr2


PERCENT_SYMBOL = '%'
DOLLAR_SYMBOL = '$'
REAIS_SYMBOL = 'R$'


class Chart(RequestComponent):
    def __init__(self, request, labels, series, groups=[], symbol=None, title=None):

        super(Chart, self).__init__(None, request)

        self.type = 'bar'
        self.labels = labels
        self.series = series
        self.groups = groups
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

    def __init__(self, request, queryset_statistics):

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

        symbol = queryset_statistics.symbol
        title = queryset_statistics.title

        super(QueryStatisticsChart, self).__init__(request, labels, series, groups, symbol, title)

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


class Timeline(RequestComponent):

    class Media:
        css = {'all': ('/static/css/timeline.css',)}

    def __init__(self, request, description, items=[]):
        super(Timeline, self).__init__(description, request)
        self.items = items
        self.description = description
        self.width = 0

    def add(self, status, date):
        self.items.append((status, date))

    def __str__(self):
        self.width = str(100.0/len(self.items))
        return self.render('timeline.html')


class RoleSelector(RequestComponent):

    def __init__(self, request):
        super(RoleSelector, self).__init__('roleselector', request)
        self.groups = []
        self.process_request()
        self._load()

    def _load(self):
        if self.request.user.is_authenticated:
            from djangoplus.admin.models import Group, Role
            pks = self.request.user.role_set.values_list('group', flat=True).distinct()
            for group in Group.objects.filter(pk__in=pks).distinct():
                group.roles = Role.objects.filter(group=group, user=self.request.user).distinct()
                group.scopes = group.roles.filter(scope__isnull=False).count()
                self.groups.append(group)

    def process_request(self):
        if 'data[]' in self.request.GET:
            pks = []
            for value in self.request.GET.getlist('data[]'):
                if value.strip():
                    pks.append(value)
            self.request.user.role_set.update(active=False)
            self.request.user.role_set.filter(pk__in=pks).update(active=True)
            self.request.user.check_role_groups()
            raise ComponentHasResponseException(HttpResponse())


class QrCode(RequestComponent):
    def __init__(self, request, text, width=200, height=200):
        super(QrCode, self).__init__(text, request)
        self.text = text
        self.width = width
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


class ProgressBar(RequestComponent):
    def __init__(self, request, percentual):
        self.percentual = percentual
        super(ProgressBar, self).__init__(percentual, request)


class Table(RequestComponent):
    def __init__(self, request, title, header=list(), rows=list(), footer=list(), enumerable=True, note=None):
        super(Table, self).__init__(title, request)
        self.title = title
        self.header = header
        self.rows = rows
        self.footer = footer
        self.enumerable = enumerable
        self.note = note


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
    def __init__(self, request, queryset_statistics):
        if queryset_statistics.groups:
            header = []
            rows = []
            footer = []
            if queryset_statistics.series:
                for i, group in enumerate(queryset_statistics.groups):
                    row = [group]
                    for value in queryset_statistics.series[i]:
                        row.append(value)
                    if len(queryset_statistics.series) > 1:
                        row.append(queryset_statistics.xtotal[i])
                    rows.append(row)
                if len(queryset_statistics.series) > 1:
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
        title = queryset_statistics.title
        super(QueryStatisticsTable, self).__init__(request, title, header, rows, footer, enumerable=False)
        self.queryset_statistics = queryset_statistics
        self.symbol = queryset_statistics.symbol


class ModelReport(RequestComponent):
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
                    form.fields[field_name] = forms.ChoiceField(choices=[['', '']]+field.choices, label=field.verbose_name, required=False)
                else:
                    form.fields[field_name] = forms.ModelChoiceField(field.remote_field.model.objects.all(), label=field.verbose_name, required=False)
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
