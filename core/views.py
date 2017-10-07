# -*- coding: utf-8 -*-
import traceback, copy
from django.apps import apps
from django.conf import settings
from django.shortcuts import render
from djangoplus.cache import loader
from django.http import HttpResponse
from djangoplus.utils import permissions
from djangoplus.ui.components.panel import ModelPanel
from djangoplus.ui.components.breadcrumbs import httprr
from django.template import Template, Context
from djangoplus.ui.components.paginator import Paginator
from djangoplus.utils.http import ReportResponse
from django.views.defaults import page_not_found
from django.core.exceptions import ValidationError
from django.http.response import HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType
from djangoplus.utils.metadata import list_related_objects, \
    is_many_to_many, is_one_to_one, get_metadata, check_condition, is_one_to_many
from djangoplus.ui.components.forms import factory, DEFAULT_FORM_TITLE, DEFAULT_SUBMIT_LABEL, ModelChoiceField


def listt(request, app, cls, subset=None):

    try:
        _model = apps.get_model(app, cls)
    except LookupError:
        return page_not_found(request)
    subsetp = None
    if subset:
        subset_func = getattr(_model.objects.all(), subset)
        can_view = subset_func._metadata['%s:can_view' % subset]
    else:
        tid = request.GET.get('tid')
        subsetp = request.GET.get('tab%s' % tid)
        if tid and subsetp:
            subset_func = getattr(_model.objects.get_queryset(), subsetp)
            can_view = subset_func._metadata['%s:can_view' % subsetp]
            if not permissions.check_group_or_permission(request, can_view):
                return httprr(request, '/admin/login/?next=%s' % request.get_full_path())
        else:
            permission = '%s.list_%s' % (app, cls)
            if not request.user.has_perm(permission):
                return httprr(request, '/admin/login/?next=%s' % request.get_full_path())

    qs = _model.objects.all(request.user)
    list_subsets = subset and [subset] or None
    if subset:
        title = getattr(getattr(qs, subset), '_metadata')['%s:title' % subset]

    else:
        title = u'%s' % get_metadata(_model, 'verbose_name_plural')

    paginator = Paginator(request, qs, title, list_subsets=list_subsets, is_list_view=True)
    response = paginator.get_response()
    if response:
        return response

    if _model in loader.class_actions:
        for group in loader.class_actions[_model]:
            for view_name in loader.class_actions[_model][group]:
                _action = loader.class_actions[_model][group][view_name]
                action_title = _action['title']
                action_message = _action['message']
                action_can_execute = _action['can_execute']
                action_input = _action['input']
                action_css = _action['css']
                action_condition = _action['condition']
                initial = _action['initial']
                choices = _action['choices']

                if subsetp:
                    if subsetp not in loader.subset_actions[_model] or view_name not in loader.subset_actions[_model][subsetp]:
                        continue
                else:
                    if subset not in loader.subset_actions[_model] or view_name not in loader.subset_actions[_model][subset]:
                        continue

                if permissions.check_group_or_permission(request, action_can_execute):
                    func = hasattr(qs, view_name) and getattr(qs, view_name) or None
                    if func:

                        char = '?' in request.get_full_path() and '&' or '?'
                        url = '%s%s%s' % (request.get_full_path(), char, '%s=' % view_name)

                        has_input = func.func_code.co_argcount > 1

                        if not has_input:
                            action_css = action_css.replace('popup', '')
                        paginator.add_subset_action(action_title, url, action_css, None, action_condition)

                        if view_name in request.GET:
                            ids = paginator.get_selected_ids()
                            if ids:
                                qs = paginator.get_queryset(paginate=False).filter(id__in=ids)
                            else:
                                qs = paginator.get_queryset(paginate=False)

                            func = getattr(qs, view_name)
                            redirect_url = None

                            if has_input:
                                form = factory.get_class_action_form(request, _model, _action, func)
                                paginator = ''
                                if form.is_valid():
                                    params = []
                                    for param in func.func_code.co_varnames[1:func.func_code.co_argcount]:
                                        if param in form.cleaned_data:
                                            params.append(form.cleaned_data[param])
                                    try:
                                        f_return = func(*params)
                                        redirect_url = '..'
                                    except ValidationError, e:
                                        form.add_error(None, unicode(e.message))
                                if not redirect_url:
                                    return render(request, 'default.html', locals())
                            else:
                                f_return = func()
                                redirect_url = '.'

                            if redirect_url:
                                request.GET._mutable = True
                                del request.GET['ids']
                                del request.GET[view_name]
                                request.GET._mutable = False
                            return httprr(request, redirect_url, action_message)
                    else:
                        url = '/%s/%s/' % (app, view_name)
                        if view_name in request.GET:
                            return httprr(request, url)
                        else:
                            action_css = action_css.replace('popup', '')
                            paginator.add_action(action_title, url, action_css, None)

    paginator.add_actions()

    return render(request, 'default.html', locals())


def add(request, app, cls, pk=None, related_field_name=None, related_pk=None):

    if not request.user.is_authenticated():
        return httprr(request, '/admin/login/?next=%s' % request.get_full_path())

    try:
        _model = apps.get_model(app, cls)
    except LookupError:
        return page_not_found(request)

    obj = pk and _model.objects.all(request.user).get(pk=pk) or _model()
    obj.request = request

    title = pk and unicode(obj) or get_metadata(_model, 'verbose_name')

    if not related_field_name:

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
        if not permissions.can_add(request, obj) and not permissions.can_edit(request, obj):
            return HttpResponseForbidden()
        form = factory.get_many_to_many_form(request, obj, related_field_name, related_pk)

    elif is_one_to_one(_model, related_field_name):
        if not permissions.can_add(request, obj) and not permissions.can_edit(request, obj):
            return HttpResponseForbidden()
        form = factory.get_one_to_one_form(request, obj, related_field_name, related_pk)
    else:
        # many to one
        for related_object in list_related_objects(_model):
            if hasattr(related_object, 'get_accessor_name'):
                if related_object.get_accessor_name() in ('%s_set' % related_field_name, related_field_name):
                    related_queryset = related_object.related_model.objects.all(request.user)
                    related_obj = related_pk and related_queryset.get(pk=related_pk) or related_object.related_model()
                    related_obj.request = request
                    setattr(related_obj, related_object.field.name, obj)
                    setattr(related_obj, '%s_id' % related_object.field.name, obj.pk)
                    if related_pk:
                        if not permissions.has_edit_permission(request, related_object.related_model) or not permissions.can_edit(request, related_obj):
                            return HttpResponseForbidden()
                    else:
                        if not permissions.has_add_permission(request, related_object.related_model) or not permissions.can_add(request, related_obj):
                            return HttpResponseForbidden()
                    form = factory.get_many_to_one_form(request, obj, related_object, related_obj)
                    title = form.title

    if form.is_valid():
        is_editing = form.instance.pk is not None
        try:
            form.save()
            obj = form.instance
            if 'select' in request.GET:
                return HttpResponse(u'%s|%s|%s' % (obj.pk, obj, request.GET['select']));
            elif related_field_name:
                message = u'Ação realizada com sucesso'
                url = '..'
            else:
                message = get_metadata(form.instance.__class__, 'add_message')
                if message and not is_editing:
                    if hasattr(obj, 'get_absolute_url'):
                        url = obj.get_absolute_url()
                    else:
                        url = '/view/%s/%s/%s/' % (get_metadata(obj.__class__, 'app_label'), obj.__class__.__name__.lower(), obj.pk)
                else:
                    url = '..'
                if is_editing:
                    message = message or u'Atualização realizada com sucesso'
                else:
                    message = message or u'Cadastro realizado com sucesso'
            return httprr(request, url, message)
        except ValidationError, e:
            form.add_error(None, unicode(e.message))
    return render(request, 'default.html', locals())


def view(request, app, cls, pk, tab=None):

    if not request.user.is_authenticated():
        return httprr(request, '/admin/login/?next=%s'%request.get_full_path())

    try:
        _model = apps.get_model(app, cls)
    except LookupError:
        return page_not_found(request)

    qs = _model.objects.all(request.user)

    obj = qs.get(pk=pk)
    obj.request = request
    obj._user = request.user

    if not permissions.can_view(request, obj):
        return HttpResponseForbidden()

    title = unicode(obj)
    parent = request.GET.get('parent', None)
    panel = ModelPanel(request, obj, tab, parent)

    if request.GET.get('pdf', False):
        return ReportResponse(title, request, [panel])
    elif panel.message:
        return httprr(request, request.get_full_path(), panel.message)

    log_data = get_metadata(obj.__class__, 'log', False)
    if log_data and request.user.is_superuser and request.user.has_perm('admin.list_log'):
        url = '/log/%s/%s/' % (app, cls)
        panel.drop_down.add_action(u'Visualizar Log', url, 'ajax', 'fa fa-history')

    return render(request, 'default.html', locals())


def action(request, app, cls, action_name, pk=None):

    try:
        _model = apps.get_model(app, cls)
    except LookupError:
        return page_not_found(request)

    for group in loader.actions[_model]:
        if action_name in loader.actions[_model][group]:
            break

    form_action = loader.actions[_model][group][action_name]
    action_title = form_action['title']
    action_can_execute = form_action['can_execute']
    action_condition = form_action['condition']
    action_function = form_action['function']
    action_message = 'message' in form_action and form_action['message'] or None
    action_permission = '%s.%s' % (_model._meta.app_label, action_function.func_name)
    action_input = form_action['input']
    redirect_to = form_action['redirect_to']

    obj = pk and _model.objects.all(request.user).get(pk=pk) or _model()
    obj.request = request
    obj._user = request.user
    title = action_title

    if check_condition(action_condition, obj) and (not action_can_execute or permissions.check_group_or_permission(request, action_permission)):

        func = getattr(_model, action_function.func_name, action_function)
        form = factory.get_action_form(request, obj, form_action)

        if func.func_code.co_argcount > 1 or action_input:
            if form.is_valid():
                if 'instance' in form.fields:
                    obj = form.cleaned_data['instance']
                func = getattr(obj, action_function.func_name, action_function)
                params = []
                for param in func.func_code.co_varnames[1:func.func_code.co_argcount]:
                    if param in form.cleaned_data:
                        params.append(form.cleaned_data[param])
                try:
                    f_return = func(*params)
                    if not redirect_to:
                        if func.func_code.co_argcount > 1:
                            return httprr(request, '..', action_message)
                        else:
                            return httprr(request, '.', action_message)
                    else:
                        return httprr(request, Template(redirect_to).render(Context({'self': obj})), action_message)
                except ValidationError, e:
                    form.add_error(None, unicode(e.message))
        else:
            try:
                if form.fields and form.is_valid() or not form.fields:
                    if form.fields:
                        obj = form.cleaned_data['instance']
                    func = getattr(obj, action_function.func_name, action_function)
                    f_return = func()
                    if not redirect_to:
                        if func.func_code.co_argcount > 1:
                            return httprr(request, '..', action_message)
                        else:
                            return httprr(request, '.', action_message)
                    else:
                        return httprr(request, Template(redirect_to).render(Context({'self': obj})), action_message)
            except ValidationError, e:
                return httprr(request, '.', unicode(e.message))

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
    except LookupError:
        return page_not_found(request)

    obj = _model.objects.all(request.user).get(pk=pk)
    obj.request = request

    permission_name = '%s.delete_%s' % (app, cls)
    if permissions.can_delete(request, obj) and permissions.check_group_or_permission(request, permission_name):

        if related_field_name:
            getattr(obj, related_field_name).remove(related_pk)
            return httprr(request, '..', u'Removido com sucesso')
        else:
            title = u'Excluir %s' % unicode(obj)
            form = factory.get_delete_form(request, obj)
            if form.is_valid():
                obj.delete()
                return httprr(request, '..', u'Exclusão realizada com sucesso.')

            return render(request, 'delete.html', locals())

    else:
        return HttpResponseForbidden()


def log(request, app, cls, pk=None):
    try:
        _model = apps.get_model(app, cls)
    except LookupError:
        return page_not_found(request)

    if pk:
        obj = _model.objects.get(pk=pk)
        qs = obj.get_logs()
        title = u'Log - %s' % obj
    else:
        content_type = ContentType.objects.get_for_model(_model)
        qs = content_type.log_set.all()
        title = u'Logs - %s' % get_metadata(_model, 'verbose_name_plural')

    paginator = Paginator(request, qs, 'Log')
    return render(request, 'default.html', locals())


def dispatcher(request, path=None):
    if path == 'favicon.ico':
        return HttpResponse()

    tokens = path.split('/')
    try:
        app_label, view_name, params = tokens[0], tokens[1], tokens[2:-1]
    except:
        return page_not_found(request)

    full_app_name = settings.APP_MAPPING.get(app_label, app_label)
    fromlist = full_app_name.split('.')

    try:
        views = __import__('%s.views' % full_app_name, fromlist=fromlist)
        if hasattr(views, view_name):
            func = getattr(views, view_name)
        else:
            return page_not_found(request)
    except ImportError:
        traceback.print_exc()
        return page_not_found(request)

    return func(request, *params)


