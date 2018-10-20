# -*- coding: utf-8 -*-
import sys
from django.conf import settings
from djangoplus.test import cache
from djangoplus.cache import loader
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

        for model in loader.subsets:
            icon = get_metadata(model, 'icon', 'fa-warning')
            title = get_metadata(model, 'verbose_name_plural')
            app_label = get_metadata(model, 'app_label')
            model_name = model.__name__.lower()
            for item in loader.subsets[model]:
                can_view = item['can_view']
                alert = item['alert']
                if alert and permissions.check_group_or_permission(request, can_view):
                    attr_name = item['function'].__func__.__name__
                    qs = model.objects.all(request.user)
                    qs = getattr(qs, attr_name)()
                    count = qs.count()
                    if count:
                        url = '/list/{}/{}/{}/'.format(app_label, model_name, attr_name)
                        description = item['title'].replace(title, '')
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
        display_emails=False,  # not executing_tests and should_display(),
        display_fake_mouse=cache.RECORD,
        executing_tests=executing_tests
    )
