# -*- coding: utf-8 -*-
from django.shortcuts import render
from djangoplus.utils import permissions
from djangoplus.utils.http import PdfResponse
from django.template.loader import render_to_string
from django.http.response import HttpResponseRedirect
from djangoplus.utils.metadata import iterable


def view(verbose_name, icon=None, menu=None, login_required=True, style='ajax', template=None, shortcut=False,
         usecase=None, can_view=()):

    def decorate(function):
        url = '/{}/{}/'.format(function.__module__.split('.')[-2], function.__name__)

        def receive_function_args(request, *args, **kwargs):
            without_permission = can_view and not permissions.check_group_or_permission(request, can_view)
            without_authentication = login_required and not request.user.is_authenticated
            if without_permission or without_authentication:
                    return HttpResponseRedirect('/admin/login/?next={}'.format(url))
            f_return = function(request, *args, **kwargs)
            if 'title' not in f_return:
                f_return['title'] = verbose_name
            if type(f_return) == dict:
                for key in f_return:
                    if hasattr(f_return[key], 'process_request'):
                        f_return[key].process_request()
                if 'pdf' in style:
                    request.GET._mutable = True
                    request.GET['pdf'] = 1
                    request.GET._mutable = False
                    from datetime import datetime
                    from djangoplus.admin.models import Settings
                    app_settings = Settings.default()
                    f_return['logo'] = app_settings.logo_pdf and app_settings.logo_pdf or app_settings.logo
                    f_return['project_name'] = app_settings.initials
                    f_return['project_description'] = app_settings.name
                    f_return['today'] = datetime.now()
                    template_list = ['{}.html'.format(function.__name__), 'report.html']
                    landscape = 'landscape' in style
                    return PdfResponse(render_to_string(template_list, f_return, request=request), landscape=landscape)
                else:
                    template_list = [template or '{}.html'.format(function.__name__), 'default.html']
                    return render(request, template_list, f_return)
            return f_return

        receive_function_args._view = dict(title=verbose_name, function=function, url=url, can_view=iterable(can_view), menu=menu, icon=icon,
                              style=style, add_shortcut=shortcut, doc=function.__doc__, usecase=usecase)
        return receive_function_args

    return decorate


def action(model, verbose_name, help_text=None, condition=None, inline=(), icon=None, category='Ações', style='ajax',
           message='Ação realizada com sucesso.', menu=None, can_execute=(),
           can_execute_by_organization=None, can_execute_by_unit=None, can_execute_by_role=None, usecase=None):

    def decorate(function):
        def receive_function_args(request, *args, **kwargs):
            if can_execute and not permissions.check_group_or_permission(
                    request, '{}.{}'.format(model._meta.app_label, function.__name__)):
                return HttpResponseRedirect('/admin/login/')
            f_return = function(request, *args, **kwargs)
            if 'title' not in f_return:
                f_return['title'] = verbose_name
            if type(f_return) == dict:
                if 'pdf' in style:
                    request.GET._mutable = True
                    request.GET['pdf'] = 1
                    request.GET._mutable = False
                    from datetime import datetime
                    from djangoplus.admin.models import Settings
                    app_settings = Settings.default()
                    f_return['logo'] = app_settings.logo_pdf and app_settings.logo_pdf or app_settings.logo
                    f_return['project_name'] = app_settings.initials
                    f_return['project_description'] = app_settings.name
                    f_return['today'] = datetime.now()
                    template_list = ['{}.html'.format(function.__name__), 'report.html']
                    landscape = 'landscape' in style
                    return PdfResponse(render_to_string(template_list, f_return, request=request), landscape=landscape)
                else:
                    template_list = ['{}.html'.format(function.__name__), 'default.html']
                    return render(request, template_list, f_return)
            else:
                return f_return

        d = dict(title=verbose_name, can_execute=iterable(can_execute), condition=condition, help_text=help_text,
                 view_name=function.__name__, function=function, group=category, css=style, message=message, model=model, input=None,
                 initial=None, choices=None, inline=iterable(inline), icon=icon, doc=function.__doc__, usecase=usecase,
                 can_execute_by_organization=iterable(can_execute_by_organization), can_execute_by_unit=iterable(can_execute_by_unit),
                 can_execute_by_role=iterable(can_execute_by_role), redirect_to=None, menu=menu, display=None, source='view')

        receive_function_args._action = d
        function._view_action = d

        return receive_function_args

    return decorate


def dashboard(can_view=(), position='bottom'):
    def decorate(function):
        def receive_function_args(request, *args, **kwargs):
            return function(request, *args, **kwargs)
        receive_function_args._widget = dict(function=function, can_view=can_view, position=position)
        return receive_function_args
    return decorate
