# -*- coding: utf-8 -*-
import json
from django.apps import apps
from django.conf import settings
from djangoplus.docs import utils
from djangoplus.cache import loader
from django.http import HttpRequest
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

    def __unicode__(self):
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

        if name.startswith('Acessar'):
            self._login(name)
        elif name.startswith('Listar'):
            self._list(name)
        elif name.startswith('Cadastrar'):
            self._register(name)
        elif name.startswith('Adicionar'):
            self._add(name)
        else:
            self._execute(name)

    def _mocked_request(self):
        if not self._request:
            self._request = HttpRequest()
            self._request.user = User(pk=0)
        return self._request

    def _debug(self):
        print u'\n'.join(self._interactions)
        print
        print u'\n'.join(self._test_function_code)
        print
        print u'\n'.join(self._test_flow_code)

    def _login(self, action):
        verbose_name = action.split('como')[-1].strip()
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

        interaction = _(u'The user access the system as')
        self._interactions.append(u'%s %s' % (interaction, verbose_name))
        self._interactions.append(_(u'The system displays the main page'))

        self._test_flow_code.append('\t\t# %s' % action)
        self._test_flow_code.append("\t\tif self.login(u'%s', u'%s'):" % (username, password))

    def _find(self, model):
        click_str = []
        click_str_unicode = []

        verbose_name = get_metadata(model, 'verbose_name')
        verbose_name_plural = get_metadata(model, 'verbose_name_plural')
        list_shortcut = get_metadata(model, 'list_shortcut', [], iterable=True)
        list_menu = get_metadata(model, 'list_menu')

        if not loader.last_authenticated_role or True in list_shortcut or loader.last_authenticated_role in list_shortcut:

            left = _(u'The user clicks on the shortcut card')
            right = _(u'in the dashboard at main page')
            interaction = u'%s "%s" %s' % (left, verbose_name_plural, right)
            self._interactions.append(interaction)

            self._interactions.append(_(u'The system displays the listing page'))

            self._test_function_code.append(u'\t\tself.click_link(u\'%s\')' % verbose_name_plural)

        elif list_menu:

            if type(list_menu) == tuple:
                list_menu = list_menu[0]
            for menu_item in list_menu.split('::'):
                click_str.append(u'"%s"' % menu_item)
                click_str_unicode.append(u"u'%s'" % menu_item)

            interaction = _(u'The user access the menu')
            self._interactions.append(u'%s %s' % (interaction, ', '.join(click_str)))

            self._test_function_code.append(u'\t\tself.click_menu(%s)' % ', '.join(click_str_unicode))

        else:
            raise ValueError(u'There is no way to access the model "%s", please do one of the following things:\n '
                             u'i) Add the "list_menu" meta-attribute to model\n '
                             u'ii) Add the "list_shortcut" meta-attribute to model\n '
                             u'iii) Add the "composotion" field attribute to one of foreignkey fields of the model if '
                             u'it exists and the the relation on the foreignkey model' % verbose_name)

    def _view(self, model, recursive=False):

        list_shortcut = get_metadata(model, 'list_shortcut', [])
        list_menu = get_metadata(model, 'list_menu')

        # if the model can be accessed by the menu or shortcut
        if list_shortcut or list_menu:
            self._find(model)
            self._interactions.append(_(u'The user locates the record and clicks the visualization icon'))
            self._interactions.append(_(u'The system displays the visualization page'))
            self._test_function_code.append(u"\t\tself.click_icon(u'%s')" % u'Visualizar')  # _(u'Visualize')
        else:
            # the model can be accesses only by a parent model
            for parent_model in loader.composition_relations:
                if model in loader.composition_relations[parent_model]:
                    self._view(parent_model, True)
                    panel_title = None
                    if hasattr(parent_model, 'fieldsets'):
                        for fieldset in parent_model.fieldsets:
                            if 'relations' in fieldset[1]:
                                for item in fieldset[1]['relations']:
                                    relation = getattr(parent_model, item)
                                    if relation.rel.related_model == model:
                                        panel_title = fieldset[0]
                                        break
                    if panel_title:
                        if '::' in panel_title:
                            tab_name, panel_title = panel_title.split('::')
                            self._test_function_code.append(u"\t\tself.click_tab(u'%s')" % tab_name)
                            interaction = _(u'The user clicks the tab')
                            self._interactions.append(u'%s "%s"' % (interaction, tab_name))
                        if panel_title:
                            interaction = _(u'The user looks at the painel')
                            self._interactions.append(u'%s "%s"' % (interaction, panel_title))
                            self._test_function_code.append(u"\t\tself.look_at_panel(u'%s')" % panel_title)

                    if recursive:
                        self._interactions.append(_(u'The user locates the record and clicks the visualization icon'))
                        self._interactions.append(_(u'The system displays the visualization page'))
                        self._test_function_code.append(u"\t\tself.click_icon(u'%s')" % u'Visualizar')  # _(u'Visualize')

    def _list(self, action):
        verbose_name_plural = action.replace(u'Listar', '').strip()

        if ':' in action:
            # it refers to a subset
            verbose_name_plural, subset_name = verbose_name_plural.split(':')
            verbose_name_plural = verbose_name_plural.strip()
            model = find_model_by_verbose_name_plural(verbose_name_plural)
            subset_name = subset_name.strip()
            subset = find_subset_by_title(subset_name, model)

            # set the attributes of the usecase
            self.description = subset['function'].__doc__.decode('utf-8').strip()
            for can_view in subset['can_view']:
                self.actors.append(can_view)
            if not self.actors:
                self.actors.append(u'Superusuário')

            # register the interactions and testing code
            self._find(model)

            interaction = _(u'The user clicks the pill')
            self._interactions.append('%s "%s"' % (interaction, subset_name))

            self._test_function_code.append(u"\t\tself.click_link(u'%s')" % subset_name)

        else:
            model = find_model_by_verbose_name_plural(verbose_name_plural)

            # set the attributes of the usecase
            self.description = u'List %s previouly registered in the system' % verbose_name_plural.lower()
            self.post_condition = _(u'The system displays the registered records')
            for meta_data in ('can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization',
                              'can_list', 'can_list_by_role', 'can_list_by_unit', 'can_list_by_organization'):
                for actor in get_metadata(model, meta_data, iterable=True):
                    if actor:
                        self.actors.append(actor)
            if not self.actors:
                self.actors.append(u'Superusuário')

            # register the interactions and testing code
            self._find(model)

        # register the interactions
        search_fields = utils.get_search_fields(model)
        if search_fields:
            interaction = _(u'The user optionally performs a search by')
            self._interactions.append(u'%s %s' % (interaction, search_fields))

        list_filter = utils.get_list_filter(model)
        if list_filter:
            interaction = _(u'The user optionally filter the records by')
            self._interactions.append(u'%s %s' % (interaction, list_filter))

        left = _(u'The system displays')
        right = _(u'of previous registered records')
        interaction = '%s %s %s' % (left, utils.get_list_display(model), right)
        self._interactions.append(interaction)

    def _register(self, action):

        model = find_model_by_add_label(action)
        if model:
            verbose_name = get_metadata(model, 'verbose_name')
            button_label = get_metadata(model, 'add_label')
            func_name = slugify(button_label).replace('-', '_')
        else:
            verbose_name = action.replace(u'Cadastrar', u'').strip()
            model = find_model_by_verbose_name(verbose_name)
            button_label = u'Cadastrar'
            func_name = u'cadastrar_%s' % model.__name__.lower()

        # set the attributes of the usecase
        self.name = action
        self.description = u'Add new records of %s in the system' % verbose_name.lower()
        self.business_rules = utils.extract_exception_messages(model.save)
        self.post_condition = u'The record will be successfully registered in the system'
        required_data = []
        for field in get_metadata(model, 'get_fields'):
            if isinstance(field, model_fields.ForeignKey) and not isinstance(field, model_fields.OneToOneField) and not isinstance(field, model_fields.OneToManyField):
                required_data.append(field.verbose_name.lower())
        if required_data:
            pre_condition = _(u'The following information must have been previouly registered in the system: ')
            self.pre_conditions.append('%s %s' % (pre_condition, u', '.join(required_data)))

        for meta_data in ('can_admin', 'can_admin_by_role', 'can_admin_by_unit', 'can_admin_by_organization', 'can_add',
                          'can_add_by_role', 'can_add_by_unit', 'can_add_by_organization'):
            for actor in get_metadata(model, meta_data, iterable=True):
                if actor:
                    self.actors.append(actor)
        if not self.actors:
            self.actors.append(u'Superusuário')

        # register the interactions and testing code
        func_signature = u'%s(self)' % func_name
        self._test_flow_code.append(u'\t\t\t# %s' % action)
        self._test_flow_code.append(u'\t\t\tself.%s()' % func_name)

        self._test_function_code.append('\tdef %s:' % func_signature)
        self._find(model)
        self._test_function_code.append(u"\t\tself.click_button(u'%s')" % button_label)

        a = _(u'The user clicks the button')
        b = _(u'on the right-side of the action bar')
        self._interactions.append(u'%s "%s" %s' % (a, button_label, b))

        form = factory.get_register_form(self._mocked_request(), model())
        self._fill_out(form)

        interaction = _(u'The user clicks the button')
        self._interactions.append(u'%s "%s"' % (interaction, button_label))
        self._test_function_code.append(u"\t\tself.click_button(u'%s')" % button_label)
        self._test_function_code.append(u"\t\tself.click_icon(u'%s')" % u'Principal')

    def _add(self, action):

        model = None

        if action.startswith('Adicionar'):
            # not add_label was defined for the related model
            tokens = action.replace('Adicionar', '').split(' em ')
            verbose_name = tokens[0].strip()
            if len(tokens) > 1:
                relation_verbose_name = tokens[1].strip()
                model = find_model_by_verbose_name(relation_verbose_name)
            related_model = find_model_by_verbose_name(verbose_name)
        else:
            # an add_label was defined for the related model
            tokens = action.split(' em ')
            add_label = tokens[0].strip()
            if len(tokens) > 1:
                verbose_name = tokens[1].strip()
                model = find_model_by_verbose_name(verbose_name)
            related_model = find_model_by_add_label(add_label)

        # check if there is a fieldset was defined with the relation
        rel = None
        if hasattr(model, 'fieldsets'):
            for fieldset in model.fieldsets:
                if 'relations' in fieldset[1]:
                    for item in fieldset[1]['relations']:
                        tmp = getattr(model, item)
                        if tmp.rel.related_model == related_model:
                            rel = tmp.rel

        # if the relation was defined in a fieldset
        if rel:
            add_inline = get_metadata(related_model, 'add_inline')
            add_label = get_metadata(related_model, 'add_label')
            button_label = add_label or u'Adicionar'
            button_label = get_metadata(related_model, 'add_label', button_label)

            function_signature = u'adicionar_%s_em_%s' % (related_model.__name__.lower(), model.__name__.lower())
            self._test_flow_code.append(u'\t\t\t# %s' % action)
            self._test_flow_code.append(u'\t\t\tself.%s()' % function_signature)

            self._test_function_code.append(u'\tdef %s(self):' % function_signature)

            self._view(related_model)

            # the form is not in the visualization page and it must be opened
            if not add_inline:
                add_button_label = u'Adicionar %s' % get_metadata(related_model, 'verbose_name')
                add_button_label = get_metadata(related_model, 'add_label', add_button_label)

                interaction = _(u'The user clicks the button')
                self._interactions.append(u'%s "%s"' % (interaction, add_button_label))
                self._interactions.append(_(u'The system displays a popup window'))

                self._test_function_code.append(u"\t\tself.click_button(u'%s')" % add_button_label)
                self._test_function_code.append(u"\t\tself.look_at_popup_window()")

            form = factory.get_many_to_one_form(self._mocked_request(), model(), rel, related_model())
            self._fill_out(form)

            interaction = _(u'The user clicks the button')
            self._interactions.append(u'%s "%s"' % (interaction, button_label))

            self._test_function_code.append(u"\t\tself.click_button(u'%s')" % button_label)
            self._test_function_code.append(u"\t\tself.click_icon(u'%s')" % u'Principal')
        else:
            raise ValueError(u'Please add the %s\'s relation in the fieldsets of model %s' % (related_model.__name__,
                             model.__name__))

    def _fill_out(self, form, inline=None):

        if not inline:
            self._interactions.append(_(u'The system displays the input form'))

        form.contextualize()
        form.configure()

        for fieldset in form.configured_fieldsets:
            if inline or fieldset['title']:
                if fieldset['tuples'] and fieldset['tuples'][0]:
                    interaction = _('The user looks at fieldset')
                    self._interactions.append(u'%s "%s"' % (interaction, inline or fieldset['title']))

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
                            self._test_function_code.append(u"\t\tself.choose(u'%s', u'%s')" % (form_field.label, value))
                            interaction = _(u'The user chooses')
                            self._interactions.append(u'%s "%s"' % (interaction, form_field.label))
                        else:
                            if not isinstance(form_field, form_fields.BooleanField) and not isinstance(form_field, form_fields.NullBooleanField):
                                self._test_function_code.append(u"\t\tself.enter(u'%s', u'%s')" % (form_field.label, value))
                                interaction = _(u'The user enters')
                                self._interactions.append(u'%s "%s"' % (interaction, form_field.label))

            # add the interactions recursively if the form inner forms
            for field, form, required, save in fieldset.get('one_to_one', ()):
                self._fill_out(form, inline=field.label)
            for field, one_to_many_forms in fieldset.get('one_to_many', ()):
                for form in one_to_many_forms[0:1]:
                    self._fill_out(form, inline=field.label)

    def _execute(self, action):
        tokens = action.split(u' em ')
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
        tokens = action.split(u' em ')
        action_name = tokens[0].strip()
        verbose_name = tokens[1].strip()
        model = find_model_by_verbose_name(verbose_name)
        action_dict = find_action(model, action_name)
        func = action_dict['function']

        func_signature = u'%s_em_%s(self)' % (func.__name__.lower(), model.__name__.lower())
        self._test_flow_code.append(u'\t\t\t# %s' % action)
        self._test_flow_code.append(u'\t\t\tself.%s_em_%s()' % (func.__name__.lower(), model.__name__.lower()))

        self._test_function_code.append(u'\tdef %s:' % func_signature)
        self._view(model, True)
        if hasattr(func, '_action'):
            button_label = func._action['title']
            params = func.func_code.co_varnames[1:func.func_code.co_argcount]
            if params:
                interaction = _(u'The user clicks the button')
                self._interactions.append(u'%s "%s"' % (interaction, button_label))
                self._interactions.append(_(u'The system displays a popup window'))

                self._test_function_code.append(u"\t\tself.click_button(u'%s')" % button_label)
                self._test_function_code.append(u"\t\tself.look_at_popup_window()")
                form = factory.get_action_form(self._mocked_request(), model(), func._action)
                self._fill_out(form)

            interaction = _(u'The user clicks the button')
            self._interactions.append(u'%s "%s"' % (interaction, button_label))
            self._test_function_code.append(u"\t\tself.click_button(u'%s')" % button_label)
            self._test_function_code.append(u"\t\tself.click_icon(u'%s')" % u'Principal')

            description = func.__doc__ and func.__doc__.decode('utf-8').strip() or ''
            business_rules = utils.extract_exception_messages(func)
            post_condition = u'Ação realizada com sucesso'
            self.name = action_dict['title']
            self.description = description
            self.business_rules = business_rules
            self.post_condition = post_condition
            for can_execute in action_dict['can_execute']:
                self.actors.append(can_execute)
            if not self.actors:
                self.actors.append(u'Superusuário')

    def _execute_view(self, action):
        pass

    def get_interactions_as_string(self):
        l = []
        for i, interaction in enumerate(self._interactions):
            l.append(u'\t\t\t%s. %s' % (i+1, interaction))
        return u'\n'.join(l)

    def get_test_flow_code(self):
        return self._test_flow_code

    def get_test_function_code(self):
        return self._test_function_code

    def as_dict(self):
        return dict(name=self.name, description=self.description, actors=self.actors,
                    business_rules=self.business_rules, pre_conditions=self.pre_conditions,
                    post_condition=self.post_condition, scenario=self.get_interactions_as_string())

    def __unicode__(self):
        l = list()
        l.append(u'')
        l.append(u'Name:\t\t\t%s' % self.name)
        l.append(u'Description:\t\t%s' % (self.description or u''))
        l.append(u'Actors:\t\t\t%s' % u', '.join(self.actors))
        l.append(u'Buniness Rules:\t\t%s' % u', '.join(self.business_rules))
        l.append(u'Pre-conditions:\t\t%s' % u', '.join(self.pre_conditions))
        l.append(u'Post-condition:\t\t%s' % (self.post_condition or ''))
        l.append(u'Main-scenario:')
        l.append(self.get_interactions_as_string())
        l.append(u'')
        return u'\n'.join(l)


class Workflow(object):

    def __init__(self):
        self.actors = []
        self.tasks = []
        tmp = None
        for task in loader.workflows:
            role = task['role']
            activity = task['activity']
            model = task['model']

            if role != tmp:
                tmp = role or u'Superusuário'
                action = u'Acessar como %s' % tmp
                self.tasks.append(action)

            if model:
                action = u'%s em %s' % (activity, model)
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
        self.description = None
        self.workflow = None
        self.actors = []
        self.usecases = []
        self.class_diagrams = []

        # load description
        for app_config in apps.get_app_configs():
            if app_config.label == settings.PROJECT_NAME:
                self.description = app_config.module.__doc__ and app_config.module.__doc__.decode('utf-8').strip() or None

        # load actors
        organization_name = loader.organization_model and get_metadata(loader.organization_model, 'verbose_name') or None
        unit_name = loader.unit_model and get_metadata(loader.unit_model, 'verbose_name') or None

        for model in loader.role_models:

            name = loader.role_models[model]['name']
            description = model.__doc__ and not model.__doc__.decode('utf-8').startswith(u'%s(' % model.__name__) and model.__doc__.decode('utf-8').replace(u'\t', u'').replace(u'\n', u'').replace(u'  ', u' ').strip() or ''
            scope = ''
            if organization_name:
                scope = loader.role_models[model]['scope']
                if scope == u'systemic':
                    scope = u'Sistêmico'
                elif scope == u'organization':
                    scope = organization_name
                elif scope == u'unit':
                    scope = unit_name
            self.actors.append(Actor(name=name, scope=scope, description=description))

        # load usecases
        self.workflow = Workflow()
        for task in self.workflow.tasks:
            if not task.startswith(u'Acessar'):
                usecase = UseCase(task)
                self.usecases.append(usecase)

        # load class diagrams
        for class_diagram_name, models in loader.class_diagrams.items():
            class_diagram = ClassDiagram(class_diagram_name, models)
            self.class_diagrams.append(class_diagram)

    def as_dict(self):
        return dict(description=self.description, actors=[actor.as_dict() for actor in self.actors],
                    usecases=[usecase.as_dict() for usecase in self.usecases],
                    class_diagrams=[class_diagram.as_json() for class_diagram in self.class_diagrams])

    def as_json(self):
        return json.dumps(self.as_dict())

    def __unicode__(self):
        l = list()
        l.append(u'Description:')
        l.append(self.description)
        l.append('')
        l.append(u'Actors:')
        for i, actor in enumerate(self.actors):
            l.append(u'%s. %s' % (i + 1, actor.name))
        l.append('')
        l.append(u'Workflow:')
        for i, task in enumerate(self.workflow.tasks):
            l.append(u'%s %s' % (u' ' * i, task))
        l.append('')
        l.append(u'Usecases:')
        for i, usecase in enumerate(self.usecases):
            l.append(u'* Usecase #%s' % (i + 1))
            l.append(u'%s' % usecase)
        l.append('')
        l.append(u'Class Diagrams:')
        for class_diagram in self.class_diagrams:
            l.append(u'\t%s Diagram' % class_diagram.name)
            for i, cls in enumerate(class_diagram.classes):
                l.append(u'\t\t\t%s. %s' % (i + 1, cls['name']))
        return '\n'.join(l)

