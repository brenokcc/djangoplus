# -*- coding: utf-8 -*-
import json
from os import path, listdir
from django.conf import settings
from djangoplus.cache import loader
from djangoplus.docs import utils
from djangoplus.admin.models import Group
from djangoplus.decorators.views import view
from djangoplus.admin.models import User, Organization


@view(u'Modelo', login_required=False, template='source.html')
def model(request):
    src = []
    content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'models.py')).read()
    src.append(dict(file=u'models.py', language='python', content=content))
    content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'formatters.py')).read()
    src.append(dict(file=u'formatters.py', language='python', content=content))
    for template_file_name in listdir(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'templates')):
        if template_file_name != 'public.html':
            content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'templates', template_file_name)).read()
            src.append(dict(file=template_file_name, language='html', content=content))
    return locals()


@view(u'Testes', login_required=False, template='source.html')
def tests(request):
    src = []
    content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'tests.py')).read()
    src.append(dict(file=u'tests.py', language='python', content=content))
    return locals()


@view(u'Homologação', login_required=False)
def homologate(request):
    title = u'Homologação'
    groups = Group.objects.filter(role__units=0, role__organizations=0).order_by('name').distinct()

    http_host = request.META['HTTP_HOST']
    if loader.organization_model:
        organization_model_name = loader.organization_model.__name__.lower()
    if loader.unit_model:
        unit_model_name = loader.unit_model.__name__.lower()

    organization_group_names = []
    unit_group_names = []
    for model in loader.role_models:
        name = loader.role_models[model]['name']
        scope = loader.role_models[model]['scope']
        if scope == 'organization':
            organization_group_names.append(name)
        if scope == 'unit':
            unit_group_names.append(name)

    organization_groups = Group.objects.filter(name__in=organization_group_names).order_by('name').distinct()
    unit_groups = Group.objects.filter(name__in=unit_group_names).order_by('name').distinct()

    organizations = []
    for organization in Organization.objects.exclude(pk=0):

        organization.users = []
        for group in organization_groups:
            organization.users.append(User.objects.filter(role__group=group, role__organizations=organization))

        organization.units = []
        for unit in organization.get_units():
            organization.units.append(unit)
            unit.users = []
            for group in unit_groups:
                unit.users.append(User.objects.filter(role__group=group, role__units=unit))

        organizations.append(organization)
    return locals()


@view(u'Doc', login_required=False)
def doc(request):
    workflow_data = json.dumps(loader.workflows)

    class_diagrams = []
    for class_diagram_name, models in loader.class_diagrams.items():
        class_digram = dict(classes=[], compositions=[], agregations=[])
        classes = dict()
        position_map = {1: (2.2,), 2: (1.2, 3.2,), 3: (3.2, 1.1, 1.3,), 4: (2.2, 3.2, 1.1, 1.3,), 5: (2.2, 1.1, 1.3, 3.1, 3.3,), 6: (1.2, 3.2, 1.1, 3.1, 1.3, 3.3,), 7: (2.2, 1.2, 3.2, 1.1, 1.3, 3.1, 3.3,), 8: (1.2, 3.2, 1.1, 1.3, 2.1, 2.3, 3.1, 3.3,), 9: (1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3,)}
        n = len(loader.class_diagrams[class_diagram_name])
        associations_count = {}
        for model in loader.class_diagrams[class_diagram_name]:
            associations_count[model] = 0

        for model in loader.class_diagrams[class_diagram_name]:
            verbose_name = model._meta.verbose_name
            classes[model] = dict(name=verbose_name, position='1.1')
            for related_object in model._meta.related_objects:
                related_verbose_name = related_object.related_model._meta.verbose_name
                if related_object.related_model in models:
                    if hasattr(related_object.field, 'composition') and related_object.field.composition:
                        class_digram['compositions'].append([related_verbose_name, verbose_name, related_object.remote_field.name])
                        associations_count[model] += 1
                        associations_count[related_object.related_model] += 1
                    else:
                        if (model not in loader.role_models or class_diagram_name == related_verbose_name) or (class_diagram_name == verbose_name and related_object.related_model not in loader.role_models):
                            class_digram['agregations'].append([verbose_name, related_verbose_name, related_object.field.name])
                            associations_count[related_object.related_model] += 1
                            associations_count[model] += 1
        sorted_associations_count = sorted(associations_count, key=associations_count.get, reverse=True)
        for i, model in enumerate(sorted_associations_count):
            cls = classes[model]
            cls['position'] = position_map[n][i]
            class_digram['classes'].append(cls)

        class_digram_data = json.dumps(class_digram)
        class_diagrams.append((class_diagram_name, class_digram_data))

    documentation = utils.documentation()
    return locals()