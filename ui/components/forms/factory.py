# -*- coding: utf-8 -*-

from django.conf import settings
from djangoplus.ui.components import forms
from django.apps import apps
from djangoplus.utils.metadata import get_metadata, find_field_by_name, list_related_objects, get_fiendly_name, getattr2


def get_register_form(request, obj):

    _model = type(obj)

    initial = hasattr(obj, 'initial') and obj.initial() or {}
    choices = hasattr(obj, 'choices') and obj.choices() or {}

    form_name = get_metadata(_model, 'add_form')
    app_label = get_metadata(_model, 'app_label')
    verbose_name = get_metadata(_model, 'verbose_name')
    role_username = get_metadata(_model, 'role_username', None)

    if form_name:
        full_app_name = settings.APP_MAPPING.get(app_label, app_label)
        forms_module = __import__('{}.forms'.format(full_app_name), fromlist=list(map(str, [app_label])))
        Form = getattr(forms_module, form_name)
    else:
        if obj.pk:
            form_title = 'Atualização de {}'.format(str(verbose_name))
            button_label = 'Atualizar'
        else:
            add_label = get_metadata(_model, 'add_label', None)
            form_title = add_label or 'Cadastro de {}'.format(str(verbose_name))
            button_label = add_label or 'Cadastrar'

        class Form(forms.ModelForm):
            class Meta:
                model = _model
                fields = get_metadata(_model, 'form_fields', '__all__')
                exclude = get_metadata(_model, 'exclude_fields', ())
                submit_label = button_label
                title = form_title
                icon = get_metadata(_model, 'icon', None)
                perm_or_group = '{}.add_{}'.format(app_label, _model.__name__.lower())

    form = Form(request, instance=obj, initial=initial)
    form.name = '{}Form'.format(_model.__name__)
    for field_name in choices:
        form.fields[field_name].queryset = choices[field_name]
        form.fields[field_name].widget.queryset = choices[field_name]

    if hasattr(obj, 'get_parent_field'):
        parent_field = obj.get_parent_field()
        if parent_field:
            if not obj.pk and parent_field.name in form.fields:
                form.fields[parent_field.name].widget = forms.widgets.HiddenInput()

    if role_username and obj.pk:
        if role_username in form.fields:
            form.fields[role_username].widget = forms.widgets.ReadOnlyInput()

    return form


def get_one_to_many_form(request, obj, related_field_name, **kwargs):
    _model = type(obj)
    related_field = find_field_by_name(_model, related_field_name)

    class Form(forms.ModelForm):
        class Meta:
            model = related_field.remote_field.model
            fields = get_metadata(related_field.remote_field.model, 'form_fields', '__all__')
            exclude = get_metadata(related_field.remote_field.model, 'exclude_fields', ())
            submit_label = 'Adicionar {}'.format(get_metadata(related_field.remote_field.model, 'verbose_name'))
            title = 'Adicionar {}'.format(get_metadata(related_field.remote_field.model, 'verbose_name'))
            icon = get_metadata(related_field.remote_field.model, 'icon', None)
            is_inner = True

        def save(self, *args, **kwargs):
            super(Form, self).save(*args, **kwargs)
            getattr(obj, related_field_name).add(self.instance)

    form = Form(request, **kwargs)
    return form


def get_many_to_one_form(request, obj, related_field_name, related_obj):
    _model = type(obj)
    rel = getattr(_model, related_field_name.split(':')[0]).rel
    add_label = get_metadata(rel.related_model, 'add_label')
    if add_label:
        form_title = add_label
        button_label = add_label
    else:
        action = related_obj.pk and 'Atualizar' or 'Adicionar'
        form_title = '{} {}'.format(action, get_metadata(rel.related_model, 'verbose_name'))
        button_label = action
    related_field_name = rel.field.name

    setattr(related_obj, related_field_name, obj)

    initial = hasattr(related_obj, 'initial') and related_obj.initial() or {}
    choices = hasattr(related_obj, 'choices') and related_obj.choices() or {}

    app_label = get_metadata(_model, 'app_label')

    form_name = get_metadata(rel.related_model, 'add_form')
    if form_name:
        full_app_name = settings.APP_MAPPING.get(app_label, app_label)
        forms_module = __import__('{}.forms'.format(full_app_name), fromlist=list(map(str, [app_label])))
        Form = getattr(forms_module, form_name)
    else:
        class Form(forms.ModelForm):
            class Meta:
                model = rel.related_model
                fields = get_metadata(rel.related_model, 'form_fields', '__all__')
                exclude = get_metadata(rel.related_model, 'exclude_fields', ())
                submit_label = related_obj.pk and 'Atualizar' or button_label
                title = form_title
                is_inner = True

    initial[related_field_name] = obj.pk
    for key in list(initial.keys()):
        if hasattr(obj, key) and obj.pk and getattr(obj, key):
            del (initial[key])

    form = Form(request, initial=initial, instance=related_obj)
    form.form_name = '{}Form'.format(rel.related_model.__name__)
    for field_name in choices:
        if field_name in form.fields:
            form.fields[field_name].queryset = choices[field_name]
    if related_field_name in form.fields:
        del (form.fields[related_field_name])
    return form


def get_one_to_one_form(request, obj, related_field_name, related_pk, **kwargs):
    _model = type(obj)

    related_field = find_field_by_name(_model, related_field_name)
    related_object = related_pk and related_field.remote_field.model.objects.get(pk=related_pk)

    initial = hasattr(related_field.remote_field.model, 'initial') and related_field.remote_field.model.initial() or {}
    choices = hasattr(related_field.remote_field.model, 'choices') and related_field.remote_field.model.choices() or {}

    class Form(forms.ModelForm):
        class Meta:
            model = related_field.remote_field.model
            fields = get_metadata(related_field.remote_field.model, 'form_fields', '__all__')
            exclude = get_metadata(related_field.remote_field.model, 'exclude_fields', ())
            submit_label = 'Atualizar {}'.format(related_field.verbose_name)
            title = 'Atualizar {}'.format(related_field.verbose_name)
            icon = get_metadata(related_field.remote_field.model, 'icon', None)
            is_inner = True

        def save(self, *args, **kwargs):
            super(Form, self).save(*args, **kwargs)
            setattr(obj, related_field_name, self.instance)
            _model.objects.filter(pk=obj.pk).update(**{related_field_name: self.instance})

    form = Form(request, instance=related_object, initial=initial, **kwargs)
    form.name = '{}Form'.format(related_field.remote_field.model.__name__)
    for field_name in choices:
        if field_name in form.fields:
            form.fields[field_name].queryset = choices[field_name]
    return form


def get_many_to_many_form(request, obj, related_field_name, related_pk):
    _model = type(obj)

    initial = hasattr(obj, 'initial') and obj.initial() or {}
    choices = hasattr(obj, 'choices') and obj.choices() or {}

    related_field_model = find_field_by_name(_model, related_field_name).remote_field.model

    class Form(forms.ModelForm):
        related_objects = forms.MultipleModelChoiceField(related_field_model.objects.all(),
                                                         label=get_metadata(related_field_model, 'verbose_name'))

        class Meta:
            model = _model
            fields = ()
            title = 'Adicionar {}'.format(get_metadata(related_field_model, 'verbose_name'))
            icon = get_metadata(related_field_model, 'icon', None)
            # is_inner = True

        def save(self, *args, **kwargs):
            for related_object in self.cleaned_data['related_objects']:
                getattr(self.instance, related_field_name).add(related_object)

    form = Form(request, instance=obj, initial=initial)
    form.name = '{}Form'.format(_model.__name__)
    for field_name in choices:
        if field_name in form.fields:
            form.fields[field_name].queryset = choices[field_name]
    return form


def get_many_to_many_reverse_form(request, obj, related_field_name):
    _model = type(obj)

    initial = hasattr(obj, 'initial') and obj.initial() or {}
    choices = hasattr(obj, 'choices') and obj.choices() or {}
    field = getattr(_model, '{}_set'.format(related_field_name))
    related_field_model = field.rel.remote_field.model

    class Form(forms.ModelForm):
        related_objects = forms.MultipleModelChoiceField(related_field_model.objects.all(),
                                                         label=get_metadata(related_field_model, 'verbose_name'))

        class Meta:
            model = _model
            fields = ()
            title = 'Adicionar {}'.format(get_metadata(related_field_model, 'verbose_name'))
            icon = get_metadata(related_field_model, 'icon', None)
            # is_inner = True

        def save(self, *args, **kwargs):
            for related_object in self.cleaned_data['related_objects']:
                getattr(related_object, field.rel.remote_field.name).add(self.instance)
            self.instance._check_role()

    form = Form(request, instance=obj, initial=initial)
    form.name = '{}Form'.format(_model.__name__)
    for field_name in choices:
        if field_name in form.fields:
            form.fields[field_name].queryset = choices[field_name]
    return form


def get_class_action_form(request, _model, action, func):
    action_title = action['title']
    initial = action['initial']
    action_input = action['input']
    app_label = get_metadata(_model, 'app_label')

    if action_input:
        # it is a form name
        if type(action_input) in [str, str] and '.' not in action_input:
            full_app_name = settings.APP_MAPPING.get(app_label, app_label)
            module = __import__('{}.forms'.format(full_app_name), fromlist=list(map(str, [app_label])))
            Form = getattr(module, action_input)
        # it is a model or model name
        else:
            if type(action_input) in [str, str]:
                app_name, class_name = action_input.split('.')
                action_input = apps.get_model(app_name, class_name)

            class Form(forms.ModelForm):
                class Meta:
                    model = action_input
                    fields = func.__code__.co_varnames[1:func.__code__.co_argcount]
                    title = action_title
                    submit_label = action_title
    else:
        class Form(forms.ModelForm):
            class Meta:
                model = _model
                fields = func.__code__.co_varnames[1:func.__code__.co_argcount]
                title = action_title
                submit_label = action_title

    initial = hasattr(_model.objects, initial) and getattr(_model.objects, initial)() or None
    form = Form(request, initial=initial)
    return form


def get_action_form(request, obj, action):
    action_function = action['function']
    action_title = action['title']
    initial = action['initial']
    action_input = action['input']
    action_choices = action['choices']
    action_display = action['display']
    app_label = get_metadata(type(obj), 'app_label')
    func = getattr(obj, action_function.__name__, action_function)

    if initial and hasattr(obj, initial):
        initial = getattr(obj, initial)()
    else:
        initial = {}
    if action_choices and hasattr(obj, action_choices):
        action_choices = getattr(obj, action_choices)()
    else:
        action_choices = {}

    if action_input:
        # it is a form name
        if type(action_input) in [str, str] and '.' not in action_input:
            full_app_name = settings.APP_MAPPING.get(app_label, app_label)
            fromlist = app_label
            module = __import__('{}.forms'.format(full_app_name), fromlist=list(map(str, [app_label])))
            form_cls = getattr(module, action_input)

        # it is a model or model name
        else:
            if type(action_input) in [str, str]:
                app_name, class_name = action_input.split('.')
                action_input = apps.get_model(app_name, class_name)

            class Form(forms.ModelForm):
                class Meta:
                    model = action_input
                    fields = func.__code__.co_varnames[1:func.__code__.co_argcount]
                    title = action_title
                    submit_label = action_title

            form_cls = Form
    else:

        class Form(forms.ModelForm):
            class Meta:
                model = func.__self__.__class__
                fields = func.__code__.co_varnames[1:func.__code__.co_argcount]
                title = action_title
                submit_label = action_title

        form_cls = Form

    if issubclass(form_cls, forms.ModelForm):
        for key in list(initial.keys()):
            if hasattr(obj, key) and obj.pk and getattr(obj, key):
                del (initial[key])
        form = form_cls(request, instance=obj, initial=initial)
    else:
        form = form_cls(request, initial=initial)

    if action_display:
        for lookup in action_display:
            label = get_fiendly_name(func.__self__.__class__, lookup)
            value = getattr2(obj, lookup)
            form.fields[lookup] = forms.CharField(label=label, initial=value, required=False, widget=forms.widgets.DisplayInput(value))

    if action_choices:
        for field_name in action_choices:
            form.fields[field_name].queryset = action_choices[field_name]

    if not obj.pk:
        verbose_name = get_metadata(obj.__class__, 'verbose_name')
        form.fields['instance'] = forms.ModelChoiceField(type(obj).objects.all(), label=verbose_name)
        if form.fieldsets:
            form.fieldsets = ((verbose_name, {'fields': ('instance',)}),) + form.fieldsets

    return form


def get_delete_form(request, obj):
    class Form(forms.Form):
        class Meta:
            submit_label = 'Confirmar Exclusão'
            submit_style = 'danger'

        def __init__(self, *args, **kwargs):
            super(Form, self).__init__(*args, **kwargs)
            self.related_objects = []
            for related_object in list_related_objects(type(obj)):
                try:
                    qs = getattr(obj, related_object.get_accessor_name()).all()
                except:
                    continue
                verbose_name = get_metadata(qs.model, 'verbose_name_plural')
                count = qs.count()
                if count:
                    self.related_objects.append(dict(verbose_name=verbose_name, count=count))

    form = Form(request)
    return form
