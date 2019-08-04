# -*- coding: utf-8 -*-


from django.utils.translation import ugettext as _
from djangoplus.utils.metadata import set_metadata, iterable


def meta(verbose_name, help_text=None, formatter=None, dashboard=None, can_view=(), expose=True, icon=None):
    def decorate(func):
        set_metadata(func, 'type', 'attr')
        set_metadata(func, 'verbose_name', verbose_name)
        set_metadata(func, 'can_view', can_view)
        set_metadata(func, 'help_text', help_text)
        set_metadata(func, 'formatter', formatter)
        set_metadata(func, 'dashboard', dashboard)
        set_metadata(func, 'icon', icon)
        set_metadata(func, 'expose', iterable(expose))
        return func
    return decorate


def subset(verbose_name, help_text=None, list_display=(), list_filter=None, search_fields=None, template=None, menu=None,
           dashboard=None, usecase=None, can_view=(), can_alert=(), can_notify=(), expose=True):
    def decorate(func):
        from djangoplus import next_number
        set_metadata(func, 'type', 'subset')
        set_metadata(func, 'tab', True)
        set_metadata(func, 'verbose_name', verbose_name)
        set_metadata(func, 'alert', can_alert)
        set_metadata(func, 'notify', can_notify)
        set_metadata(func, 'menu', menu)
        set_metadata(func, 'help_text', help_text)
        set_metadata(func, 'usecase', usecase)
        set_metadata(func, 'can_view', iterable(can_view))
        set_metadata(func, 'name', func.__name__)
        set_metadata(func, 'order', next_number())
        set_metadata(func, 'dashboard', dashboard)
        set_metadata(func, 'list_display', list_display)
        set_metadata(func, 'list_filter', list_filter)
        set_metadata(func, 'search_fields', search_fields)
        set_metadata(func, 'template', template)
        set_metadata(func, 'formatter', None)
        set_metadata(func, 'expose', iterable(expose))
        return func

    return decorate


def action(verbose_name, help_text=None, condition=None, inline=False, subset=(), icon=None, category=None,
           style='popup', message=_('Action successfully performed.'), redirect_to=None, menu=None, initial=None,
           choices=None, display=None, input=None, usecase=None, can_execute=(), can_execute_by_organization=None,
           can_execute_by_unit=None, can_execute_by_role=None, expose=True):
    def decorate(func):
        func._action = dict(
            verbose_name=verbose_name, can_execute=iterable(can_execute), help_text=help_text,
            input=input, group=category or verbose_name, style=style, condition=condition, view_name=func.__name__,
            message=message, initial=initial or '{}_initial'.format(func.__name__), function=func,
            choices=choices or '{}_choices'.format(func.__name__), inline=inline, subsets=iterable(subset), icon=icon,
            doc=func.__doc__, usecase=usecase, can_execute_by_organization=iterable(can_execute_by_organization),
            can_execute_by_unit=iterable(can_execute_by_unit), can_execute_by_role=iterable(can_execute_by_role),
            redirect_to=redirect_to, menu=menu, display=display, source='model', expose=iterable(expose)
        )
        return func

    return decorate


def role(username, email=None, name=None, active=None, scope=None, signup=False, notify=False):
    def decorate(cls):
        metaclass = getattr(cls, '_meta')
        metaclass.role_username = username
        metaclass.role_email = email
        metaclass.role_name = name
        metaclass.role_active = active
        metaclass.role_scope = scope
        metaclass.role_signup = signup
        metaclass.role_notify = notify
        return cls
    return decorate
