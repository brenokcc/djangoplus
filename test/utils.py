# -*- coding: utf-8 -*-
import re
from os.path import join
from django.conf import settings
from django.utils.translation import ugettext as _
from djangoplus.docs.utils import workflow_as_string
from django.template.defaultfilters import slugify
from djangoplus.db.models import fields as model_fields
from djangoplus.utils.metadata import get_metadata, find_action, find_model_by_verbose_name, find_model_by_add_label, \
    get_field


class TestCaseGenerator(object):
    """ This class has the aim of generating testcases based on the user interaction with the system.
    The code generation is based on strings that defines actions of the user.
    The actions must follow the sintaxe bellow:
        Login as <group name>
        Register <class verbose name>
        Add <relation name> to <class verbose name>
        <action name> in <class verbose name>
        <action name>
        Logout
    Code generation is also compatible with Porguese and may also follow the sintaxe bellow
        Acessar como <nome do grupo>
        Cadastrar <nome amigável da classe>
        Adicionar <nome da relação> em <nome amigável da classe>
        <nome da ação> em <nome amigável da classe>
        <nome da ação>
        Sair
    Each interaction is codified in a separate function and it is called in the main flow of the test.
    """

    def __init__(self):
        self._function_definitions = []
        self._function_calls = []
        self._interactions = []

    def generate(self, actions=()):
        if actions:
            actions = '#'.join(actions)
        else:
            actions = '#'.join(workflow_as_string().replace('\t', '').split('\n'))
        pattern = u'(Acessar como \w+|Cadastrar [\w|\s\w|,]+|Adicionar [\w|\s\w]+|[\w|\s\w]+)'
        for action in re.findall(pattern, actions, re.UNICODE):
            s = action.strip()
            if s.startswith('Acessar como'):
                self._append_login_interaction(action)
            elif s == 'Sair':
                self._append_logout_interaction(action)
            elif s.startswith('Cadastrar'):
                verbose_name = s.replace('Cadastrar', '')
                verbose_name = verbose_name.strip()
                model = find_model_by_verbose_name(verbose_name)
                self._append_register_interaction(action, model)
            elif s.startswith('Adicionar'):
                s = s.replace('Adicionar', '')
                relation_name, verbose_name = s.split(u' em ')
                relation_name = relation_name.strip()
                verbose_name = verbose_name.strip()
                model = find_model_by_verbose_name(verbose_name)
                self._append_add_interaction(action, model, relation_name)
            elif u' em ' in s:
                action_name, verbose_name = s.split(u' em ')
                action_name = action_name.strip()
                verbose_name = verbose_name.strip()
                add_model = find_model_by_add_label(action_name)
                model = find_model_by_verbose_name(verbose_name)
                if add_model:
                    self._append_add_interaction(action_name, model, get_metadata(add_model, 'verbose_name'))
                else:
                    model = find_model_by_verbose_name(verbose_name)
                    func = find_action(model, action_name)
                    self._generate_action_interaction(action, model, func)
            else:
                model = find_model_by_add_label(s)
                if model:
                    self._append_register_interaction(action, model, add_label=s)
                else:
                    self._append_view_interaction(action)

    def save(self):
        test_file_path = join(settings.BASE_DIR, settings.PROJECT_NAME, 'tests.py')
        file_content = open(test_file_path).read().decode('utf-8')
        for function_definition in self._function_definitions:
            file_content = file_content.replace(u'(TestCase):', u'(TestCase):\n\n%s' % function_definition, 1)
        for function_call in self._function_calls:
            file_content = '%s\n%s' % (file_content, function_call)
        open(test_file_path, 'w').write(file_content.encode('utf-8'))

    def get_interactions_as_string(self):
        l = []
        for i, interaction in enumerate(self._interactions):
            l.append(u'%s. %s' % (i+1, interaction))
        return u'\n'.join(l)

    def _append_interactions(self, model, output, exclude_fields=(), fields=()):
        for field in get_metadata(model, 'get_fields'):
            add_field = False
            if fields:
                add_field = field.name in fields

            else:
                add_field = field.name not in exclude_fields
                if hasattr(field, 'exclude'):
                    add_field = add_field and not field.exclude

            if add_field:
                if isinstance(field, model_fields.ForeignKey) or isinstance(field, model_fields.ManyToManyField) or (hasattr(field, 'choices') and field.choices):
                    value = callable(field.example) and field.example() or field.example
                    if value:
                        output.append(u"self.choose(u'%s', u'%s')\n" % (field.verbose_name,  value))
                    action = _(u'The user chooses')
                    self._interactions.append(u'%s "%s"' % (action, field.verbose_name))
                elif isinstance(field, model_fields.CharField) or isinstance(field, model_fields.DateField) \
                        or isinstance(field, model_fields.DateTimeField) or isinstance(field, model_fields.IntegerField) \
                        or isinstance(field, model_fields.DecimalField) or isinstance(field, model_fields.TextField):
                    output.append(u"self.enter(u'%s', u'%s')\n" % (field.verbose_name, field.example or ''))
                    action = _(u'The user enters')
                    self._interactions.append(u'%s "%s"' % (action, field.verbose_name))

    def _append_menu_interaction(self, model, output):
        click_str = []
        click_str_unicode = []
        list_shortcut = get_metadata(model, 'list_shortcut')
        list_menu = get_metadata(model, 'list_menu')
        if list_shortcut:
            verbose_name_plural = get_metadata(model, 'verbose_name_plural')
            output.append(u'self.click_link(u\'%s\')\n' % verbose_name_plural)
            action = _(u'The user click the shortcut card')
            self._interactions.append(u'%s %s' % (action, model))
        elif list_menu:
            if type(list_menu) == tuple:
                list_menu = list_menu[0]
            for menu_item in list_menu.split('::'):
                click_str.append(u'"%s"' % menu_item)
                click_str_unicode.append(u"u'%s'" % menu_item)
            output.append(u'self.click_menu(%s)\n' % ', '.join(click_str_unicode))
            action = _(u'The user access the menu')
            self._interactions.append(u'%s %s' % (action, ', '.join(click_str)))

    def _append_login_interaction(self, action):
        verbose_name = action.split('como')[-1].strip()
        model = find_model_by_verbose_name(verbose_name)
        if model:
            role_username = get_metadata(model, 'role_username')
            if role_username:
                field = get_field(model, role_username)
                username = field.example or ''
            else:
                username = 'admin'
        else:
            username = 'admin'
        output = list('        # %s' % action)
        output.append("\n        if self.login(u'%s', u'senha'):" % username)
        action = _(u'The user access the system as')
        self._interactions.append(u'%s %s' % (action, verbose_name))
        self._interactions.append(_(u'The system displays the main page'))
        func_code = ''.join(output)
        self._function_calls.append(func_code)

    def _append_logout_interaction(self, action):
        output = list('            # %s' % action)
        output.append("\n            self.logout()")
        func_code = ''.join(output)
        self._function_calls.append(func_code)

    def _append_register_interaction(self, action, model, add_label=None):
        if add_label:
            func_name = slugify(add_label).replace('-', '_')
        else:
            func_name = u'cadastrar_%s' % model.__name__.lower()
        func_signature = u'%s(self)' % func_name
        func_call = u'            # %s\n            self.%s()' % (action, func_name)
        output = [u'    def %s:\n' % func_signature]
        button_label = add_label or u'Cadastrar'
        self._append_menu_interaction(model, output)
        self._interactions.append(_(u'The system displays previous registered records'))
        output.append(u"self.click_button(u'%s')\n" % button_label)
        a = _(u'The user clicks the button')
        b = _(u'on the right-side of the action bar')
        self._interactions.append(u'%s "%s" %s' % (a, button_label, b))
        self._interactions.append(_(u'The system displays the input form'))
        self._append_interactions(model, output)

        output.append(u"self.click_button(u'Cadastrar')\n")
        action = _(u'The user clicks the button')
        self._interactions.append(u'%s "%s"' % (action, button_label))
        output.append(u"self.click_icon(u'%s')" % 'Principal')
        func_code = '        '.join(output)
        self._function_calls.append(func_call)
        self._function_definitions.append(func_code)

    def _append_view_interaction(self, action):
        func_name = 'xxxx'
        func_call = u'            # %s\n            pass# self.%s()' % (action, func_name)
        self._function_calls.append(func_call)

    def _append_add_interaction(self, action, model, relation_name):
        panel_title = None
        if hasattr(model, 'fieldsets'):
            for fieldset in model.fieldsets:
                if 'relations' in fieldset[1]:
                    for item in fieldset[1]['relations']:
                        relation = getattr(model, item)
                        related_model = relation.rel.related_model
                        if get_metadata(related_model, 'verbose_name') == relation_name:
                            panel_title = fieldset[0]
                            break

        if panel_title:
            add_inline = get_metadata(related_model, 'add_inline')
            button_label = add_inline and u'Adicionar' or u'Salvar'
            func_signature = u'adicionar_%s_em_%s(self)' % (relation.rel.name.lower(), model.__name__.lower())
            func_call = u'            # %s\n            self.adicionar_%s_em_%s()' % (action, relation.rel.name.lower(), model.__name__.lower())
            output = [u'    def %s:\n' % func_signature]
            self._append_menu_interaction(model, output)
            output.append(u"self.click_icon(u'Visualizar')\n")
            output.append(u"self.look_at_panel(u'%s')\n" % panel_title)
            if not add_inline:
                add_button_label = u'Adicionar %s' % get_metadata(related_model, 'verbose_name')
                add_button_label = get_metadata(related_model, 'add_label', add_button_label)
                output.append(u"self.click_button(u'%s')\n" % add_button_label)
                output.append(u"self.look_at_popup_window()\n")
            self._append_interactions(related_model, output, exclude_fields=[model.__name__.lower()])
            output.append(u"self.click_button(u'%s')\n" % button_label)
            output.append(u"self.click_icon(u'%s')" % 'Principal')
            func_code = '        '.join(output)
            self._function_calls.append(func_call)
            self._function_definitions.append(func_code)

    def _generate_action_interaction(self, action, model, func):
        func_signature = u'%s_em_%s(self)' % (func.__name__.lower(), model.__name__.lower())
        func_call = u'            # %s\n            self.%s_em_%s()' % (action, func.__name__.lower(), model.__name__.lower())
        output = [u'    def %s:\n' % func_signature]
        if hasattr(func, '_action'):
            params = func.func_code.co_varnames[1:func.func_code.co_argcount]
            self._append_menu_interaction(model, output)
            output.append(u"self.click_icon(u'Visualizar')\n")
            if params:
                output.append(u"self.click_button(u'%s')\n" % func._action['title'])
                output.append(u"self.look_at_popup_window()\n")

                self._append_interactions(model, output, fields=params)

            output.append(u"self.click_button(u'%s')\n" % func._action['title'])
            output.append(u"self.click_icon(u'%s')" % 'Principal')
            func_code = '        '.join(output)
            self._function_calls.append(func_call)
            self._function_definitions.append(func_code)

