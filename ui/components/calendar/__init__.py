import datetime

from djangoplus.ui import Component
from djangoplus.utils.metadata import get_metadata
from djangoplus.utils.serialization import dumps_qs_query


class Calendar(Component):
    def __init__(self, request, title):
        super(Calendar, self).__init__(request)
        self.title = title
        self.items = []
        self.id = hash(self)
        self.lazy = False
        self.default_date = datetime.date.today()
        session_default_date = request.session.get('calendar_default_date')
        if session_default_date:
            self.default_date = datetime.datetime.strptime(session_default_date, '%Y-%m-%d')

    def add(self, description, start, end=None, url=None, allday=True):
        item = dict(description=description, start=start, end=end, allday=allday)
        self.items.append(item)

    def __unicode__(self):
        return self.render('calendar.html')


class ModelCalendar(Calendar):
    def __init__(self, request, title, editable=False):
        super(ModelCalendar, self).__init__(request, title)
        self.links = []
        self.lazy = True
        self.editable = editable

    def add(self, queryset, start_field, end_field=None, color='', action_names=[]):
        item = dict(queryset=dumps_qs_query(queryset), start_field=start_field, end_field=end_field, color=color, action_names=','.join(action_names))
        self.items.append(item)
        label = get_metadata(queryset.model, 'verbose_name')
        app_label = get_metadata(queryset.model, 'app_label')
        model_name = queryset.model.__name__.lower()
        url = '/add/{}/{}/?{}='.format(app_label, model_name, start_field)
        link = dict(label=label, url=url)
        self.links.append(link)