# -*- coding: utf-8 -*-
import tempfile
import qrcode
import base64
from decimal import Decimal
from django.conf import settings
from djangoplus.ui import Component
from djangoplus.ui.components import forms
from django.utils.safestring import mark_safe
from djangoplus.utils.metadata import get_fiendly_name, get_field, get_metadata, getattr2


PERCENT_SYMBOL = '%'
DOLLAR_SYMBOL = '$'
REAIS_SYMBOL = 'R$'


class Chart(Component):
    def __init__(self, request, labels, series, groups=[], symbol=None, title=None):

        super(Chart, self).__init__(request)

        self.type = 'bar'
        self.labels = labels
        self.series = series
        self.groups = groups
        self.symbol = symbol or ''
        self.title = title
        self.color_index = 0

        for i, serie in enumerate(self.series):
            for j, valor in enumerate(serie):
                if type(valor) == Decimal:
                    self.series[i][j] = float(valor)

        self.colors = []
        for color in settings.GRADIENT:
            self.colors.append(color)
        for i in range(len(self.colors), 16):
            self.colors.append('#FFFFFF')

    def __str__(self):
        return self.render('chart.html')

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


class Timeline(Component):

    def __init__(self, request, description, items=[]):
        super(Timeline, self).__init__(request)
        self.items = items
        self.description = description
        self.width = 0

    def add(self, status, date):
        self.items.append((status, date))

    def __str__(self):
        self.width = str(100.0/len(self.items))
        return self.render('timeline.html')


class QrCode(Component):
    def __init__(self, request, text, width=200, height=200):
        self.text = text
        self.width = width
        self.base64 = None
        super(QrCode, self).__init__(request)

    def __str__(self):
        if self.as_pdf:
            qr = qrcode.QRCode()
            qr.add_data(self.text)
            image = qr.make_image()
            file_path = tempfile.mktemp()
            buffer = open(file_path, 'wb')
            image.save(buffer, format="JPEG")
            self.base64 = base64.b64encode(open(file_path, 'rb').read()).decode('utf-8')
        return self.render('qrcode.html')


class ProgressBar(Component):
    def __init__(self, request, percentual):
        self.percentual = percentual
        super(ProgressBar, self).__init__(request)

    def __str__(self):
        return self.render('progress_bar.html')


class Table(Component):
    def __init__(self, request, title, header=[], rows=[], footer=[], enumerable=True):
        super(Table, self).__init__(request)
        self.title = title
        self.header = header
        self.rows = rows
        self.footer = footer
        self.enumerable = enumerable

    def __str__(self):
        return self.render('table.html')


class ModelTable(Table):
    def __init__(self, request, title, qs, list_display=()):

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

        super(ModelTable, self).__init__(request, title, header, rows)


class StatisticsTable(Table):
    def __init__(self, request, title, queryset_statistics, symbol=None):
        if queryset_statistics.groups:
            header = []
            rows = []
            footer = []
            if queryset_statistics.series:
                for i, label in enumerate(queryset_statistics.labels):
                    row = [label]
                    for value in queryset_statistics.series[i]:
                        row.append(value)
                    if len(queryset_statistics.series) > 1:
                        row.append(queryset_statistics.xtotal[i])
                    rows.append(row)
                if len(queryset_statistics.series) > 1:
                    footer = [' '] + queryset_statistics.ytotal + [queryset_statistics.total()]
                    header = [' '] + queryset_statistics.groups + [' ']
                else:
                    header = [' '] + queryset_statistics.groups
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
        super(StatisticsTable, self).__init__(request, title, header, rows, footer, enumerable=False)
        self.queryset_statistics = queryset_statistics
        self.symbol = symbol

    def as_chart(self):
        if not self.queryset_statistics.groups:
            return Chart(self.request, self.queryset_statistics.labels, self.queryset_statistics.series, symbol=self.symbol, title=self.title).donut()
        else:
            chart = Chart(self.request, self.queryset_statistics.groups, self.queryset_statistics.series, self.queryset_statistics.labels, symbol=self.symbol, title=self.title)
            if self.queryset_statistics.labels and self.queryset_statistics.labels[0] == 'Jan':
                return chart.line()
            else:
                return chart.bar()


class ModelReport(Component):
    def __init__(self, request, title, qs, list_display=(), list_filter=(), distinct=False):
        super(ModelReport, self).__init__(request)
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
        component = StatisticsTable(self.request, 'Resumo', self.qs.count(vertical_key, horizontal_key), symbol)
        if add_table:
            self.components.append(component)
        if add_chart:
            self.components.append(component.as_chart())

    def __str__(self):
        return self.render('model_report.html')





