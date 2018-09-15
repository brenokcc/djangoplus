# -*- coding: utf-8 -*-

from djangoplus import cache
from djangoplus.utils.metadata import set_metadata, iterable


def meta(verbose_name, help_text=None, formatter=None, dashboard=None, can_view=()):
    def decorate(func):
        set_metadata(func, 'type', 'attr')
        set_metadata(func, 'verbose_name', verbose_name)
        set_metadata(func, 'can_view', can_view)
        set_metadata(func, 'help_text', help_text)
        set_metadata(func, 'formatter', formatter)
        set_metadata(func, 'dashboard', dashboard)
        return func
    return decorate


def subset(title, help_text=None, list_display=(), list_filter=None, search_fields=None, template=None, menu=None,
           dashboard=None, inline=False, usecase=None, can_view=(), can_alert=(), can_notify=()):
    def decorate(function):
        set_metadata(function, 'type', 'subset')
        set_metadata(function, 'tab', True)
        set_metadata(function, 'title', title)
        set_metadata(function, 'alert', can_alert)
        set_metadata(function, 'notify', can_notify)
        set_metadata(function, 'menu', menu)
        set_metadata(function, 'help_text', help_text)
        set_metadata(function, 'usecase', usecase)
        set_metadata(function, 'can_view', iterable(can_view))
        set_metadata(function, 'inline', inline)
        set_metadata(function, 'name', function.__name__)
        set_metadata(function, 'order', cache.next_number())
        set_metadata(function, 'dashboard', dashboard)
        set_metadata(function, 'list_display', list_display)
        set_metadata(function, 'list_filter', list_filter)
        set_metadata(function, 'search_fields', search_fields)
        set_metadata(function, 'template', template)
        return function

    return decorate


def action(verbose_name, help_text=None, condition=None, inline=(), icon=None, category='Ações', style='popup',
           message='Ação realizada com sucesso.', redirect_to=None, menu=None, initial=None, choices=None, display=None,
           input=None, usecase=None, can_execute=(), can_execute_by_organization=None, can_execute_by_unit=None,
           can_execute_by_role=None):
    def decorate(function):
        function._action = dict(
            title=verbose_name, can_execute=iterable(can_execute), help_text=help_text,
            input=input, group=category or verbose_name, css=style, condition=condition, view_name=function.__name__,
            message=message, initial=initial or '{}_initial'.format(function.__name__), function=function,
            choices=choices or '{}_choices'.format(function.__name__), inline=iterable(inline), icon=icon,
            doc=function.__doc__, usecase=usecase, can_execute_by_organization=iterable(can_execute_by_organization),
            can_execute_by_unit=iterable(can_execute_by_unit), can_execute_by_role=iterable(can_execute_by_role),
            redirect_to=redirect_to, menu=menu, display=display, source='model'
        )
        return function

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
