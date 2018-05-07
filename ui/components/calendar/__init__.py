import datetime

from djangoplus.utils.permissions import has_add_permission

from djangoplus.ui import RequestComponent
from djangoplus.utils.metadata import get_metadata
from djangoplus.utils.serialization import dumps_qs_query


class Calendar(RequestComponent):
    def __init__(self, request, title, url=None):
        super(Calendar, self).__init__(title, request)
        self.title = title
        self.items = []
        self.lazy = False
        self.initial_date = None
        self.url = url

        self.set_initial_date(datetime.date.today())

    def add(self, description, start, end=None, url=None, allday=True):
        item = dict(description=description, start=start, end=end, allday=allday)
        self.items.append(item)
    
    def set_initial_date(self, initial_date):
        self.initial_date = initial_date
        session_initial_date = self.request.session.get('calendar_initial_date')
        if session_initial_date:
            self.initial_date = datetime.datetime.strptime(session_initial_date, '%Y-%m-%d')


class ModelCalendar(Calendar):
    def __init__(self, request, title, editable=False, display_time=True, url=None):
        super(ModelCalendar, self).__init__(request, title, url=url)
        self.links = []
        self.lazy = True
        self.models = []
        self.editable = editable
        self.display_time = display_time

    def add(self, queryset, start_field, end_field=None, color='#ccc', action_names=[], as_initial_date=False):
        item = dict(queryset=dumps_qs_query(queryset), start_field=start_field, end_field=end_field, color=color, action_names=','.join(action_names))
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