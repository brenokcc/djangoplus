# -*- coding: utf-8 -*-
import copy
import urllib
import json
from django.conf import settings
from django.db import transaction
from django.template import loader
from djangoplus.ui.components.forms.fields import *
from djangoplus.ui.components.forms import widgets
from django import forms as django_forms
from django.forms.forms import BoundField
from djangoplus.templatetags import mobile
from django.utils.html import conditional_escape
from djangoplus.utils.metadata import get_metadata, iterable
from django.db.models.fields import NOT_PROVIDED
ValidationError = django_forms.ValidationError
DEFAULT_FORM_TITLE = 'Formulário'
DEFAULT_SUBMIT_LABEL = 'Enviar'


class Form(django_forms.Form):

    fieldsets = None

    def __init__(self, request, *args, **kwargs):
        metaclass = hasattr(self.__class__, 'Meta') and self.__class__.Meta or None
        self.request = request
        self.method = kwargs.pop('method', None) or metaclass and hasattr(metaclass, 'method') and metaclass.method or 'post'
        self.horizontal = True
        self.id = self.__class__.__name__.lower()
        self.inline = kwargs.pop('inline', False)
        self.partial = kwargs.pop('partial', False)
        self.perm_or_group = ()
        self.str_hidden = ''
        self.inner_forms = []
        self.configured_fieldsets = []
        self.submit_label = DEFAULT_SUBMIT_LABEL
        self.title = DEFAULT_FORM_TITLE
        self.is_inner = False
        self.captcha = False

        if self.method.lower() == 'post':
            kwargs['data'] = request.POST or None
            kwargs['files'] = request.FILES or None
        else:
            kwargs['data'] = request.GET or None

        if request.GET.get('popup'):
            prefix = kwargs.get('prefix', '')
            prefix = 'popup{}'.format(prefix)
            kwargs.update(prefix=prefix)

        super(Form, self).__init__(*args, **kwargs)

        if hasattr(self, 'instance') and not self.fieldsets and not self.inline:
            self.fieldsets = copy.deepcopy(get_metadata(self._meta.model, 'fieldsets', ()))

        if metaclass:
            self.title = hasattr(metaclass, 'title') and metaclass.title or ''
            self.icon = hasattr(metaclass, 'icon') and metaclass.icon or ''
            self.note = hasattr(metaclass, 'note') and metaclass.note or ''
            self.is_inner = hasattr(metaclass, 'is_inner') and metaclass.is_inner or False
            self.horizontal = hasattr(metaclass, 'horizontal') and metaclass.horizontal or False
            self.perm_or_group = hasattr(metaclass, 'perm_or_group') and iterable(metaclass.perm_or_group) or self.perm_or_group
            self.captcha = hasattr(metaclass, 'captcha') and metaclass.captcha or False

            if hasattr(metaclass, 'submit_label'):
                self.submit_label = metaclass.submit_label
            elif hasattr(self, 'instance'):
                self.submit_label = self.instance.pk and 'Atualizar' or 'Cadastrar'

            self.submit_style = hasattr(metaclass, 'submit_style') and metaclass.submit_style or 'default'
            self.method = hasattr(metaclass, 'method') and metaclass.method or 'post'

        for field_name in self.fields:
            if self.method.lower() == 'post' and field_name in self.request.GET:
                # field.widget = django_forms.HiddenInput()
                self.initial[field_name] = self.request.GET[field_name]

    def contextualize(self):

        for field_name in self.fields:
            field = self.fields[field_name]
            if hasattr(field, 'queryset'):
                if type(field) == django_forms.ModelMultipleChoiceField:
                    field.widget = MultipleModelChoiceField(field.queryset)
                if type(field) == CurrentUserField:
                    field.queryset = field.queryset.filter(pk=self.request.user.pk)
                    self.initial[field_name] = self.request.user.pk

                # if it is a model form
                if hasattr(self, 'instance'):
                    obj = None
                    role_username = get_metadata(field.queryset.model, 'role_username')
                    if role_username and self.request.user.groups.filter(name=field.queryset.model._meta.verbose_name):
                        obj = field.queryset.model.objects.get(**{role_username: self.request.user.username})
                    for subclass in field.queryset.model.__subclasses__():
                        role_username = get_metadata(subclass, 'role_username')
                        if role_username and self.request.user.groups.filter(name=subclass._meta.verbose_name):
                            obj = subclass.objects.get(**{role_username: self.request.user.username})
                    if obj:
                        groups = self.request.user.find_groups(self.perm_or_group, get_metadata(obj.__class__, 'verbose_name'))
                        # if the user is not superuser or there is only one group that allows the user to register the object
                        if not self.request.user.is_superuser and not groups.exists():
                            field.widget = widgets.HiddenInput(attrs={'value': obj.pk})
                            # field.widget = widgets.DisplayInput(obj)
                            continue

                if self.request.user.is_authenticated and (not hasattr(field, 'ignore_lookup') or not field.ignore_lookup):
                    if not self.is_inner:
                        field.queryset = field.queryset.all(self.request.user, obj=hasattr(self, 'instance') and self.instance or None)

                if True:#hasattr(field.queryset.model._meta, 'organization_lookup') or hasattr(field.queryset.model,'organization_ptr'):
                    from djangoplus.admin.models import Organization
                    if issubclass(field.queryset.model, Organization) and field.queryset.count() == 1:
                        if not isinstance(field, MultipleModelChoiceField):
                            obj = field.queryset[0]
                            field.widget = widgets.HiddenInput(attrs={'value': obj.pk})
                            # field.widget = widgets.DisplayInput(obj)

                if True:# hasattr(field.queryset.model._meta, 'unit_lookup') or hasattr(field.queryset.model, 'unit_ptr'):
                    from djangoplus.admin.models import Unit
                    if issubclass(field.queryset.model, Unit):
                        if not isinstance(field, MultipleModelChoiceField) and field.queryset.count() == 1:
                            obj = field.queryset[0]
                            field.widget = widgets.DisplayInput(obj)

                if hasattr(field.widget, 'lazy') and mobile(self.request):
                    field.widget.lazy = False

            if type(self.fields[field_name]) in [ModelChoiceField, MultipleModelChoiceField]:
                self.fields[field_name].widget.user = self.request.user

    def configure(self):

        from djangoplus.ui.components.forms import factory

        hidden_fields = []

        one_to_one_fields = dict()
        one_to_many_fields = dict()
        for name in list(self.fields.keys()):
            field = self.fields[name]
            if type(field) == OneToOneField:
                one_to_one_fields[name] = field
                del (self.fields[name])
            elif type(field) == OneToManyField:
                one_to_many_fields[name] = field
                del (self.fields[name])

        if not self.fieldsets:
            fields = list(self.fields.keys()) + list(one_to_one_fields.keys()) + list(one_to_many_fields.keys())
            if self.inline:
                self.fieldsets = (('', {'fields': (fields, )}),)
            else:
                self.fieldsets = (('', {'fields': fields}),)

        fieldset_field_names = []
        extra_fieldset_field_names = []
        for title, fieldset in self.fieldsets:
            field_names = fieldset.get('fields', ())
            relation_names = fieldset.get('relations', ())
            for name_or_tuple in tuple(field_names) + tuple(relation_names):
                for name in iterable(name_or_tuple):
                    fieldset_field_names.append(name)
        for field_name in list(self.fields.keys()):
            if field_name not in fieldset_field_names:
                extra_fieldset_field_names.append(field_name)
        if extra_fieldset_field_names:
            self.fieldsets += ('Outros', {'fields': extra_fieldset_field_names, }),

        for title, fieldset in self.fieldsets:
            title = '::' in title and title.split('::')[1] or title.split('::')[0]
            field_names = fieldset.get('fields', ())
            relation_names = fieldset.get('relations', ())

            configured_fieldset = dict(title=title, tuples=[], one_to_one=[], one_to_many=[])

            for name_or_tuple in tuple(field_names) + tuple(relation_names):
                fields = []
                for name in iterable(name_or_tuple):
                    if name in self.fields:
                        field = self.fields[name]
                        bf = BoundField(self, field, name)
                        if bf.is_hidden:
                            hidden_fields.append(bf)
                        else:
                            if bf.label:
                                label = conditional_escape(str(bf.label))
                                if self.label_suffix:
                                    if label[-1] not in ':?.!':
                                        label += self.label_suffix
                                label = label or ''
                            else:
                                label = ''

                            help_text = field.help_text or ''
                            label = str(label)[0:-1]
                            label = field.required and '{}<span class="text-danger">*</span>'.format(label) or label

                            d = dict(name=name, request=self.request, label=label, widget=bf,
                                     help_text=help_text)
                            fields.append(d)

                    elif name in one_to_one_fields:
                        field = one_to_one_fields[name]
                        one_to_one_id = getattr(self.instance, '{}_id'.format(name))
                        form = factory.get_one_to_one_form(self.request, self.instance, name, one_to_one_id,
                                                           partial=True, prefix=name)
                        required = field.required or form.data.get(form.prefix, None)
                        save = form.data.get(form.prefix, None)
                        if not required:
                            for field_name in form.fields:
                                form.fields[field_name].required = False
                        configured_fieldset['one_to_one'].append((field, form, required, save))
                        self.inner_forms.append(form)
                    elif name in one_to_many_fields:
                        field = one_to_many_fields[name]
                        one_to_many_forms = []

                        if self.instance.pk:
                            qs = getattr(self.instance, name).all()
                        else:
                            qs = field.queryset.filter(pk=0)
                        count = qs.count()
                        for i in range(0, field.one_to_many_max):
                            instance = i < count and qs[i] or None
                            form = factory.get_one_to_many_form(self.request, self.instance, name, partial=True,
                                                                inline=True, prefix='{}{}'.format(name, i),
                                                                instance=instance)
                            form.id = '{}-{}'.format(name, i)
                            form.hidden = i > count or field.one_to_many_count
                            required = form.data.get(form.prefix, None)
                            if not required:
                                for field_name in form.fields:
                                    form.fields[field_name].required = False
                            one_to_many_forms.append(form)
                            self.inner_forms.append(form)
                        one_to_many_count = None
                        if field.one_to_many_count:
                            if type(field.one_to_many_count) is int:
                                one_to_many_count = field.one_to_many_count
                            else:
                                app_label = get_metadata(qs.model, 'app_label')
                                if '__' in field.one_to_many_count:
                                    tokens = field.one_to_many_count.split('__')
                                    model_name = self.fields[tokens[0]].queryset.model.__name__.lower()
                                    model_lookup = '__'.join(tokens[1:])
                                    one_to_many_count = '{}:/view/{}/{}/PK/?one_to_many_count={}'.format(
                                        tokens[0], app_label, model_name, model_lookup)
                                else:
                                    one_to_many_count = field.one_to_many_count
                        configured_fieldset['one_to_many'].append((name, field, one_to_many_forms, one_to_many_count))

                if len(fields) > 2 or mobile(self.request):
                    self.horizontal = False

                configured_fieldset['tuples'].append(fields)

            self.configured_fieldsets.append(configured_fieldset)
        self.str_hidden = ''.join([str(x) for x in hidden_fields])

    def clean(self, *args, **kwargs):
        if self.request.POST and 'g-recaptcha-response' in self.request.POST:
            captcha_response = self.request.POST.get('g-recaptcha-response')
            captcha_url = 'https://www.google.com/recaptcha/api/siteverify'
            captcha_secret = settings.CAPTCHA_SECRET
            if captcha_response:
                if not self.is_inner:
                    data = dict(secret=captcha_secret, response=captcha_response)
                    response = json.loads(urllib.request.urlopen(captcha_url, urllib.parse.urlencode(data).encode('utf-8')).read().decode('utf-8'))
                    print(response)
                    if not response.get('success'):
                        raise ValidationError('Confirme que você não é um robô.')
            else:
                raise ValidationError('Confirme que você não é um robô.')
        return super(Form, self).clean(*args, **kwargs)

    def is_valid(self, *args, **kwargs):
        self.contextualize()
        self.configure()
        valid = super(Form, self).is_valid(*args, **kwargs)
        for form in self.inner_forms:
            valid = form.is_valid(*args, **kwargs) and valid or False
        return valid

    def has_errors(self):
        if self.errors:
            return True
        for form in self.inner_forms:
            if form.errors:
                return True
        return False

    def __str__(self):
        if self.inline:
            for field_name in self.fields:
                self.fields[field_name].widget.attrs['placeholder'] = self.fields[field_name].label
                self.fields[field_name].widget.attrs['data-placeholder'] = self.fields[field_name].label
        return loader.render_to_string('form.html', {'self': self}, request=self.request)


class ModelForm(Form, django_forms.ModelForm):

    def save(self, *args, **kwargs):
        setattr(self.instance, 'request', self.request)
        for model_field in get_metadata(self.instance, 'fields'):
            # Se para o campo em questão foi definido um valor default. Ex: BooleanField(default=True)
            if model_field.default != NOT_PROVIDED:
                value = model_field.default
                if callable(value):
                    value = value()
                # Se não há nenhum valor no atributo da instância em questão, então será adotado
                # o valor default definido pelo desenvolvedor.
                if getattr(self.instance, model_field.name) is None:
                    setattr(self.instance, model_field.name, value)

        kwargs.update(commit=False)

        if len(self.inner_forms):
            with transaction.atomic():
                sid = transaction.savepoint()
                instance = super(ModelForm, self).save(*args, **kwargs)
                instance._post_save_form = self
                try:
                    instance.save()
                    sid and transaction.savepoint_commit(sid)
                except ValidationError as e:
                    sid and transaction.savepoint_rollback(sid)
                    raise e
        else:
            instance = super(ModelForm, self).save(*args, **kwargs)
            instance._post_save_form = self
            instance.save()

        return instance

    def save_121_and_12m(self):
        for fieldset in self.configured_fieldsets:
            for field, form, required, save in fieldset.get('one_to_one', ()):
                if save:
                    form.save()
                elif form.instance.pk:
                    form.instance.delete()

            for name, field, one_to_many_forms, one_to_many_count in fieldset.get('one_to_many', ()):
                for form in one_to_many_forms:
                    if form.data.get(form.prefix, None):
                        form.save()
                    else:
                        if form.instance.pk:
                            form.instance.delete()

class ModelFormOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', ())
        self.exclude = getattr(options, 'exclude', None)
        self.widgets = getattr(options, 'widgets', None)
        self.localized_fields = getattr(options, 'localized_fields', None)
        self.labels = getattr(options, 'labels', None)
        self.help_texts = getattr(options, 'help_texts', None)
        self.error_messages = getattr(options, 'error_messages', None)
