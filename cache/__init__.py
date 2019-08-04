# -*- coding: utf-8 -*-

from django.apps import apps
from threading import Thread
from django.conf import settings
from djangoplus.utils.metadata import get_metadata, get_scope, get_can_execute, count_parameters_names


CACHE = dict(
    INITIALIZED=False,
    SETTINGS_INSTANCE=None,
    # USER INTERFACE
    VIEWS=[],
    WIDGETS=[],
    SUBSET_WIDGETS=[],
    MODEL_WIDGETS={},
    CARD_PANEL_MODELS=[],
    ICON_PANEL_MODELS=[],
    LIST_DASHBOARD=[],
    SUBSETS=dict(),
    MANAGER_METHODS=dict(),
    INSTANCE_METHODS=dict(),
    SIMPLE_MODELS=[],
    # ROLES
    ROLE_MODELS=dict(),
    ABSTRACT_ROLE_MODELS=dict(),
    ABSTRACT_ROLE_MODEL_NAMES=dict(),
    # ACTIONS
    INSTANCE_ACTIONS=dict(),
    QUERYSET_ACTIONS=dict(),
    CLASS_ACTIONS=dict(),
    CLASS_VIEW_ACTIONS=dict(),
    FIELDSET_ACTIONS=dict(),
    # DOCUMENTATION
    WORKFLOWS=dict(),
    CLASS_DIAGRAMS=dict(),
    COMPOSITION_FIELDS=dict(),
    COMPOSITION_RELATIONS=dict(),
    # ACCESS SCOPE
    ORGANIZATION_MODEL=None,
    UNIT_MODEL=None,
    SIGNUP_MODEL=None,
    PERMISSIONS_BY_SCOPE=dict(),
    # FORMATTERS
    FORMATTERS=dict(),
    # DOCUMENTATION
    LAST_AUTHENTICATED_ROLE=None,
    LAST_AUTHENTICATED_USERNAME=None,
    # API
    API_MODELS=[]
)


if not CACHE['INITIALIZED']:
    CACHE['INITIALIZED'] = True

    for model in apps.get_models():
        model_name = model.__name__.lower()
        app_label = get_metadata(model, 'app_label')
        add_shortcut = get_metadata(model, 'add_shortcut')
        list_shortcut = get_metadata(model, 'list_shortcut')
        list_diplay = get_metadata(model, 'list_display')
        verbose_name = get_metadata(model, 'verbose_name')
        verbose_name_plural = get_metadata(model, 'verbose_name_plural')
        menu = get_metadata(model, 'menu')
        list_menu = get_metadata(model, 'list_menu')
        dashboard = get_metadata(model, 'dashboard')
        expose = get_metadata(model, 'expose')
        role_signup = get_metadata(model, 'role_signup', False)

        field_names = []
        for field in get_metadata(model, 'get_fields'):
            field_names.append(field.name)
            if hasattr(field, 'composition') and field.composition:
                CACHE['COMPOSITION_FIELDS'][model] = field.name
                if field.remote_field.model not in CACHE['COMPOSITION_RELATIONS']:
                    CACHE['COMPOSITION_RELATIONS'][field.remote_field.model] = []
                if model not in CACHE['COMPOSITION_RELATIONS'][field.remote_field.model]:
                    CACHE['COMPOSITION_RELATIONS'][field.remote_field.model].append(model)

        if model not in CACHE['SUBSETS']:
            CACHE['SUBSETS'][model] = []
        if model not in CACHE['INSTANCE_ACTIONS']:
            CACHE['INSTANCE_ACTIONS'][model] = dict()
        if model not in CACHE['QUERYSET_ACTIONS']:
            CACHE['QUERYSET_ACTIONS'][model] = dict()
        if model not in CACHE['CLASS_ACTIONS']:
            CACHE['CLASS_ACTIONS'][model] = dict()
        if model not in CACHE['FIELDSET_ACTIONS']:
            CACHE['FIELDSET_ACTIONS'][model] = dict()

        if role_signup:
            CACHE['SIGNUP_MODEL'] = model

        # indexing organization model
        if hasattr(model, 'organization_ptr_id'):
            CACHE['ORGANIZATION_MODEL'] = model

        # indexing unit model
        if hasattr(model, 'unit_ptr_id'):
            CACHE['UNIT_MODEL'] = model

        if expose:
            CACHE['API_MODELS'].append(model)

        # indexing shortcuts
        if add_shortcut:
            CACHE['ICON_PANEL_MODELS'].append((model, add_shortcut))
        if list_shortcut:
            CACHE['CARD_PANEL_MODELS'].append((model, list_shortcut))
        if dashboard:
            CACHE['LIST_DASHBOARD'].append(model)

        # indexing the views generated from model classes
        url = '/list/{}/{}/'.format(app_label, model_name)
        icon = None
        if menu and model not in CACHE['COMPOSITION_FIELDS']:
            menu_groups = ()
            if list_menu and list_menu is not True:
                if type(list_menu) != tuple:
                    list_menu = list_menu,
                menu_groups = list_menu
            if type(menu) == tuple:
                description, icon = menu
            else:
                description, icon = menu, get_metadata(model, 'icon')
            permission = '{}.list_{}'.format(app_label, model_name)
            item = dict(
                url=url, can_view=permission, menu=description, icon=icon, add_shortcut=False, groups=menu_groups
            )
            CACHE['VIEWS'].append(item)

        # indexing the @subset and @meta methods defined in the manager classes

        for attr_name in dir(model.objects.get_queryset()):
            attr = getattr(model.objects.get_queryset(), attr_name)
            if hasattr(attr, '_metadata'):
                metadata_type = get_metadata(attr, 'type')
                if metadata_type == 'subset':
                    subset_title = get_metadata(attr, 'verbose_name')
                    subset_name = get_metadata(attr, 'name')
                    subset_help_text = get_metadata(attr, 'help_text')
                    subset_alert = get_metadata(attr, 'alert')
                    subset_notify = get_metadata(attr, 'notify')
                    subset_can_view = get_metadata(attr, 'can_view')
                    subset_order = get_metadata(attr, 'order')
                    subset_menu = get_metadata(attr, 'menu')
                    subset_template = get_metadata(attr, 'template')
                    subset_expose = get_metadata(attr, 'expose')
                    subset_dashboard = get_metadata(attr, 'dashboard')
                    subset_list_display = get_metadata(attr, 'list_display')
                    subset_list_filter = get_metadata(attr, 'list_filter')
                    subset_search_fields = get_metadata(attr, 'search_fields')
                    subset_workflow = get_metadata(attr, 'usecase')
                    subset_url = '{}{}/'.format(url, attr.__func__.__name__)

                    item = dict(
                        verbose_name=subset_title, name=attr_name, function=attr, url=subset_url, can_view=subset_can_view,
                        menu=subset_menu, icon=icon, alert=subset_alert, notify=subset_notify,
                        order=subset_order, help_text=subset_help_text, list_display=subset_list_display,
                        list_filter=subset_list_filter, search_fields=subset_search_fields, expose=subset_expose,
                        template=subset_template
                    )
                    CACHE['SUBSETS'][model].append(item)

                    if subset_dashboard:
                        widget = dict(
                            verbose_name=subset_title, model=model, function=attr_name, can_view=subset_can_view,
                            dashboard=subset_dashboard, formatter=None, link=True, list_display=subset_list_display,
                            list_filter=subset_list_filter, search_fields=subset_search_fields, template=subset_template
                        )
                        CACHE['SUBSET_WIDGETS'].append(widget)

                    if subset_workflow:
                        role = subset_can_view and subset_can_view[0] or 'Superusuário'
                        if attr_name == 'all':
                            activity_description = 'Listar {}'.format(verbose_name_plural,)
                        else:
                            activity_description = 'Listar {}: {}'.format(verbose_name_plural, subset_title)
                        CACHE['WORKFLOWS'][subset_workflow] = dict(activity=activity_description, role=role, model=None)

                # @meta
                else:
                    widget_verbose_name = get_metadata(attr, 'verbose_name')
                    widget_can_view = get_metadata(attr, 'can_view')
                    widget_dashboard = get_metadata(attr, 'dashboard')
                    widget_formatter = get_metadata(attr, 'formatter')
                    widget_icon = get_metadata(attr, 'icon')
                    widget = dict(
                        verbose_name=widget_verbose_name, model=model, function=attr_name, can_view=widget_can_view,
                        dashboard=widget_dashboard, formatter=widget_formatter, link=False, icon=widget_icon
                    )
                    CACHE['SUBSET_WIDGETS'].append(widget)
                    if model not in CACHE['MANAGER_METHODS']:
                        CACHE['MANAGER_METHODS'][model] = list()
                        CACHE['MANAGER_METHODS'][model].append(widget)

        # indexing the actions refered in fieldsets
        if hasattr(model, 'fieldsets'):
            for title, info in model.fieldsets:
                if title not in CACHE['FIELDSET_ACTIONS'][model]:
                    CACHE['FIELDSET_ACTIONS'][model][title] = []
                for action_name in info.get('actions', []):
                    CACHE['FIELDSET_ACTIONS'][model][title].append(action_name)
        else:
            CACHE['SIMPLE_MODELS'].append(model)

        # indexing the actions defined in models
        for attr_name in dir(model):
            if attr_name[0] != '_' and attr_name not in field_names:
                func = getattr(model, attr_name)

                if hasattr(func, '_action'):
                    action = getattr(func, '_action')
                    action_group = action['group']

                    action_can_execute = get_can_execute(action)
                    action_verbose_name = action['verbose_name']
                    action_workflow = action['usecase']
                    action_menu = action['menu']
                    view_name = action['view_name']
                    if action_group not in CACHE['INSTANCE_ACTIONS'][model]:
                        CACHE['INSTANCE_ACTIONS'][model][action_group] = dict()
                    CACHE['INSTANCE_ACTIONS'][model][action_group][view_name] = action
                    if action_workflow:
                        role = action_can_execute and action_can_execute[0] or 'Superusuário'
                        CACHE['WORKFLOWS'][action_workflow] = dict(activity=action_verbose_name, role=role, model=verbose_name)
                    if action_menu:
                        url = '/action/{}/{}/{}/'.format(
                            get_metadata(model, 'app_label'), model.__name__.lower(), attr_name
                        )
                        action_view = dict(
                            verbose_name=action_verbose_name, function=None, url=url, can_view=action_can_execute, menu=action_menu,
                            icon=None, style='ajax', add_shortcut=False, doc=func.__doc__, usecase=None
                        )
                        CACHE['VIEWS'].append(action_view)

                if hasattr(func, '_metadata'):
                    widget_verbose_name = get_metadata(func, 'verbose_name')
                    widget_can_view = get_metadata(func, 'can_view')
                    widget_dashboard = get_metadata(func, 'dashboard')
                    widget_formatter = get_metadata(func, 'formatter')
                    widget_icon = get_metadata(func, 'icon')
                    widget = dict(
                        verbose_name=widget_verbose_name, model=model, function=attr_name, can_view=widget_can_view,
                        dashboard=widget_dashboard, formatter=widget_formatter, link=False, icon=widget_icon
                    )
                    if model not in CACHE['MODEL_WIDGETS']:
                        CACHE['MODEL_WIDGETS'][model] = []
                    CACHE['MODEL_WIDGETS'][model].append(widget)
                    if model not in CACHE['INSTANCE_METHODS']:
                        CACHE['INSTANCE_METHODS'][model] = list()
                        CACHE['INSTANCE_METHODS'][model].append(widget)

        # indexing the actions related to relations whose model has the add_inline meta-attribute
        inlines = []
        if hasattr(model, 'fieldsets'):
            for fieldset in model.fieldsets:
                if 'relations' in fieldset[1]:
                    for item in fieldset[1]['relations']:
                        if ':' in item:
                            # 'relation_name:all[action_a,action_b],subset[action_c]'
                            relation_name = item.split(':')[0]
                        elif '[' in item:
                            # 'relation_name[action_a,action_b]'
                            relation_name = item.split('[')[0]
                        else:
                            # 'relation_name'
                            relation_name = item

        # indexing the actions defined in managers
        qs_manager_class = type(model.objects.get_queryset())
        for attr_name in dir(qs_manager_class):
            if not attr_name[0] == '_':
                attr = getattr(qs_manager_class, attr_name)
                if hasattr(attr, '_action'):
                    action = getattr(attr, '_action')
                    action_verbose_name = action['verbose_name']
                    action_can_execute = get_can_execute(action)
                    action_group = action['group']
                    action_name = action['view_name']
                    action_subsets = action['subsets']
                    action_workflow = action['usecase']
                    is_class_method = isinstance(qs_manager_class.__dict__[attr_name], classmethod)
                    if not action_subsets:
                        action['inline'] = True
                    if is_class_method:
                        if action_group not in CACHE['CLASS_ACTIONS'][model]:
                            CACHE['CLASS_ACTIONS'][model][action_group] = dict()
                        CACHE['CLASS_ACTIONS'][model][action_group][action_name] = action
                    else:
                        if action_group not in CACHE['QUERYSET_ACTIONS'][model]:
                            CACHE['QUERYSET_ACTIONS'][model][action_group] = dict()
                        CACHE['QUERYSET_ACTIONS'][model][action_group][action_name] = action

                    if action_workflow:
                        role = action_can_execute and action_can_execute[0] or 'Superusuário'
                        CACHE['WORKFLOWS'][action_workflow] = dict(activity=action_verbose_name, role=role, model=verbose_name)

    # indexing the formatters
    for app_label in settings.INSTALLED_APPS:
        try:
            module_name = '{}.formatters'.format(app_label)
            module = __import__(module_name, fromlist=list(map(str, app_label.split('.'))))
            for attr_name in dir(module):
                module_attr = getattr(module, attr_name)
                if hasattr(module_attr, '_formatter'):
                    CACHE['FORMATTERS'][getattr(module_attr, '_formatter') or attr_name] = module_attr
        except ImportError as e:
            pass

    from djangoplus.ui.components import Component
    for cls in Component.subclasses():
        formatter_name = cls.formatter_name or cls.__name__.lower()
        if formatter_name not in CACHE['FORMATTERS']:
            CACHE['FORMATTERS'][formatter_name] = cls

    # indexing the actions, views and widgets in views module
    for app_label in settings.INSTALLED_APPS:
            try:
                module = __import__('{}.views'.format(app_label), fromlist=list(map(str, app_label.split('.'))))
                for attr_name in dir(module):
                    func = getattr(module, attr_name)
                    # indexing the actions defined in the views
                    if hasattr(func, '_action'):
                        action = getattr(func, '_action')
                        action_group = action['group']
                        action_model = action['model']
                        action_function = action['function']
                        action_name = action['view_name']
                        action_verbose_name = action['verbose_name']
                        action_workflow = action['usecase']
                        action_can_execute = get_can_execute(action)
                        action_subsets = action['subsets']
                        action_menu = action['menu']

                        if action_workflow:
                            role = action_can_execute and action_can_execute[0] or 'Superusuário'
                            action_model_verbose_name = get_metadata(action_model, 'verbose_name')
                            CACHE['WORKFLOWS'][action_workflow] = dict(activity=action_verbose_name, role=role, model=action_model_verbose_name)
                        # instance action
                        if count_parameters_names(action_function) > 1:
                            if action_group not in CACHE['INSTANCE_ACTIONS'][action_model]:
                                CACHE['INSTANCE_ACTIONS'][action_model][action_group] = dict()
                            CACHE['INSTANCE_ACTIONS'][action_model][action_group][action_name] = action
                        # class action
                        else:
                            if not action_subsets:
                                action['inline'] = True
                            if action_model not in CACHE['CLASS_VIEW_ACTIONS']:
                                CACHE['CLASS_VIEW_ACTIONS'][action_model] = dict()
                            if action_group not in CACHE['CLASS_VIEW_ACTIONS'][action_model]:
                                CACHE['CLASS_VIEW_ACTIONS'][action_model][action_group] = dict()
                            CACHE['CLASS_VIEW_ACTIONS'][action_model][action_group][action_name] = action
                    # indexing the views
                    elif hasattr(func, '_view'):
                        action = getattr(func, '_view')
                        CACHE['VIEWS'].append(action)
                        view_title = action['verbose_name']
                        view_workflow = action['usecase']
                        view_can_view = action['can_view']
                        if view_workflow:
                            role = view_can_view and view_can_view[0] or 'Superusuário'
                            CACHE['WORKFLOWS'][view_workflow] = dict(activity=view_title, role=role, model=None)
                    # indexing the widgets
                    elif hasattr(func, '_widget'):
                        CACHE['WIDGETS'].append(getattr(func, '_widget'))
            except ImportError as e:
                pass

    for model in apps.get_models():
        app_label = get_metadata(model, 'app_label')
        verbose_name = get_metadata(model, 'verbose_name')
        role_username = get_metadata(model, 'role_username')
        role_signup = get_metadata(model, 'role_signup')
        add_label = get_metadata(model, 'add_label', None)
        workflow = get_metadata(model, 'usecase', 0)
        diagram_classes = get_metadata(model, 'class_diagram', None)

        # indexing role models
        if role_username:
            CACHE['ROLE_MODELS'][model] = dict(
                username_field=role_username, scope=get_scope(
                    model, CACHE['ORGANIZATION_MODEL'], CACHE['UNIT_MODEL']), name=verbose_name
            )
        for subclass in model.__subclasses__():
            subclass_role_username = get_metadata(subclass, 'role_username')
            if subclass_role_username:
                subclass_verbose_name = get_metadata(subclass, 'verbose_name')
                CACHE['ROLE_MODELS'][subclass] = dict(username_field=subclass_role_username, scope=get_scope(
                    subclass, CACHE['ORGANIZATION_MODEL'], CACHE['UNIT_MODEL']), name=subclass_verbose_name)
                if model not in CACHE['ABSTRACT_ROLE_MODELS']:
                    CACHE['ABSTRACT_ROLE_MODELS'][model] = []
                    CACHE['ABSTRACT_ROLE_MODEL_NAMES'][verbose_name] = []
                CACHE['ABSTRACT_ROLE_MODELS'][model].append(subclass)
                CACHE['ABSTRACT_ROLE_MODEL_NAMES'][verbose_name].append(subclass_verbose_name)

        permission_by_scope = dict()
        for scope in ('role', 'unit', 'organization'):
            for permission_name in ('edit', 'add', 'delete', 'view', 'list'):
                permission_key = '{}_by_{}'.format(permission_name, scope)
                for group_name in get_metadata(model, 'can_{}'.format(permission_key), (), iterable=True):
                    if permission_name == 'list':
                        permission_key = 'view_by_{}'.format(scope)
                    if permission_key not in permission_by_scope:
                        permission_by_scope[permission_key] = []
                    if group_name in CACHE['ABSTRACT_ROLE_MODEL_NAMES']:
                        for concrete_group_name in CACHE['ABSTRACT_ROLE_MODEL_NAMES'][group_name]:
                            permission_by_scope[permission_key].append(concrete_group_name)
                    else:
                        permission_by_scope[permission_key].append(group_name)
            for group_name in get_metadata(model, 'can_admin_by_{}'.format(scope), (), iterable=True):
                for permission_name in ('edit', 'add', 'delete', 'view', 'list'):
                    if permission_name == 'list':
                        permission_key = 'view_by_{}'.format(scope)
                    else:
                        permission_key = '{}_by_{}'.format(permission_name, scope)
                    if permission_key not in permission_by_scope:
                        permission_by_scope[permission_key] = []
                    if group_name not in permission_by_scope[permission_key]:
                        if group_name in CACHE['ABSTRACT_ROLE_MODEL_NAMES']:
                            for concrete_group_name in CACHE['ABSTRACT_ROLE_MODEL_NAMES'][group_name]:
                                permission_by_scope[permission_key].append(concrete_group_name)
                        else:
                            permission_by_scope[permission_key].append(group_name)

        for permission_name in ('edit', 'add', 'delete', 'view', 'list'):
            permission_key = permission_name
            for group_name in get_metadata(model, 'can_{}'.format(permission_name), (), iterable=True):
                if permission_name == 'list':
                    permission_key = 'view'
                if permission_key not in permission_by_scope:
                    permission_by_scope[permission_key] = []
                if group_name not in permission_by_scope[permission_key]:
                    permission_by_scope[permission_key].append(group_name)
        for group_name in get_metadata(model, 'can_admin', (), iterable=True):
            for permission_name in ('edit', 'add', 'delete', 'view', 'list'):
                permission_key = permission_name
                if permission_name == 'list':
                    permission_key = 'view'
                if permission_key not in permission_by_scope:
                    permission_by_scope[permission_key] = []
                if group_name not in permission_by_scope[permission_key]:
                    permission_by_scope[permission_key].append(group_name)

        for actions_dict in (CACHE['INSTANCE_ACTIONS'], CACHE['QUERYSET_ACTIONS']):
            for category in actions_dict[model]:
                for key in list(actions_dict[model][category].keys()):
                    name = actions_dict[model][category][key]['verbose_name']
                    view_name = actions_dict[model][category][key]['view_name']
                    can_execute = []
                    for scope in ('', 'role', 'unit', 'organization'):
                        scope = scope and '_by_{}'.format(scope) or scope
                        for group_name in actions_dict[model][category][key].get('can_execute{}'.format(scope)) or ():
                            permission_key = '{}{}'.format(view_name, scope)
                            if permission_key not in permission_by_scope:
                                permission_by_scope[permission_key] = []
                            permission_by_scope[permission_key].append(group_name)

        if permission_by_scope:
            CACHE['PERMISSIONS_BY_SCOPE'][model] = permission_by_scope

        if workflow:
            role = permission_by_scope.get('add_by_role') and permission_by_scope.get('add_by_role')[0] or None
            if not role:
                role = permission_by_scope.get('add_by_unit') and permission_by_scope.get('add_by_unit')[0] or None
            if not role:
                role = permission_by_scope.get('add_by_organization') and permission_by_scope.get('add_by_organization')[0] or None
            if not role:
                role = permission_by_scope.get('add') and permission_by_scope.get('add')[0] or None
            if not role or role == verbose_name:
                role = 'Superusuário'

            if model in CACHE['COMPOSITION_FIELDS']:
                related_model = getattr(model, CACHE['COMPOSITION_FIELDS'][model]).field.remote_field.model
                related_verbose_name = get_metadata(related_model, 'verbose_name')
                related_add_label = get_metadata(model, 'add_label')
                if related_add_label:
                    related_add_label = related_add_label.replace(' em ', ' __ ')
                    activity = '{} em {}'.format(related_add_label, related_verbose_name)
                else:
                    verbose_name = verbose_name.replace(' em ', ' __ ')
                    activity = 'Adicionar {} em {}'.format(verbose_name, related_verbose_name)
                CACHE['WORKFLOWS'][workflow] = dict(activity=activity, role=role, model=None)
            else:
                if add_label:
                    activity = add_label
                else:
                    if role_signup:
                        activity = '{} {}'.format('Cadastrar-se como', verbose_name)
                        role = verbose_name
                    else:
                        activity = '{} {}'.format('Cadastrar', verbose_name)
                CACHE['WORKFLOWS'][workflow] = dict(activity=activity, role=role, model=None)

        if diagram_classes is not None:
            CACHE['CLASS_DIAGRAMS'][verbose_name] = [model]
            if type(diagram_classes) == bool and diagram_classes:
                for field in model._meta.get_fields():
                    if field.remote_field and field.remote_field.model:
                        if field.remote_field.model not in CACHE['CLASS_DIAGRAMS'][verbose_name]:
                            CACHE['CLASS_DIAGRAMS'][verbose_name].append(field.remote_field.model)
            else:
                for model_name in diagram_classes:
                    try:
                        extra_model = apps.get_model(app_label, model_name)
                    except LookupError:
                        for extra_model in apps.get_models():
                            if extra_model.__name__.lower() == model_name:
                                break
                    if extra_model not in CACHE['CLASS_DIAGRAMS'][verbose_name]:
                        CACHE['CLASS_DIAGRAMS'][verbose_name].append(extra_model)

    keys = list(CACHE['WORKFLOWS'].keys())
    keys.sort()
    l = []
    for key in keys:
        l.append(CACHE['WORKFLOWS'][key])
    CACHE['WORKFLOWS'] = l

    if settings.DROPBOX_TOKEN and settings.DEBUG:
        def sync_storage():
            from djangoplus.utils.storage.dropbox import DropboxStorage
            DropboxStorage().sync()
        Thread(target=sync_storage).start()