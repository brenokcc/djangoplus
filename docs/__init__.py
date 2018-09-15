# -*- coding: utf-8 -*-

import json
from django.apps import apps
from django.conf import settings
from djangoplus.docs import utils
from django.utils import translation
from djangoplus.tools import terminal
from django.utils.translation import ugettext as _


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

