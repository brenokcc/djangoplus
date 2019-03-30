# -*- coding: utf-8 -*-

from djangoplus.utils.metadata import iterable
from djangoplus.utils.http import return_response
from django.utils.translation import ugettext as _
from django.http.response import HttpResponseRedirect
from djangoplus.utils import permissions, get_metadata


def view(verbose_name, icon=None, menu=None, login_required=True, style='ajax', template=None, shortcut=False,
         usecase=None, can_view=()):

    def decorate(func):
        url = '/{}/{}/'.format(func.__module__.split('.')[-2], func.__name__)

        def receive_function_args(request, *args, **kwargs):
            without_permission = can_view and not permissions.check_group_or_permission(request, can_view)
            without_authentication = login_required and not request.user.is_authenticated
            if without_permission or without_authentication:
                    return HttpResponseRedirect('/admin/login/?next={}'.format(url))
            f_return = func(request, *args, **kwargs)
            template_name = template or '{}.html'.format(func.__name__)
            return return_response(f_return, request, verbose_name, style, template_name)

        receive_function_args._view = dict(
            verbose_name=verbose_name, function=func, url=url, can_view=iterable(can_view), menu=menu, icon=icon,
            style=style, add_shortcut=shortcut, doc=func.__doc__, usecase=usecase
        )
        return receive_function_args

    return decorate


def action(model, verbose_name, help_text=None, condition=None, inline=False, subset=(), icon=None, category=None,
           style='ajax', message=_('Action successfully performed'), menu=None, can_execute=(),
           can_execute_by_organization=None, can_execute_by_unit=None, can_execute_by_role=None, usecase=None):

    def decorate(func):
        def receive_function_args(request, *args, **kwargs):
            if can_execute and not permissions.check_group_or_permission(
                    request, '{}.{}'.format(get_metadata(model, 'app_label'), func.__name__)):
                return HttpResponseRedirect('/admin/login/')
            f_return = func(request, *args, **kwargs)
            template_name = '{}.html'.format(func.__name__)
            return return_response(f_return, request, verbose_name, style, template_name)

        _action = dict(
            verbose_name=verbose_name, can_execute=iterable(can_execute), condition=condition, help_text=help_text,
            view_name=func.__name__, function=func, group=category, style=style, message=message, model=model,
            input=None, initial=None, choices=None, inline=inline, subsets=iterable(subset), icon=icon,
            doc=func.__doc__, usecase=usecase, can_execute_by_organization=iterable(can_execute_by_organization),
            can_execute_by_unit=iterable(can_execute_by_unit), can_execute_by_role=iterable(can_execute_by_role),
            redirect_to=None, menu=menu, display=None, source='view', expose=('web',)
        )

        receive_function_args._action = _action
        func._view_action = _action

        return receive_function_args

    return decorate


def dashboard(can_view=(), position='bottom'):
    def decorate(func):
        def receive_function_args(request, *args, **kwargs):
            return func(request, *args, **kwargs)
        receive_function_args._widget = dict(function=func, can_view=can_view, position=position)
        return receive_function_args
    return decorate
