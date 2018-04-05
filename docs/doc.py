# -*- coding: utf-8 -*-

import json
from django.apps import apps
from django.conf import settings
from djangoplus.docs import utils
from djangoplus.cache import loader
from django.http import HttpRequest
from django.utils import translation
from djangoplus.utils import terminal
from djangoplus.admin.models import User
from django.utils.translation import ugettext as _
from django.template.defaultfilters import slugify
from djangoplus.ui.components.forms import factory, fields as form_fields
from djangoplus.db.models import fields as model_fields
from djangoplus.utils.metadata import get_metadata, find_action, find_model_by_verbose_name, find_model_by_add_label, get_field, find_model_by_verbose_name_plural, find_subset_by_title


class Actor(object):
    def __init__(self, name=None, description=None, scope=None):
        self.name = name
        self.description = description
        self.scope = scope

    def __str__(self):
        return self.name

    def as_dict(self):
        return dict(name=self.name, description=self.description, scope=self.scope)


class UseCase(object):
    
    ACTOR = None

    """ This class has the aim of generating interactions and testcases based on usecases.
    The code generation is based on strings that holds the usercase name.
    The usecases must follow the sintaxe bellow:
        Login as <group name>
        Register <class verbose name>
        List <class plural verbose name>
        List <class plural verbose name>: <subset name>
        Add <relation name> to <class verbose name>
        <action name> in <class verbose name>
        <action name>
    Code generation is also compatible with Porguese and may also follow the sintaxe bellow
        Acessar como <nome do grupo>
        Cadastrar <nome amigável da classe>
        Listar <nome amigável da classe no plural>
        Listar <nome amigável da classe no plural>: <nome do subconjunto>
        Adicionar <nome da relação> em <nome amigável da classe>
        <nome da ação> em <nome amigável da classe>
        <nome da ação>
    """

    def __init__(self, name):

        translation.activate(settings.LANGUAGE_CODE)

        self._interactions = []

        self._test_flow_code = []
        self._test_function_code = []

        self.name = name
        self.description = None
        self.actors = []
        self.business_rules = []
        self.pre_conditions = []
        self.post_condition = None

        self._request = None

        if name.startswith(_('Access')):
            self._login(name)
        elif name.startswith(_('List')):
            self._list(name)
        elif name.startswith(_('Register')) and _('in') not in name:
            self._register(name)
        elif name.startswith(_('Add')):
            self._add(name)
        else:
            self._execute(name)

    def _mocked_request(self):
        if not self._request:
            self._request = HttpRequest()
            self._request.user = User(pk=0)
        return self._request

    def _debug(self):
        print('\n'.join(self._interactions))
        print()
        print('\n'.join(self._test_function_code))
        print()
        print('\n'.join(self._test_flow_code))

    def _login(self, action):
        verbose_name = action.split(_('as'))[-1].strip()
        loader.last_authenticated_role = verbose_name
        model = find_model_by_verbose_name(verbose_name)
        if model:
            role_username = get_metadata(model, 'role_username')
            if role_username:
                field = get_field(model, role_username)
                username = field.example or ''
            else:
                username = settings.DEFAULT_SUPERUSER
        else:
            username = username = settings.DEFAULT_SUPERUSER
        password = settings.DEFAULT_PASSWORD

        interaction = _('The user access the system as')
        self._interactions.append('{} {}'.format(interaction, verbose_name))
        self._interactions.append(_('The system displays the main page'))

        self._test_flow_code.append('\t\t# {}'.format(action))
        self._test_flow_code.append("\t\tif self.login('{}', '{}'):".format(username, password))

    def _find(self, model):
        click_str = []
        click_str_unicode = []

        verbose_name_plural = get_metadata(model, 'verbose_name_plural')
        list_shortcut = get_metadata(model, 'list_shortcut', [], iterable=True)
        menu = get_metadata(model, 'menu')

        if not loader.last_authenticated_role or True in list_shortcut or loader.last_authenticated_role in list_shortcut:

            left = _('The user clicks on the shortcut card')
            right = _('in the dashboard at main page')
            interaction = '{} "{}" {}'.format(left, verbose_name_plural, right)
            self._interactions.append(interaction)

            self._interactions.append(_('The system displays the listing page'))

            self._test_function_code.append('\t\tself.click_link(u\'{}\')'.format(verbose_name_plural))
            return True
        elif menu:

            if type(menu) == tuple:
                menu = menu[0]
            for menu_item in menu.split('::'):
                click_str.append('"{}"'.format(menu_item))
                click_str_unicode.append("'{}'".format(menu_item))

            interaction = _('The user access the menu')
            self._interactions.append('{} {}'.format(interaction, ', '.join(click_str)))

            self._test_function_code.append('\t\tself.click_menu({})'.format(', '.join(click_str_unicode)))
            return True
        return False

    def _view(self, model, recursive=False):
        accessible = False

        verbose_name = get_metadata(model, 'verbose_name')
        list_shortcut = get_metadata(model, 'list_shortcut', [])
        list_menu = get_metadata(model, 'menu')

        # if the model can be accessed by the menu or shortcut
        if (list_shortcut or list_menu) and self._find(model):
            accessible = True
            self._interactions.append(_('The user locates the record and clicks the visualization icon'))
            self._interactions.append(_('The system displays the visualization page'))
            self._test_function_code.append("\t\tself.click_icon('{}')".format('Visualizar'))  # _('Visualize')
        else:
            # the model can be accessed only by a parent model
            for parent_model in loader.composition_relations:
                if model in loader.composition_relations[parent_model]:
                    self._view(parent_model, True)
                    panel_title = None
                    if hasattr(parent_model, 'fieldsets'):
                        for fieldset in parent_model.fieldsets:
                            for item in fieldset[1].get('relations', ()) + fieldset[1].get('inlines', ()):
                                relation = getattr(parent_model, item)
                                if hasattr(relation, 'field') and relation.field.remote_field.related_model == model:
                                    panel_title = fieldset[0]
                                    break
                    if panel_title:
                        accessible = True
                        if '::' in panel_title:
                            tab_name, panel_title = panel_title.split('::')
                            self._test_function_code.append("\t\tself.click_tab('{}')".format(tab_name))
                            interaction = _('The user clicks the tab')
                            self._interactions.append('{} "{}"'.format(interaction, tab_name))
                        if panel_title:
                            interaction = _('The user looks at the painel')
                            self._interactions.append('{} "{}"'.format(interaction, panel_title))
                            self._test_function_code.append("\t\tself.look_at_panel('{}')".format(panel_title))

                    if recursive:
                        self._interactions.append(_('The user locates the record and clicks the visualization icon'))
                        self._interactions.append(_('The system displays the visualization page'))
                        self._test_function_code.append("\t\tself.click_icon('{}')".format('Visualizar'))  # _('Visualize')

        if not accessible:
            raise ValueError('There is no way to access the model "{}", please do one of the following things:\n '
                             'i) Add the "list_menu" meta-attribute to the model\n '
                             'ii) Add the "list_shortcut" meta-attribute to the model\n '
                             'iii) Add the "composition" field attribute to one of foreignkey fields of the model if '
                             'it exists and the the relation on the foreignkey model'.format(verbose_name))

    def _list(self, action):
        verbose_name_plural = action.replace(_('List'), '').strip()

        if ':' in action:
            # it refers to a subset
            verbose_name_plural, subset_name = verbose_name_plural.split(':')
            verbose_name_plural = verbose_name_plural.strip()
            model = find_model_by_verbose_name_plural(verbose_name_plural)
            subset_name = subset_name.strip()
            subset = find_subset_by_title(subset_name, model)

            # set the attributes of the usecase
            self.description = subset['function'].__doc__.strip()
            for can_view in subset['can_view']:
                self.actors.append(can_view)
            if not self.actors:
                self.actors.append('Superusuário')

            # register the interactions and testing code
            self._find(model)

            interaction = _('The user clicks the pill')
            self._interactions.append('{} "{}"'.format(interaction, subset_name))

            self._test_function_code.append("\t\tself.click_link('{}')".format(subset_name))

        else:
            model = find_model_by_verbose_name_plural(verbose_name_plural)

            # set the attributes of the usecase
            self.description = 'List {} previouly registered in the system'.format(verbose_name_plural.lower())
            self.post_condition = _('The system displays the registered records')
            for meta_data in ('can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization',
                              'can_view', 'can_view_by_role', 'can_view_by_unit', 'can_view_by_organization'):
                for actor in get_metadata(model, meta_data, iterable=True):
                    if actor:
                        self.actors.append(actor)
            if not self.actors:
                self.actors.append('Superusuário')

            # register the interactions and testing code
            self._find(model)

        # register the interactions
        search_fields = utils.get_search_fields(model)
        if search_fields:
            interaction = _('The user optionally performs a search by')
            self._interactions.append('{} {}'.format(interaction, search_fields))

        list_filter = utils.get_list_filter(model)
        if list_filter:
            interaction = _('The user optionally filter the records by')
            self._interactions.append('{} {}'.format(interaction, list_filter))

        left = _('The system displays')
        right = _('of previous registered records')
        interaction = '{} {} {}'.format(left, utils.get_list_display(model), right)
        self._interactions.append(interaction)

    def _register(self, action):
        model = find_model_by_add_label(action)
        if model:
            verbose_name = get_metadata(model, 'verbose_name')
            button_label = get_metadata(model, 'add_label')
            func_name = slugify(button_label).replace('-', '_')
        else:
            verbose_name = action.replace(_('Register'), '').strip()
            model = find_model_by_verbose_name(verbose_name)
            button_label = _('Register')
            func_name = 'cadastrar_{}'.format(model.__name__.lower())

        # set the attributes of the usecase
        self.name = action
        self.description = '{} {} {}'.format(_('Add new records of'),  verbose_name.lower(), _('in the system'))
        self.business_rules = utils.extract_exception_messages(model.save)
        self.post_condition = _('The record will be successfully registered in the system')
        required_data = []
        for field in get_metadata(model, 'get_fields'):
            if isinstance(field, model_fields.ForeignKey):
                if not isinstance(field, model_fields.OneToOneField):
                    if not isinstance(field, model_fields.OneToManyField):
                        required_data.append(field.verbose_name.lower())
        if required_data:
            pre_condition = _('The following information must have been previouly registered in the system: ')
            self.pre_conditions.append('{} {}'.format(pre_condition, ', '.join(required_data)))

        for meta_data in ('can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization', 'can_add',
                          'can_add_by_role', 'can_add_by_unit', 'can_add_by_organization'):
            for actor in get_metadata(model, meta_data, iterable=True):
                if actor:
                    self.actors.append(actor)
        if not self.actors:
            self.actors.append(_('Superuser'))

        # register the interactions and testing code
        func_signature = '{}(self)'.format(func_name)
        self._test_flow_code.append('\t\t\t# {}'.format(action))
        self._test_flow_code.append('\t\t\tself.{}()'.format(func_name))

        self._test_function_code.append('\tdef {}:'.format(func_signature))
        self._find(model)
        self._test_function_code.append("\t\tself.click_button('{}')".format(button_label))

        a = _('The user clicks the button')
        b = _('on the right-side of the action bar')
        self._interactions.append('{} "{}" {}'.format(a, button_label, b))

        form = factory.get_register_form(self._mocked_request(), model())
        self._fill_out(form)

        interaction = _('The user clicks the button')
        self._interactions.append('{} "{}"'.format(interaction, button_label))
        self._test_function_code.append("\t\tself.click_button('{}')".format(button_label))
        self._test_function_code.append("\t\tself.click_icon('{}')".format('Principal'))

    def _add(self, action):

        model = None

        if action.startswith(_('Add')):
            # not add_label was defined for the related model
            tokens = action.replace(_('Add'), '').split(_(' in '))
            verbose_name = tokens[0].strip()
            if len(tokens) > 1:
                relation_verbose_name = tokens[1].strip()
                model = find_model_by_verbose_name(relation_verbose_name)
            related_model = find_model_by_verbose_name(verbose_name)
        else:
            # an add_label was defined for the related model
            tokens = action.split(_(' in '))
            add_label = tokens[0].strip()
            if len(tokens) > 1:
                verbose_name = tokens[1].strip()
                model = find_model_by_verbose_name(verbose_name)
            related_model = find_model_by_add_label(add_label)

        # check if there is a fieldset was defined with the relation
        relation_name = None
        inlines = []
        if hasattr(model, 'fieldsets'):
            for fieldset in model.fieldsets:
                if 'relations' in fieldset[1]:
                    for item in fieldset[1]['relations']:
                        tmp = getattr(model, item)
                        if hasattr(tmp, 'field') and tmp.field.remote_field.model == model:
                            relation_name = item
                if 'inlines' in fieldset[1]:
                    for item in fieldset[1]['inlines']:
                        inlines.append(item)
                        tmp = getattr(model, item)
                        if hasattr(tmp, 'field') and tmp.field.remote_field.model == model:
                            relation_name = item

        # if the relation was defined in a fieldset
        if relation_name:
            add_inline = relation_name in inlines
            add_label = get_metadata(related_model, 'add_label')
            button_label = add_label or 'Adicionar'
            button_label = get_metadata(related_model, 'add_label', button_label)

            function_signature = '{}_{}_{}_{}'.format(_('add'), related_model.__name__.lower(), _('in'), model.__name__.lower())
            self._test_flow_code.append('\t\t\t# {}'.format(action))
            self._test_flow_code.append('\t\t\tself.{}()'.format(function_signature))

            self._test_function_code.append('\tdef {}(self):'.format(function_signature))

            self._view(related_model)

            # the form is not in the visualization page and it must be opened
            if not add_inline:
                add_button_label = 'Adicionar {}'.format(get_metadata(related_model, 'verbose_name'))
                add_button_label = get_metadata(related_model, 'add_label', add_button_label)

                interaction = _('The user clicks the button')
                self._interactions.append('{} "{}"'.format(interaction, add_button_label))
                self._interactions.append(_('The system displays a popup window'))

                self._test_function_code.append("\t\tself.click_button('{}')".format(add_button_label))
                self._test_function_code.append("\t\tself.look_at_popup_window()")

            form = factory.get_many_to_one_form(self._mocked_request(), model(), relation_name, related_model())
            self._fill_out(form)

            interaction = _('The user clicks the button')
            self._interactions.append('{} "{}"'.format(interaction, button_label))

            self._test_function_code.append("\t\tself.click_button('{}')".format(button_label))
            self._test_function_code.append("\t\tself.click_icon('{}')".format('Principal'))
        else:
            raise ValueError('Please add the {}\'s relation in the fieldsets of model {}'.format(related_model.__name__, model.__name__))

    def _fill_out(self, form, inline=None):

        if not inline:
            self._interactions.append(_('The system displays the input form'))

        form.contextualize()
        form.configure()

        for fieldset in form.configured_fieldsets:
            if inline or fieldset['title']:
                if fieldset['tuples'] and fieldset['tuples'][0]:
                    interaction = _('The user looks at fieldset')
                    self._interactions.append('{} "{}"'.format(interaction, inline or fieldset['title']))

            for fields in fieldset['tuples']:
                if not type(fields) in (list, tuple):
                    fields = fields,
                field_names = [field['name'] for field in fields]

                for field_name in field_names:
                    if field_name in form.base_fields:
                        form_field = form.base_fields[field_name]

                        # it is necessary to skip "organization" and "unit" fields if the actor's scope does not match
                        if self.actors and hasattr(form_field, 'queryset'):
                            from djangoplus.admin.models import Organization, Unit
                            scopes = []
                            if issubclass(form_field.queryset.model, Organization):
                                scopes = ['systemic']
                            if issubclass(form_field.queryset.model, Unit):
                                scopes = ['systemic', 'organization']
                            if scopes:
                                ignore_field = False
                                for role_model in loader.role_models:
                                    if loader.role_models[role_model]['name'] == self.actors[0]:
                                        if loader.role_models[role_model]['scope'] not in scopes:
                                            ignore_field = True
                                            break
                                if ignore_field:
                                    continue

                        # get the test value in case of model form and if the sample value was defined in the model
                        value = ''
                        meta_class = getattr(form, '_meta', None)
                        if meta_class:
                            if hasattr(meta_class.model, field_name):
                                model_field = get_field(meta_class.model, field_name)
                                if hasattr(model_field, 'example') and model_field.example:
                                    value = callable(model_field.example) and model_field.example() or model_field.example

                        # define the kind of user interaction
                        if hasattr(form_field, 'choices') and form_field.choices:
                            self._test_function_code.append("\t\tself.choose('{}', '{}')".format(form_field.label, value))
                            interaction = _('The user chooses')
                            self._interactions.append('{} "{}"'.format(interaction, form_field.label))
                        else:
                            if not isinstance(form_field, form_fields.BooleanField) and not isinstance(form_field, form_fields.NullBooleanField):
                                self._test_function_code.append("\t\tself.enter('{}', '{}')".format(form_field.label, value))
                                interaction = _('The user enters')
                                self._interactions.append('{} "{}"'.format(interaction, form_field.label))

            # add the interactions recursively if the form inner forms
            for field, form, required, save in fieldset.get('one_to_one', ()):
                self._fill_out(form, inline=field.label)
            for name, field, one_to_many_forms, one_to_many_count in fieldset.get('one_to_many', ()):
                for form in one_to_many_forms[0:1]:
                    self._fill_out(form, inline=field.label)

    def _execute(self, action):
        tokens = action.split(_(' in '))
        if find_model_by_add_label(tokens[0].strip()):
            if len(tokens) == 1:
                self._register(action)
            else:
                self._add(action)
        else:
            if len(tokens) == 1:
                self._execute_view(action)
            else:
                self._execute_action(action)

    def _execute_action(self, action):
        tokens = action.split(_(' in '))
        action_name = tokens[0].strip()
        verbose_name = tokens[1].strip()
        model = find_model_by_verbose_name(verbose_name)
        action_dict = find_action(model, action_name)
        func = action_dict['function']

        func_signature = '{}_em_{}(self)'.format(func.__name__.lower(), model.__name__.lower())
        self._test_flow_code.append('\t\t\t# {}'.format(action))
        self._test_flow_code.append('\t\t\tself.{}_em_{}()'.format(func.__name__.lower(), model.__name__.lower()))

        self._test_function_code.append('\tdef {}:'.format(func_signature))
        self._view(model, True)
        if hasattr(func, '_action'):
            button_label = func._action['title']
            params = func.__code__.co_varnames[1:func.__code__.co_argcount]
            if params:
                interaction = _('The user clicks the button')
                self._interactions.append('{} "{}"'.format(interaction, button_label))
                self._interactions.append(_('The system displays a popup window'))

                self._test_function_code.append("\t\tself.click_button('{}')".format(button_label))
                self._test_function_code.append("\t\tself.look_at_popup_window()")
                form = factory.get_action_form(self._mocked_request(), model(), func._action)
                self._fill_out(form)

            interaction = _('The user clicks the button')
            self._interactions.append('{} "{}"'.format(interaction, button_label))
            self._test_function_code.append("\t\tself.click_button('{}')".format(button_label))
            self._test_function_code.append("\t\tself.click_icon('{}')".format('Principal'))

            description = func.__doc__ and func.__doc__.strip() or ''
            business_rules = utils.extract_exception_messages(func)
            post_condition = _('Action successfully performed')
            self.name = action_dict['title']
            self.description = description
            self.business_rules = business_rules
            self.post_condition = post_condition
            for can_execute in action_dict['can_execute']:
                self.actors.append(can_execute)
            if not self.actors:
                self.actors.append(_('Superuser'))

    def _execute_view(self, action):
        pass

    def get_interactions_as_string(self):
        l = []
        for i, interaction in enumerate(self._interactions):
            l.append('\t\t\t{}. {}'.format(i+1, interaction))
        return '\n'.join(l)

    def get_test_flow_code(self):
        return self._test_flow_code

    def get_test_function_code(self):
        return self._test_function_code

    def as_dict(self):
        return dict(name=self.name, description=self.description, actors=self.actors,
                    business_rules=self.business_rules, pre_conditions=self.pre_conditions,
                    post_condition=self.post_condition, scenario=self.get_interactions_as_string())

    def __str__(self):
        l = list()
        l.append('')
        l.append('{}:\t\t\t{}'.format(terminal.info(_('Name')), self.name))
        l.append('{}:\t\t{}'.format(terminal.info(_('Description')), self.description or ''))
        l.append('{}:\t\t\t{}'.format(terminal.info(_('Actors')), ', '.join(self.actors)))
        l.append('{}:\t\t{}'.format(terminal.info(_('Buniness Rules')), ', '.join(self.business_rules)))
        l.append('{}:\t\t{}'.format(terminal.info(_('Pre-conditions')), ', '.join(self.pre_conditions)))
        l.append('{}:\t\t{}'.format(terminal.info(_('Post-condition')), (self.post_condition or '')))
        l.append('{}:'.format(terminal.info(_('Main-scenario'))))
        l.append(self.get_interactions_as_string())
        l.append('')
        return '\n'.join(l)


class Workflow(object):

    def __init__(self):

        translation.activate(settings.LANGUAGE_CODE)

        self.actors = []
        self.tasks = []
        tmp = None
        for task in loader.workflows:
            role = task['role']
            activity = task['activity']
            model = task['model']

            if role != tmp:
                tmp = role or _('Superuser')
                action = _('Acessar como')
                self.tasks.append('{} {}'.format(action, tmp))

            if model:
                action = '{}{}{}'.format(activity, _(' in '), model)
            else:
                action = activity
            self.tasks.append(action)


class ClassDiagram(object):

    POSITION_MAP = {
        1: (2.2,), 2: (1.2, 3.2,), 3: (3.2, 1.1, 1.3,), 4: (2.2, 3.2, 1.1, 1.3,), 5: (2.2, 1.1, 1.3, 3.1, 3.3,),
        6: (1.2, 3.2, 1.1, 3.1, 1.3, 3.3,), 7: (2.2, 1.2, 3.2, 1.1, 1.3, 3.1, 3.3,),
        8: (1.2, 3.2, 1.1, 1.3, 2.1, 2.3, 3.1, 3.3,), 9: (1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3,)
    }

    def __init__(self, class_diagram_name, models):

        self.name = class_diagram_name
        self.classes = []
        self.compositions = []
        self.agregations = []

        classes = dict()
        n = len(loader.class_diagrams[class_diagram_name])
        associations_count = {}
        for model in loader.class_diagrams[class_diagram_name]:
            associations_count[model] = 0

        for model in loader.class_diagrams[class_diagram_name]:
            verbose_name = get_metadata(model, 'verbose_name')
            related_objects = get_metadata(model, 'related_objects')
            classes[model] = dict(name=verbose_name, position='1.1')
            for related_object in related_objects:
                related_verbose_name = get_metadata(related_object.related_model, 'verbose_name')
                if related_object.related_model in models:
                    if hasattr(related_object.field, 'composition') and related_object.field.composition:
                        self.compositions.append(
                            [related_verbose_name, verbose_name, related_object.remote_field.name])
                        associations_count[model] += 1
                        associations_count[related_object.related_model] += 1
                    else:
                        if (model not in loader.role_models or class_diagram_name == related_verbose_name) or (
                                        class_diagram_name == verbose_name and related_object.related_model not in loader.role_models):
                            self.agregations.append(
                                [verbose_name, related_verbose_name, related_object.field.name])
                            associations_count[related_object.related_model] += 1
                            associations_count[model] += 1
        sorted_associations_count = sorted(associations_count, key=associations_count.get, reverse=True)
        for i, model in enumerate(sorted_associations_count):
            cls = classes[model]
            cls['position'] = ClassDiagram.POSITION_MAP[n][i]
            self.classes.append(cls)

    def as_dict(self):
        return dict(name=self.name, classes=self.classes, compositions=self.compositions, agregations=self.agregations)

    def as_json(self):
        return json.dumps(self.as_dict())


class Documentation(object):

    def __init__(self):

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

    def __str__(self):
        l = list()
        l.append(terminal.bold(_('Description:').upper()))
        l.append(terminal.info(self.description))
        l.append('')
        l.append(terminal.bold(_('Actors:').upper()))
        for i, actor in enumerate(self.actors):
            l.append('{}. {}'.format(i + 1, actor.name))
        l.append('')
        l.append(terminal.bold(_('Workflow:').upper()))
        for i, task in enumerate(self.workflow.tasks):
            l.append('{} {}'.format(' ' * i, task))
        l.append('')
        l.append(terminal.bold(_('Usecases:').upper()))
        for i, usecase in enumerate(self.usecases):
            l.append(terminal.bold('* Usecase #{}'.format((i + 1))))
            l.append('{}'.format(usecase))
        l.append('')
        l.append(terminal.bold(_('Class Diagrams:').upper()))
        for class_diagram in self.class_diagrams:
            l.append(terminal.bold('\t{} {}'.format(class_diagram.name, _('Diagram'))))
            for i, cls in enumerate(class_diagram.classes):
                l.append('\t\t\t{}. {}'.format(i + 1, cls['name']))
        return '\n'.join(l)

