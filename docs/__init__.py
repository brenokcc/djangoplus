# -*- coding: utf-8 -*-

import json
import requests
from django.apps import apps
from django.conf import settings
from djangoplus.docs import utils
from django.utils import translation
from django.utils.translation import ugettext as _
from djangoplus.utils import get_metadata, get_parameters_names, get_field, get_parameters_details
from djangoplus.ui.components import forms


class Documentation(object):

    def __init__(self):
        from djangoplus.cache import loader
        from djangoplus.docs.usecase import Actor, UseCase
        from djangoplus.docs.diagrams import Workflow, ClassDiagram

        translation.activate(settings.LANGUAGE_CODE)

        self.description = None
        self.workflow = None
        self.actors = []
        self.usecases = []
        self.class_diagrams = []

        # load description
        for app_config in apps.get_app_configs():
            if app_config.label == settings.PROJECT_NAME:
                self.description = app_config.module.__doc__ and app_config.module.__doc__.strip() or None

        # load actors
        self.organization_model = loader.organization_model
        self.unit_model = loader.unit_model

        for model in loader.role_models:
            name = loader.role_models[model]['name']
            scope = loader.role_models[model]['scope']
            description = utils.extract_documentation(model)
            self.actors.append(Actor(name=name, scope=scope, description=description))

        # load usecases
        self.workflow = Workflow()
        for task in self.workflow.tasks:
            if not task.startswith(_('Access')):
                usecase = UseCase(task)
                self.usecases.append(usecase)

        # load class diagrams
        for class_diagram_name, models in list(loader.class_diagrams.items()):
            class_diagram = ClassDiagram(class_diagram_name, models)
            self.class_diagrams.append(class_diagram)

    def as_dict(self):
        return dict(description=self.description, actors=[actor.as_dict() for actor in self.actors],
                    usecases=[usecase.as_dict() for usecase in self.usecases],
                    class_diagrams=[class_diagram.as_json() for class_diagram in self.class_diagrams],
                    organization_model=self.organization_model, unit_model=self.unit_model)

    def as_json(self):
        return json.dumps(self.as_dict())


class ApiDocumentation(object):

    def __init__(self):
        self.title = 'Index'
        self.index = []
        self.endpoints = []

    def load_models(self):
        from djangoplus.cache import loader
        for model in loader.api_models:
            app_label = get_metadata(model, 'app_label')
            verbose_name_plural = get_metadata(model, 'verbose_name_plural')
            model_name = model.__name__.lower()
            url = '/docs/api/{}/{}/'.format(app_label, model_name)
            self.index.append((verbose_name_plural, url))

    def load_model(self, app_label, model_name, endpoint_name):
        from djangoplus.cache import loader
        model = apps.get_model(app_label, model_name)
        self.title = get_metadata(model, 'verbose_name')

        name = 'list'
        url = '/api/{}/{}/'.format(app_label, model_name)
        doc_url = '/docs/api/{}/{}/{}/'.format(app_label, model_name, name)
        query_params = [
            dict(verbose_name='Page', name='page', type='Integer', required=False, help_text=None)
        ]
        self.add_endpoint(name, url, 'get', doc_url, query_params, [])

        name = 'get'
        url = '/api/{}/{}/{{}}/'.format(app_label, model_name)
        doc_url = '/docs/api/{}/{}/{}/'.format(app_label, model_name, name)
        self.add_endpoint(name, url, 'get', doc_url, [], [])

        for group in loader.instance_actions[model]:
            for func_name in loader.instance_actions[model][group]:
                action = loader.instance_actions[model][group][func_name]
                url = '/api/{}/{}/{{}}/{}/'.format(app_label, model_name, func_name)
                doc_url = '/docs/api/{}/{}/{}/'.format(app_label, model_name, func_name)
                func = getattr(model(), func_name)
                input_params = get_parameters_details(model, func, action['input'])
                self.add_endpoint(func_name, url, 'post', doc_url, [], input_params)
        for group in loader.queryset_actions[model]:
            for func_name in loader.queryset_actions[model][group]:
                action = loader.queryset_actions[model][group][func_name]
                url = '/api/{}/{}/{}/'.format(app_label, model_name, func_name)
                doc_url = '/docs/api/{}/{}/{}/'.format(app_label, model_name, func_name)
                func = getattr(model.objects.all(), func_name)
                input_params = get_parameters_details(model, func, action['input'])
                self.add_endpoint(func_name, url, 'post', doc_url, [], input_params)

        for endpoint in self.endpoints:
            if endpoint['name'] == endpoint_name:
                return endpoint
        return None

    def add_endpoint(self, name, url, method, doc_url, query_params, input_params):
        endpoint = dict(
            name=name, url=url, method=method, doc_url=doc_url,
            vars=vars, query_params=query_params, input_params=input_params
        )
        self.endpoints.append(endpoint)

    def form_cls(self, endpoint, token):

        class ApiForm(forms.Form):

            class Meta:
                title = ''
                cancel_button = False
                submit_label = 'Execute'

            def __init__(self, *args, **kwargs):
                super(ApiForm, self).__init__(*args, **kwargs)
                self.query_params_fields = []
                self.input_params_fields = []
                self.fields['api'] = forms.CharField(widget=forms.widgets.HiddenInput(), required=False)
                if '{}' in endpoint['url']:
                    self.fields['pk'] = forms.CharField(label='ID', required=True)
                for param in endpoint['query_params']:
                    self.fields[param['name']] = forms.CharField(label=param['verbose_name'], required=param['required'], help_text=param['help_text'])
                    self.query_params_fields.append(param['name'])
                for param in endpoint['input_params']:
                    self.fields[param['name']] = forms.CharField(label=param['verbose_name'], required=param['required'], help_text=param['help_text'])
                    self.input_params_fields.append(param['name'])

                self.fieldsets = []
                if 'pk' in self.fields:
                    self.fieldsets.append((u'Identifier', {'fields': ('pk',)}))
                if self.query_params_fields:
                    self.fieldsets.append((u'Query Params', {'fields': self.query_params_fields}))
                if self.input_params_fields:
                    self.fieldsets.append((u'Input Params', {'fields': self.input_params_fields}))

            def process(self):
                if 'pk' in self.fields:
                    url = endpoint['url'].format(self.cleaned_data['pk'])
                else:
                    url = endpoint['url']
                data = dict()
                input_params = []
                for field_name in self.input_params_fields:
                    data[field_name] = self.cleaned_data[field_name]
                    input_params.append('{}={}'.format(field_name, self.cleaned_data[field_name]))
                query_params = []
                for field_name in self.query_params_fields:
                    query_params.append('{}={}'.format(field_name, self.cleaned_data[field_name]))
                if query_params:
                    url = '{}?{}'.format(url, '&'.join(query_params))
                url = 'http://localhost:8000{}'.format(url)
                headers = {'Authorization': 'Token {}'.format(token)}
                call_func = endpoint['method'] == 'get' and requests.get or requests.post
                response = call_func(url, data=self.cleaned_data, headers=headers)
                extra = input_params and '-d "{}"'.format('&'.join(input_params)) or ''
                cmd = 'curl -X post -H "Authorization: Token {}" {} {}'.format(token, extra, url)
                return cmd, response.content.decode()

        return ApiForm
