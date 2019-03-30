# -*- coding: utf-8 -*-
from djangoplus.ui.components import forms
from djangoplus.ui.components.utils import ScheduleTable


class ScheduleTableForm(forms.Form):
    values = forms.CharField(label='Values', widget=forms.widgets.HiddenInput())

    def __init__(self, *args, **kwargs):
        intervals = kwargs.get('initial', {}).pop('intervals', [])
        values = kwargs.get('initial', {}).pop('values', [])
        kwargs['initial']['values'] = ''

        super().__init__(*args, **kwargs)
        self.component = ScheduleTable(self.request, 'Horários')
        self.component.form_prefix = self.prefix and '{}-'.format(self.prefix) or ''

        for interval in intervals:
            self.component.add_interval(interval)
        for week_day, interval in values:
            self.component.add(week_day, interval)

    def clean_values(self):
        values = self.cleaned_data['values']
        cleaned_values = []
        if values:
            for value in values.split('|'):
                i, interval = value.split('::')
                cleaned_values.append((ScheduleTable.WEEK_DAYS[int(i)-1], interval))
        return cleaned_values
