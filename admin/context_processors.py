# -*- coding: utf-8 -*-
import sys
from djangoplus import test
from django.conf import settings
from djangoplus.cache import CACHE
from djangoplus.utils import permissions
from djangoplus.admin.models import Settings
from djangoplus.mail.utils import should_display
from djangoplus.utils.metadata import get_metadata
from djangoplus.ui.components.utils import RoleSelector
from djangoplus.ui.components.navigation.menu import Menu


def context_processor(request):
    executing_tests = 'test' in sys.argv
    app_settings = Settings.default()
    alerts = []
    menu = None

    if request.user.is_authenticated:
        menu = Menu(request, app_settings)

        for model in CACHE['SUBSETS']:
            icon = get_metadata(model, 'icon', 'fa-warning')
            title = get_metadata(model, 'verbose_name_plural')
            app_label = get_metadata(model, 'app_label')
            model_name = model.__name__.lower()
            for item in CACHE['SUBSETS'][model]:
                can_view = item['can_view']
                alert = item['alert']
                if alert and permissions.check_group_or_permission(request, can_view):
                    attr_name = item['function'].__func__.__name__
                    qs = model.objects.all(request.user)
                    qs = getattr(qs, attr_name)()
                    count = qs.count()
                    if count:
                        url = '/list/{}/{}/{}/'.format(app_label, model_name, attr_name)
                        description = item['verbose_name'].replace(title, '')
                        item = dict(title=title, description=description, count=count, url=url, icon=icon)
                        alerts.append(item)

    return dict(
        debug=settings.DEBUG,
        role_selector=RoleSelector(request),
        username_mask=settings.USERNAME_MASK,
        js_files=settings.EXTRA_JS,
        css_files=settings.EXTRA_CSS,
        settings=app_settings,
        menu=menu,
        alerts=alerts,
        display_emails=settings.DEBUG and not executing_tests and should_display(),
        display_fake_mouse=test.CACHE['RECORD'],
        executing_tests=executing_tests,
        default_template='default.html'
    )
