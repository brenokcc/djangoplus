# -*- coding: utf-8 -*-
import traceback
from django.apps import apps
from django.conf import settings
from django.shortcuts import render
from djangoplus.cache import loader
from django.http import HttpResponse
from djangoplus.ui import ComponentHasResponseException
from djangoplus.utils import permissions
from djangoplus.ui.components.panel import ModelPanel
from djangoplus.ui.components.navigation.breadcrumbs import httprr
from django.template import Template, Context
from djangoplus.ui.components.paginator import Paginator
from django.views.defaults import page_not_found, server_error
from django.core.exceptions import ValidationError
from django.http.response import HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType
from djangoplus.utils.metadata import list_related_objects, \
    is_many_to_many, is_one_to_one, get_metadata, check_condition, is_one_to_many, getattr2, is_one_to_many_reverse
from djangoplus.ui.components.forms import factory, DEFAULT_FORM_TITLE, DEFAULT_SUBMIT_LABEL


def listt(request, app, cls, subset=None):

    try:
        _model = apps.get_model(app, cls)
    except LookupError as e:
        return page_not_found(request, e, 'error404.html')
    title = get_metadata(_model, 'verbose_name_plural')
    subsetp = None
    list_display = None
    list_filter = None
    search_fields = None
    if subset:
        subset_func = getattr(_model.objects.get_queryset(), subset)
        can_view = subset_func._metadata['{}:can_view'.format(subset)]
        list_display = subset_func._metadata['{}:list_display'.format(subset)]
        list_filter = subset_func._metadata['{}:list_filter'.format(subset)]
        search_fields = subset_func._metadata['{}:search_fields'.format(subset)]
        title = '{} - {}'.format(title, subset_func._metadata['{}:title'.format(subset)])
    else:
        tid = request.GET.get('tid')
        subsetp = request.GET.get('tab{}'.format(tid))
        if tid and subsetp:
            subset_func = getattr(_model.objects.get_queryset(), subsetp)
            subset_title = subset_func._metadata['{}:title'.format(subsetp)]
            can_view = subset_func._metadata['{}:can_view'.format(subsetp)]
            title = '{} - {}'.format(title, subset_func._metadata['{}:title'.format(subsetp)])
            if not permissions.check_group_or_permission(request, can_view):
                return httprr(request, '/admin/login/?next={}'.format(request.get_full_path()))
        else:
            permission = '{}.list_{}'.format(app, cls)
            if not request.user.has_perm(permission):
                return httprr(request, '/admin/login/?next={}'.format(request.get_full_path()))

    qs = _model.objects.all(request.user)
    list_subsets = subset and [subset] or None

    paginator = Paginator(request, qs, title, list_subsets=list_subsets, is_list_view=True, list_display=list_display, list_filter=list_filter, search_fields=search_fields)
    paginator.process_request()



    paginator.add_actions()
    return render(request, 'default.html', locals())


def add(request, app, cls, pk=None, related_field_name=None, related_pk=None):

    if not request.user.is_authenticated:
        return httprr(request, '/admin/login/?next={}'.format(request.get_full_path()))

    try:
        _model = apps.get_model(app, cls)
    except LookupError as e:
        return page_not_found(request, e, 'error404.html')

    obj = pk and _model.objects.all(request.user).filter(pk=pk).first() or _model()
    obj.request = request
    obj._user = request.user

    title = pk and str(obj) or get_metadata(_model, 'verbose_name')

    if related_field_name is None:

        if obj.pk:
            if not permissions.has_edit_permission(request, _model) or not permissions.can_edit(request, obj):
                return HttpResponseForbidden()
        else:
            if not permissions.has_add_permission(request, _model) or not permissions.can_add(request, obj):
                return HttpResponseForbidden()

        form = factory.get_register_form(request, obj)
        title = form.title

    elif is_one_to_many(_model, related_field_name):
        if not permissions.can_add(request, obj) and not permissions.can_edit(request, obj):
            return HttpResponseForbidden()
        form = factory.get_one_to_many_form(request, obj, related_field_name)

    elif is_many_to_many(_model, related_field_name):
        if not permissions.can_edit_field(request, obj, related_field_name):
            return HttpResponseForbidden()
        form = factory.get_many_to_many_form(request, obj, related_field_name, related_pk)

    elif is_one_to_many_reverse(_model, related_field_name):
        form = factory.get_many_to_many_reverse_form(request, obj, related_field_name)

    elif is_one_to_one(_model, related_field_name):
        if not permissions.can_add(request, obj) and not permissions.can_edit(request, obj):
            return HttpResponseForbidden()
        form = factory.get_one_to_one_form(request, obj, related_field_name, related_pk)
    else:
        # many to one
        for rel in list_related_objects(_model):
            if hasattr(rel, 'get_accessor_name'):
                if rel.get_accessor_name() in ('{}_set'.format(related_field_name), related_field_name):
                    related_queryset = rel.related_model.objects.all(request.user)
                    related_obj = related_pk and related_queryset.get(pk=related_pk) or rel.related_model()
                    related_obj.request = request
                    setattr(related_obj, rel.field.name, obj)
                    setattr(related_obj, '{}_id'.format(rel.field.name), obj.pk)
                    if related_pk:
                        if not permissions.has_edit_permission(request, rel.related_model) or not permissions.can_edit(request, related_obj):
                            return HttpResponseForbidden()
                    else:
                        if not permissions.has_add_permission(request, rel.related_model) or not permissions.can_add(request, related_obj):
                            return HttpResponseForbidden()
                    form = factory.get_many_to_one_form(request, obj, rel.get_accessor_name(), related_obj)
                    title = form.title

    if form.is_valid():
        is_editing = form.instance.pk is not None
        try:
            form.save()
            obj = form.instance
            if 'select' in request.GET:
                return HttpResponse('{}|{}|{}'.format(obj.pk, obj, request.GET['select']));
            elif related_field_name:
                message = 'Ação realizada com sucesso'
                url = '..'
            else:
                message = get_metadata(form.instance.__class__, 'add_message')
                if message and not is_editing:
                    if hasattr(obj, 'get_absolute_url'):
                        url = obj.get_absolute_url()
                    else:
                        url = '/view/{}/{}/{}/'.format(get_metadata(obj.__class__, 'app_label'), obj.__class__.__name__.lower(), obj.pk)
                else:
                    url = '..'
                if is_editing:
                    message = message or 'Atualização realizada com sucesso'
                else:
                    message = message or 'Cadastro realizado com sucesso'
            return httprr(request, url, message)
        except ValidationError as e:
            form.add_error(None, str(e.message))
    return render(request, 'default.html', locals())


def view(request, app, cls, pk, tab=None):

    if not request.user.is_authenticated:
        return httprr(request, '/admin/login/?next={}'.format(request.get_full_path()))

    try:
        _model = apps.get_model(app, cls)
    except LookupError as e:
        return page_not_found(request, e, 'error404.html')

    obj = _model.objects.all(request.user).filter(pk=pk).first()
    obj.request = request
    obj._user = request.user

    if 'one_to_many_count' in request.GET:
        # TODO create a specific view for this purpose
        return HttpResponse(getattr2(obj, request.GET['one_to_many_count']))

    if not permissions.can_view(request, obj):
        return HttpResponseForbidden()

    title = str(obj)
    parent = request.GET.get('parent', None)
    printable = get_metadata(_model, 'pdf', False)
    panel = ModelPanel(request, obj, tab, parent, printable=printable)
    panel.process_request()

    if panel.message:
        return httprr(request, request.get_full_path(), panel.message)

    log_data = get_metadata(obj.__class__, 'log', False)
    if log_data and request.user.is_superuser and request.user.has_perm('admin.list_log'):
        url = '/log/{}/{}/'.format(app, cls)
        panel.drop_down.add_action('Visualizar Log', url, 'ajax', 'fa fa-history')

    return render(request, 'default.html', locals())


def action(request, app, cls, action_name, pk=None):

    try:
        _model = apps.get_model(app, cls)
    except LookupError as e:
        return page_not_found(request, e, 'error404.html')

    for group in loader.actions[_model]:
        if action_name in loader.actions[_model][group]:
            break

    form_action = loader.actions[_model][group][action_name]
    action_title = form_action['title']
    action_can_execute = form_action['can_execute']
    action_condition = form_action['condition']
    action_function = form_action['function']
    action_message = 'message' in form_action and form_action['message'] or None
    action_permission = '{}.{}'.format(_model._meta.app_label, action_function.__name__)
    action_input = form_action['input']
    action_display = form_action['display']
    action_style = form_action['css']
    action_redirect = form_action['redirect_to']

    obj = pk and _model.objects.all(request.user).distinct().get(pk=pk) or _model()
    obj.request = request
    obj._user = request.user
    title = action_title
    redirect_to = None

    if check_condition(action_condition, obj) and (not action_can_execute or permissions.check_group_or_permission(request, action_permission)):
        f_return = None
        func = getattr(_model, action_function.__name__, action_function)
        form = factory.get_action_form(request, obj, form_action)

        if func.__code__.co_argcount > 1 or action_input:
            if form.is_valid():
                if 'instance' in form.fields:
                    obj = form.cleaned_data['instance']
                func = getattr(obj, action_function.__name__, action_function)
                params = []
                for param in func.__code__.co_varnames[1:func.__code__.co_argcount]:
                    if param in form.cleaned_data:
                        params.append(form.cleaned_data[param])
                try:
                    f_return = func(*params)
                    if not action_redirect:
                        if func.__code__.co_argcount > 1 or action_display:
                            redirect_to = '..'
                        else:
                            redirect_to = '.'
                    else:
                        redirect_to = Template(action_redirect).render(Context({'self': obj}))
                except ValidationError as e:
                    form.add_error(None, str(e.message))
        else:
            try:
                if form.fields and form.is_valid() or not form.fields:
                    if 'instance' in form.fields:
                        obj = form.cleaned_data['instance']
                    func = getattr(obj, action_function.__name__, action_function)
                    f_return = func()
                    if not action_redirect:
                        if func.__code__.co_argcount > 1 or action_display:
                            redirect_to = '..'
                        else:
                            redirect_to = '.'
                    else:
                        redirect_to = Template(action_redirect).render(Context({'self': obj}))
            except ValidationError as e:
                if form.fields:
                    form.add_error(None, str(e.message))
                return httprr(request, '.', e.message, error=True)

        if f_return:
            if 'pdf' in action_style:
                request.GET._mutable = True
                request.GET['pdf'] = 1
                request.GET._mutable = False
                from datetime import datetime
                from djangoplus.admin.models import Settings
                from djangoplus.utils.http import PdfResponse
                from django.template.loader import render_to_string
                app_settings = Settings.default()
                f_return['logo'] = app_settings.logo_pdf and app_settings.logo_pdf or app_settings.logo
                f_return['project_name'] = app_settings.initials
                f_return['project_description'] = app_settings.name
                f_return['today'] = datetime.now()
                template_list = ['{}.html'.format(action_function.__name__), 'report.html']
                landscape = 'landscape' in action_style
                return PdfResponse(render_to_string(template_list, f_return, request=request), landscape=landscape)
        elif redirect_to:
            return httprr(request, redirect_to, action_message)

        if form.title == DEFAULT_FORM_TITLE:
            form.title = action_title
        if form.submit_label == DEFAULT_SUBMIT_LABEL:
            form.submit_label = action_title
        return render(request, 'default.html', locals())
    else:
        return HttpResponseForbidden()


def delete(request, app, cls, pk, related_field_name=None, related_pk=None):

    try:
        _model = apps.get_model(app, cls)
    except LookupError as e:
        return page_not_found(request, e, 'error404.html')

    obj = _model.objects.all(request.user).get(pk=pk)
    obj._request = request
    obj._user = request.user

    if permissions.can_delete(request, obj):
        if related_field_name:
            getattr(obj, related_field_name).remove(related_pk)
            return httprr(request, '..', 'Removido com sucesso')
        else:
            title = 'Excluir {}'.format(str(obj))
            form = factory.get_delete_form(request, obj)
            if form.is_valid():
                obj.delete()
                return httprr(request, '..', 'Exclusão realizada com sucesso.')
            return render(request, 'delete.html', locals())
    else:
        return HttpResponseForbidden()


def log(request, app, cls, pk=None):
    try:
        _model = apps.get_model(app, cls)
    except LookupError as e:
        return page_not_found(request, e, 'error404.html')

    if pk:
        obj = _model.objects.get(pk=pk)
        qs = obj.get_logs()
        title = 'Log - {}'.format(obj)
    else:
        content_type = ContentType.objects.get_for_model(_model)
        qs = content_type.log_set.all()
        title = 'Logs - {}'.format(get_metadata(_model, 'verbose_name_plural'))

    paginator = Paginator(request, qs, 'Log')
    return render(request, 'default.html', locals())


def dispatcher(request, app, view_name, params):

    params = params.split('/')[0:-1]

    full_app_name = settings.APP_MAPPING.get(app, app)
    fromlist = full_app_name.split('.')

    try:
        views = __import__('{}.views'.format(full_app_name), fromlist=list(map(str, fromlist)))
        func = getattr(views, view_name)
    except ComponentHasResponseException as e:
        raise e
    except (ImportError, TypeError, AttributeError) as e:
        traceback.print_exc()
        return page_not_found(request, e, 'error404.html')

    try:
        return func(request, *params)
    except ComponentHasResponseException as e:
        raise e
    except Exception as e:
        print(e)
        traceback.print_exc()
        #return server_error(request, 'error500.html')
        raise e


