# -*- coding: utf-8 -*-
import re
import json
import inspect
from django.apps import apps
from djangoplus.cache import loader
from djangoplus.utils.metadata import get_metadata, get_fiendly_name


def workflow_as_string():
    l = []
    tmp = None
    for task in loader.workflows:
        role = task['role']
        activity = task['activity']
        model = task['model']
        if role != tmp:
            tmp = role or u'Superusuário'
            l.append('Acessar como %s' % tmp)
        if model:
            l.append('\t%s em %s' % (activity, model))
        else:
            l.append('\t%s' % activity)
    return '\n'.join(l)


def extract_exception_messages(function):
    messages = []
    if function:
        code = unicode((''.join(inspect.getsourcelines(function)[0])).decode('utf-8'))
        for message in re.findall('ValidationError.*\(.*\)', code):
            messages.append(
                message[message.index('(') + 1:message.index(')') - 1].replace(u'u\'', '').replace(u'"', ''))
    return messages


def get_search_description(model):
    l = []
    lookups = get_metadata(model, 'search_fields', [])
    if lookups:
        l.append('Permite a busca de registros por ')
        for i, lookup in enumerate(lookups):
            l.append(get_fiendly_name(model, lookup).lower())
            if i > 0 and i == len(lookups) - 2:
                l.append(' e ')
            elif i < len(lookups) - 2:
                l.append(', ')
        l.append('.')
    return ''.join(l)


def get_filter_description(model):
    l = []
    lookups = get_metadata(model, 'list_filter', [])
    if lookups:
        l.append('Possibilita a filtro de registros por ')
        for i, lookup in enumerate(lookups):
            l.append(get_fiendly_name(model, lookup).lower())
            if i > 0 and i == len(lookups) - 2:
                l.append(' e ')
            elif i < len(lookups) - 2:
                l.append(', ')
        l.append('.')
    return ''.join(l)


def get_display_description(model):
    verbose_name_plural = get_metadata(model, 'verbose_name_plural')
    list_template = get_metadata(model, 'list_template')
    article = get_metadata(model, 'verbose_name_female') and 'as' or 'os'
    l = []
    if list_template:
        l.append('Lista %s %s cadastradas no sistema.' % (article, verbose_name_plural.lower()))
    else:
        l.append('Lista %s %s cadastradas no sistema, exibindo os seguintes campos: ' % (
        article, verbose_name_plural.lower()))
        lookups = get_metadata(model, 'list_display', [])
        for i, lookup in enumerate(lookups):
            if i > 0:
                if i == len(lookups) - 1:
                    l.append(' e ')
                else:
                    l.append(', ')
            l.append(get_fiendly_name(model, lookup).lower())
        l.append('.')
    return ''.join(l)


def documentation(as_json=False):

    organization_name = loader.organization_model and get_metadata(loader.organization_model, 'verbose_name') or None
    unit_name = loader.unit_model and get_metadata(loader.unit_model, 'verbose_name') or None
    docs = dict(description='', modules=[], organization_name=organization_name)
    for app_config in apps.get_app_configs():
        description = app_config.module.__doc__
        module = dict(actors=[], models=dict(), views=[], name=app_config.verbose_name, description=description)
        for model in loader.role_models:

            app_label = get_metadata(model, 'app_label')
            if app_label == app_config.name:
                name = loader.role_models[model]['name']
                description = not model.__doc__.startswith('%s(' % model.__name__) and model.__doc__ or None
                scope = None
                if organization_name:
                    scope = loader.role_models[model]['scope']
                    if scope == 'systemic':
                        scope = 'Sistêmico'
                    elif scope == 'organization':
                        scope = organization_name
                    elif scope == 'unit':
                        scope = unit_name
                actor = dict(name=name, scope=scope, description=description)
                module['actors'].append(actor)

        for model in app_config.get_models():
            list_menu = get_metadata(model, 'list_menu')
            list_shortcut = get_metadata(model, 'list_shortcut')
            sequence = get_metadata(model, 'sequence', False)
            if sequence and (list_menu or list_shortcut):
                model_name = get_metadata(model, 'verbose_name')
                description = not model.__doc__.startswith('%s(' % model.__name__) and model.__doc__ or None
                module['models'][model_name] = dict(name=model_name, description=description, functionalities=[])

                add_register(module['models'][model_name]['functionalities'], model)
                add_compositions(module['models'][model_name]['functionalities'], model)
                add_actions(module['models'][model_name]['functionalities'], model)
                add_edition(module['models'][model_name]['functionalities'], model)
                add_list(module['models'][model_name]['functionalities'], model)
                add_deletion(module['models'][model_name]['functionalities'], model)

        for custom_view in loader.views:
            if 'function' in custom_view and app_config.name in custom_view['url']:
                add_view(module['views'], custom_view)

        if module['models']:
            docs['modules'].append(module)
    if as_json:
        return json.dumps(docs)
    else:
        return docs


def add_list(functionalities, model):
    verbose_name_plural = get_metadata(model, 'verbose_name_plural')
    display_description = get_display_description(model)

    add_default_list = True
    for subset in loader.subsets[model]:
        if subset['name'] == 'all':
            add_default_list = False
            break

    if add_default_list:
        search_description = get_search_description(model)
        filter_description = get_filter_description(model)
        description = u'%s %s %s' % (display_description, search_description, filter_description)
        funcionality = dict(name='Listar %s' % verbose_name_plural, actors=[], description=description, business_rules=[])
        for meta_data in (
                'can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization', 'can_list',
                'can_list_by_role', 'can_list_by_unit', 'can_list_by_organization'):
            for actor in get_metadata(model, meta_data, iterable=True):
                if actor:
                    funcionality['actors'].append(actor)
        if not funcionality['actors']:
            funcionality['actors'].append(u'Superusuário')
        functionalities.append(funcionality)

    for subset in loader.subsets[model]:
        name = 'Listar %s %s' % (verbose_name_plural.lower(), subset['title'].lower())
        description = subset['function'].__doc__
        if subset['name'] == 'all':
            name = 'Listar %s' % verbose_name_plural
            description = display_description
        funcionality = dict(name=name, actors=[], description=description, business_rules=[])
        for actor in subset['can_view']:
            if actor:
                funcionality['actors'].append(actor)
        if not funcionality['actors']:
            funcionality['actors'].append(u'Superusuário')
        functionalities.append(funcionality)


def add_register(functionalities, model):
    verbose_name = get_metadata(model, 'verbose_name')
    add_label = get_metadata(model, 'add_label')
    if add_label:
        name = add_label
    else:
        name = u'%s %s' % (u'Cadastrar', verbose_name)

    description = u'Permite a inserção de novas registros de %s no sistema.' % verbose_name.lower()
    business_rules = extract_exception_messages(model.save)
    pre_conditions = []
    post_condition = u'Cadastro realizado com sucesso'
    required_data = []
    for field in model._meta.get_fields():
        if hasattr(field, 'rel') and hasattr(field.rel, 'to') and field.rel.to:
            if hasattr(field, 'exclude') and not field.exclude:
                if hasattr(field, 'blank') and not field.blank:
                    required_data.append(field.rel.to._meta.verbose_name.lower())
    if required_data:
        pre_conditions.append(u'As sequintes informações tenham sido previamente cadastradas no sistema: %s' % (', '.join(required_data)))

    from djangoplus.test.utils import TestCaseGenerator
    g = TestCaseGenerator()
    g.generate(('Cadastrar %s' % verbose_name,))
    scenario = g.get_interactions_as_string()

    funcionality = dict(name=name, actors=[], description=description, business_rules=business_rules,
                        pre_conditions=pre_conditions, post_condition=post_condition, scenario=scenario)

    for meta_data in ('can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization', 'can_add',
                      'can_add_by_role', 'can_add_by_unit', 'can_add_by_organization'):
        for actor in get_metadata(model, meta_data, iterable=True):
            if actor:
                funcionality['actors'].append(actor)
    if not funcionality['actors']:
        funcionality['actors'].append(u'Superusuário')
    functionalities.append(funcionality)


def add_edition(functionalities, model):
    verbose_name = get_metadata(model, 'verbose_name')
    description = u'Permite a edição de registros de %s no sistema.' % verbose_name.lower()
    post_condition = u'Atualização realizada com sucesso'
    funcionality = dict(name='Editar %s' % verbose_name, actors=[], description=description, business_rules=[],
                        pre_conditions=[], post_condition=post_condition)
    for meta_data in ('can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization', 'can_edit',
                      'can_edit_by_role', 'can_edit_by_unit', 'can_edit_by_organization'):
        for actor in get_metadata(model, meta_data, iterable=True):
            if actor:
                funcionality['actors'].append(actor)
    if not funcionality['actors']:
        funcionality['actors'].append(u'Superusuário')
    functionalities.append(funcionality)


def add_deletion(functionalities, model):
    verbose_name = get_metadata(model, 'verbose_name')
    description = u'Exclui registros de %s do sistema.' % verbose_name.lower()
    post_condition = u'Exclusão realizada com sucesso'
    funcionality = dict(name='Excluir %s' % verbose_name, actors=[], description=description, business_rules=[],
                        pre_conditions=[], post_condition=post_condition)
    for meta_data in ('can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization', 'can_delete',
                      'can_delete_by_role', 'can_delete_by_unit', 'can_delete_by_organization'):
        for actor in get_metadata(model, meta_data, iterable=True):
            if actor:
                funcionality['actors'].append(actor)
    if not funcionality['actors']:
        funcionality['actors'].append(u'Superusuário')
    functionalities.append(funcionality)


def add_actions(functionalities, model, ref=None):
    for group in loader.actions[model]:
        for action_name in loader.actions[model][group]:
            verbose_name = get_metadata(model, 'verbose_name')
            action = loader.actions[model][group][action_name]
            description = action['function'].__doc__
            business_rules = extract_exception_messages(action['function'])
            post_condition = u'Ação realizada com sucesso'

            from djangoplus.test.utils import TestCaseGenerator
            g = TestCaseGenerator()
            g.generate(('%s em %s' % (action['title'], verbose_name),))
            scenario = g.get_interactions_as_string()

            funcionality = dict(name=action['title'], actors=[], description=description, business_rules=business_rules,
                                pre_conditions=[], post_condition=post_condition, scenario=scenario)
            for can_execute in action['can_execute']:
                funcionality['actors'].append(can_execute)
            if not funcionality['actors']:
                funcionality['actors'].append(u'Superusuário')
            functionalities.append(funcionality)
    for group in loader.class_actions[model]:
        for action_name in loader.class_actions[model][group]:
            action = loader.class_actions[model][group][action_name]
            description = action['function'].__doc__
            business_rules = extract_exception_messages(action['function'])
            post_condition = u'Ação realizada com sucesso'
            funcionality = dict(name=action['title'], actors=[], description=description, business_rules=business_rules,
                                pre_conditions=[], post_condition=post_condition)
            for can_execute in action['can_execute']:
                funcionality['actors'].append(can_execute)
            if not funcionality['actors']:
                funcionality['actors'].append(u'Superusuário')
            functionalities.append(funcionality)


def add_compositions(functionalities, model, ref=None):
    if model in loader.composition_relations:
        verbose_name = get_metadata(model, 'verbose_name')
        for composition_relation in loader.composition_relations[model]:
            add_label = get_metadata(composition_relation, 'add_label')
            add_str = u'Adicionar %s' % get_metadata(composition_relation, 'verbose_name')
            name = add_label or add_str
            description = ''
            business_rules = []
            pre_conditions = []
            scenario = []

            post_condition = u'%s adicionado com sucesso' % get_metadata(composition_relation, 'verbose_name')
            funcionality = dict(name=name, actors=[], description=description, business_rules=business_rules,
                                pre_conditions=pre_conditions, post_condition=post_condition, scenario=scenario)
            functionalities.append(funcionality)

            add_compositions(functionalities, composition_relation, model)
            add_actions(functionalities, composition_relation, model)


def add_view(functionalties, custom_view):
    description = custom_view['function'].__doc__
    business_rules = extract_exception_messages(custom_view['function'])
    funcionality = dict(name=custom_view['menu'].split('::')[-1], actors=[], description=description,
                        business_rules=business_rules, pre_conditions=[], post_condition='')
    for can_view in custom_view['can_view']:
        funcionality['actors'].append(can_view)
    functionalties.append(funcionality)