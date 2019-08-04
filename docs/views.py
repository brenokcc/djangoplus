# -*- coding: utf-8 -*-
import json
from os import path, listdir
from django.conf import settings
from djangoplus.cache import CACHE
from djangoplus.admin.models import Group
from djangoplus.docs import Documentation, ApiDocumentation
from djangoplus.decorators.views import view, action
from djangoplus.admin.models import User, Organization
from djangoplus.tools.video import VideoUploader


@view('Source', login_required=False)
def source(request, module=None):
    src = []
    if module == 'model':
        content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'models.py')).read()
        src.append(dict(file='models.py', language='python', content=content))
        content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'formatters.py')).read()
        src.append(dict(file='formatters.py', language='python', content=content))
        for template_file_name in listdir(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'templates')):
            if template_file_name != 'public.html':
                content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'templates', template_file_name)).read()
                src.append(dict(file=template_file_name, language='html', content=content))
    elif module == 'tests':
        content = open(path.join(settings.BASE_DIR, settings.PROJECT_NAME, 'tests.py')).read()
        src.append(dict(file='tests.py', language='python', content=content))
    return locals()


@view('Homologação', login_required=False)
def homologate(request):
    title = 'Homologação'
    groups = Group.objects.filter(role__scope__isnull=True).order_by('name').distinct()

    http_host = request.META['HTTP_HOST']
    if CACHE['ORGANIZATION_MODEL']:
        organization_model_name = CACHE['ORGANIZATION_MODEL'].__name__.lower()
    if CACHE['UNIT_MODEL']:
        unit_model_name = CACHE['UNIT_MODEL'].__name__.lower()

    organization_group_names = []
    unit_group_names = []
    for model in CACHE['ROLE_MODELS']:
        name = CACHE['ROLE_MODELS'][model]['name']
        scope = CACHE['ROLE_MODELS'][model]['scope']
        if scope == 'organization':
            organization_group_names.append(name)
        if scope == 'unit':
            unit_group_names.append(name)

    organization_groups = Group.objects.filter(name__in=organization_group_names).order_by('name').distinct()
    unit_groups = Group.objects.filter(name__in=unit_group_names).order_by('name').distinct()

    organizations = []
    for organization in Organization.objects.all():

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


@view('Documentation', login_required=False)
def doc(request):
    documentation = Documentation()
    workflow_data = json.dumps(CACHE['WORKFLOWS'])
    return locals()


@view('Videos', login_required=False)
def tutorial(request):
    youtube = VideoUploader()
    videos = youtube.list_videos()
    return locals()


@view('API')
def api(request, app_label=None, model_name=None, endpoint_name=None):
    documentation = ApiDocumentation()
    endpoint = None
    if app_label and model_name:
        endpoint = documentation.load_model(app_label, model_name, endpoint_name)
    else:
        documentation.load_models()
    token = request.user.token

    if endpoint:
        form_cls = documentation.form_cls(endpoint, token)
        form = form_cls(request)
        if form.is_valid():
            cmd, result = form.process()
            result = result.replace('\n', '<br>').replace(' ', '&nbsp')
    return locals()


@action(User, 'Login as User', can_execute='Superuser')
def login_as(request, pk):
    pass
