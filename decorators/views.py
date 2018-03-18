# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render
from djangoplus.utils import permissions
from djangoplus.utils.http import PdfResponse
from django.template.loader import render_to_string
from django.http.response import HttpResponseRedirect
from djangoplus.utils.metadata import iterable


def view(title, can_view=None, icon=None, menu=None, login_required=True, style='ajax', template=None, add_shortcut=False, sequence=0):

    def decorate(function):
        url = '/{}/{}/'.format(function.__module__.split('.')[-2], function.func_name)

        def receive_function_args(request, *args, **kwargs):
            without_permission = can_view and not permissions.check_group_or_permission(request, can_view)
            without_authentication = login_required and not request.user.is_authenticated()
            if without_permission or without_authentication:
                    return HttpResponseRedirect('/admin/login/?next={}'.format(url))
            f_return = function(request, *args, **kwargs)
            if 'title' not in f_return:
                f_return['title'] = title
            if type(f_return) == dict:
                if 'pdf' in style:
                    from datetime import datetime
                    from djangoplus.admin.models import Settings
                    app_settings = Settings.default()
                    f_return['logo'] = app_settings.logo_pdf and app_settings.logo_pdf or app_settings.logo
                    f_return['project_name'] = app_settings.initials
                    f_return['project_description'] = app_settings.name
                    f_return['today'] = datetime.now()
                    template_list = ['{}.html'.format(function.func_name), 'report.html']
                    return PdfResponse(render_to_string(template_list, f_return, request=request))
                else:
                    template_list = [template or '{}.html'.format(function.func_name), 'default.html']
                    return render(request, template_list, f_return)
            return f_return

        receive_function_args._view = dict(title=title, function=function, url=url, can_view=iterable(can_view), menu=menu, icon=icon,
                              style=style, add_shortcut=add_shortcut, doc=function.__doc__, sequence=sequence)
        return receive_function_args

    return decorate


def dashboard(can_view=(), position='bottom'):
    def decorate(function):
        def receive_function_args(request, *args, **kwargs):
            return function(request, *args, **kwargs)
        receive_function_args._widget = dict(function=function, can_view=can_view, position=position)
        return receive_function_args
    return decorate


def action(model, title, can_execute=(), condition=None, category='Ações',
           style='ajax', message='Ação realizada com sucesso.', template=None, inline=False, icon=None, sequence=0,
           can_execute_by_organization=None, can_execute_by_unit=None, can_execute_by_role=None, redirect_to=None):

    def decorate(function):
        def receive_function_args(request, *args, **kwargs):
            if can_execute and not permissions.check_group_or_permission(request, '{}.{}'.format(model._meta.app_label, function.func_name)):
                return HttpResponseRedirect('/admin/login/')
            f_return = function(request, *args, **kwargs)
            if 'title' not in f_return:
                f_return['title'] = title
            if type(f_return) == dict:
                if 'pdf' in style:
                    from datetime import datetime
                    from djangoplus.admin.models import Settings
                    app_settings = Settings.default()
                    f_return['logo'] = app_settings.logo_pdf and app_settings.logo_pdf or app_settings.logo
                    f_return['project_name'] = app_settings.initials
                    f_return['project_description'] = app_settings.name
                    f_return['today'] = datetime.now()
                    template_list = ['{}.html'.format(function.func_name), 'report.html']
                    return PdfResponse(render_to_string(template_list, f_return, request=request))
                else:
                    template_list = ['{}.html'.format(function.func_name), 'default.html']
                    return render(request, template or template_list, f_return)

            else:
                return f_return

        d = dict(title=title, can_execute=iterable(can_execute), condition=condition,
                 view_name=function.__name__, function=function, group=category, css=style, message=message, model=model, input=None,
                 initial=None, choices=None, inline=inline, icon=icon, doc=function.__doc__, sequence=sequence,
                 can_execute_by_organization=iterable(can_execute_by_organization), can_execute_by_unit=iterable(can_execute_by_unit),
                 can_execute_by_role=iterable(can_execute_by_role), redirect_to=redirect_to, menu=None)

        receive_function_args._action = d

        return receive_function_args

    return decorate
