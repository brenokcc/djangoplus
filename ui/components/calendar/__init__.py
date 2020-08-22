# -*- coding: utf-8 -*-

import datetime
from collections import OrderedDict
from djangoplus.ui.components import Component
from djangoplus.utils import normalyze
from djangoplus.utils.metadata import get_metadata
from djangoplus.utils.serialization import dumps_qs_query
from djangoplus.utils.permissions import has_add_permission
from djangoplus.utils.dateutils import add_days, DAY_INITIALS


class Calendar(Component):
    def __init__(self, request, title, url=None):
        super(Calendar, self).__init__(title, request)
        self.title = title
        self.items = []
        self.lazy = False
        self.initial_date = None
        self.url = url

        self.set_initial_date(datetime.date.today())

    def add(self, description, start, end=None, url=None, allday=True, color=None):
        item = dict(description=description, start=start, end=end, allday=allday, color=color)
        self.items.append(item)
    
    def set_initial_date(self, initial_date):
        self.initial_date = initial_date
        session_initial_date = self.request.session.get('calendar_initial_date')
        if session_initial_date:
            self.initial_date = datetime.datetime.strptime(session_initial_date, '%Y-%m-%d')


class AnnualCalendar(Component):

    formatter_name = 'annual_calendar'

    def __init__(self, data, title=None, compact=False):
        super().__init__()
        self.title = title
        self.compact = compact
        self.calendars = []
        self.items = []
        self.caption = OrderedDict()

        for values in data or []:
            self.add(*values)

    def add(self, description, start, end=None, color='#FFF', detail=None):
        item = dict(description=description, start=start, end=end, color=color, detail=detail)
        self.items.append(item)
        if color not in self.caption:
            self.caption[color] = description

    def __str__(self):
        today = datetime.date.today()
        header = DAY_INITIALS[0:-1]
        header.insert(0, DAY_INITIALS[-1])
        for i in range(1, 13):
            first_day = datetime.date(today.year, i, 1)
            calendar = [header]
            details = {}
            line = []
            date = first_day
            month = date.month
            weekday = date.weekday()
            weekday = weekday is not 6 and weekday + 1 or 0
            for day in range(0, weekday):
                line.append(('', '#FFF', '#777'))
            while date.month == month:
                weekday = date.weekday()
                weekday = weekday is not 6 and weekday + 1 or 0
                bgcolor = weekday in (0, 6) and '#EEE' or '#FFF'
                fcolor = '#777'
                for item in self.items:
                    add_detail = False
                    if item['start'] and item['end']:
                        if item['start'] <= date <= item['end']:
                            bgcolor = item['color']
                            fcolor = '#FFF'
                            add_detail = True
                    else:
                        if date == item['start']:
                            bgcolor = item['color']
                            fcolor = '#FFF'
                            add_detail = True
                    if item['detail'] and add_detail:
                        if item['detail'] not in details:
                            details[item['detail']] = []
                        details[item['detail']].append(date.day)
                line.append((date.day, bgcolor, fcolor))
                if weekday == 6:
                    calendar.append(line)
                    line = []
                date = add_days(date, 1)
            while len(line) < 7:
                line.append(('', '#FFF', '#777'))
            if len(calendar) < 6:
                calendar.append(line)
            visible = i in (today.month-1, today.month, today.month+1)
            self.calendars.append((normalyze(first_day.strftime('%B')), calendar, details, visible))
        return super().__str__()


class AnnualCompactCalendar(AnnualCalendar):
    template_name = 'annualcalendar.html'
    formatter_name = 'annual_compact_calendar'

    def __init__(self, items, title=None):
        super().__init__(items, title=title, compact=True)


class ModelCalendar(Calendar):
    def __init__(self, request, title, editable=False, display_time=True, url=None):
        super(ModelCalendar, self).__init__(request, title, url=url)
        self.links = []
        self.lazy = True
        self.models = []
        self.editable = editable
        self.display_time = display_time

    def add(self, queryset, start_field, end_field=None, color='#ccc', action_names=None, as_initial_date=False):
        if action_names is None:
            action_names = []
        item = dict(
            queryset=dumps_qs_query(queryset), start_field=start_field,
            end_field=end_field, color=color, action_names=','.join(action_names)
        )
        self.items.append(item)
        if as_initial_date:
            qs_initial_date = queryset.order_by(start_field).values_list(start_field, flat=True)
            if qs_initial_date.exists():
                self.set_initial_date(qs_initial_date[0])
        if queryset.model not in self.models and has_add_permission(self.request, queryset.model):
            label = get_metadata(queryset.model, 'verbose_name')
            app_label = get_metadata(queryset.model, 'app_label')
            model_name = queryset.model.__name__.lower()
            url = '/add/{}/{}/?{}='.format(app_label, model_name, start_field)
            link = dict(label=label, url=url)
            self.links.append(link)
            self.models.append(queryset.model)
