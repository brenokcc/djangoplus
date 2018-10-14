# -*- coding: utf-8 -*-
import sys
import json
import uuid
from djangoplus.utils.aescipher import encrypt
from djangoplus.utils.mail import send_mail
from djangoplus.db import models
from django.conf import settings
from djangoplus.decorators import action, meta, subset
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.models import ContentTypeManager
from djangoplus.utils.metadata import get_metadata, getattr2, get_field
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, \
    UserManager as DjangoUserManager, Group, Permission


class ContentTypeManager(ContentTypeManager):
    pass


class ContentType(ContentType):
    class Meta:
        proxy = True

    objects = ContentTypeManager()


class Log(models.Model):
    ADD = 1
    EDIT = 2
    DELETE = 3

    OPERATION_CHOICES = [[ADD, 'Cadastro'], [EDIT, 'Edição'], [DELETE, 'Exclusão']]

    content_type = models.ForeignKey(ContentType, verbose_name='Objeto', filter=True)
    operation = models.IntegerField(verbose_name='Operação', choices=OPERATION_CHOICES, filter=True)
    user = models.ForeignKey('admin.User', filter=True)
    date = models.DateTimeField(verbose_name='Data/Hora', auto_now=True, filter=True)
    object_id = models.IntegerField(verbose_name='Identificador', search=True)
    object_description = models.CharField(verbose_name='Descrição do Objeto')
    content = models.TextField(verbose_name='Conteúdo', null=True)

    fieldsets = (
        ('Dados Gerais', {'fields': (
        ('content_type', 'operation'), ('user', 'date'), ('object_id', 'object_description'), 'get_tags')}),
        ('Índices', {'relations': ('logindex_set',)}),
    )

    objects = models.Manager()

    class Meta:
        verbose_name = 'Log'
        verbose_name_plural = 'Logs'
        icon = 'fa-history'
        list_per_page = 25

    def __str__(self):
        return 'Log #{}'.format(self.pk)

    def can_add(self):
        return False

    def can_edit(self):
        return False

    def can_delete(self):
        return False

    def get_action_description(self):
        return ('adiciono', 'editou', 'removeu')[self.operation - 1]

    def get_style(self):
        return ('success', 'info', 'danger')[self.operation - 1]

    def get_icon(self):
        return ('plus', 'pencil', 'trash-o')[self.operation - 1]

    @meta('Tags')
    def get_tags(self):
        return json.loads(self.content)

    def create_indexes(self, instance):
        for log_index in get_metadata(instance.__class__, 'logging', (), iterable=True):
            index_object = getattr2(instance, log_index)
            if index_object:
                index_content_type = ContentType.objects.get_for_model(index_object.__class__)
                LogIndex.objects.create(log=self, content_type=index_content_type, object_id=index_object.pk)


class LogIndex(models.Model):
    log = models.ForeignKey(Log, verbose_name='Log', composition=True)
    content_type = models.ForeignKey('contenttypes.ContentType', verbose_name='Dado')
    object_id = models.IntegerField(verbose_name='Identificador', search=True)

    class Meta:
        verbose_name = 'Index'
        verbose_name_plural = 'Indexes'

    def __str__(self):
        return 'Index #{}'.format(self.pk)


class Scope(models.AsciiModel):
    class Meta:
        verbose_name = 'Scope'
        verbose_name_plural = 'Scopes'


class Organization(Scope):
    class Meta:
        verbose_name = 'Organização'
        verbose_name_plural = 'Organizações'

    @classmethod
    def subclass(cls):
        return cls.__subclasses__() and cls.__subclasses__()[0] or None

    def get_units(self):
        unit_subclass = Unit.subclass()
        if unit_subclass:
            for field in get_metadata(unit_subclass, 'fields'):
                if field.remote_field and hasattr(field.remote_field.model, 'organization_ptr'):
                    return unit_subclass.objects.filter(**{field.name:self.pk})
        return Unit.objects.none()


class Unit(Scope):
    class Meta:
        verbose_name = 'Unidade'
        verbose_name_plural = 'Unidades'

    @classmethod
    def subclass(cls):
        return cls.__subclasses__() and cls.__subclasses__()[0] or None

    def get_organization(self):
        organization_subclass = Organization.subclass()
        if organization_subclass:
            for field in get_metadata(type(self), 'fields'):
                if field.remote_field and field.remote_field.model == organization_subclass:
                    return getattr(self, field.name)
        return None

    @classmethod
    def get_organization_field_name(cls):
        organization_subclass = Organization.subclass()
        unit_subclass = cls.subclass()
        if organization_subclass and unit_subclass:
            for field in get_metadata(unit_subclass, 'fields'):
                if field.remote_field and field.remote_field.model == organization_subclass:
                    return field.name
        return None


class UserManager(DjangoUserManager):

    def all(self, *args, **kwargs):
        return super(UserManager, self).all()

    def get_queryset(self):
        return models.QuerySet(self.model, using=self._db)

    @subset('Ativos')
    def active(self):
        return self.filter(active=True)

    @subset('Inativos')
    def inactive(self):
        return self.filter(active=False)

    def create_user(self, username, email, password=None, is_superuser=False):
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, active=True, is_superuser=is_superuser,
                          last_login=None)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        return self.create_user(username, email, password, True)


class User(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    name = models.CharField('Nome', max_length=30, blank=True, search=True)
    username = models.CharField('Login', max_length=30, unique=True, search=True)
    email = models.CharField('E-mail', max_length=75, blank=True, default='')
    active = models.BooleanField(verbose_name='Ativo?', default=True, filter=True)
    photo = models.ImageField(upload_to='profiles', null=True, blank=True, default='/static/images/user.png', verbose_name='Foto', exclude=True)

    permission_mapping = models.JsonField(verbose_name='Mapeamento de Permissão', exclude=True, display=False)
    objects = UserManager()

    fieldsets = (
        ('Identificação', {'fields': (('name', 'email'),), 'image':'photo'}),
        ('Acesso', {'fields': (('username', 'is_superuser'), ('active',))}),
        ('Funções', {'relations': ('role_set',)}),
        ('Mapeamento de Permissão', {'fields': ('permission_mapping',)}),
    )

    class Meta():
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        list_display = 'photo', 'username', 'name', 'email', 'groups'
        add_form = 'UserForm'
        can_admin = 'Gerenciador de Usuários'
        icon = 'fa-users'
        # list_template = 'image_cards.html'

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.password:
            if settings.DEBUG or 'test' in sys.argv:
                password = settings.DEFAULT_PASSWORD
            else:
                password = uuid.uuid4().get_hex()
            self.set_password(password)
        super(User, self).save(*args, **kwargs)
        if self.is_superuser:
            group = Group.objects.get_or_create(name='Superuser')[0]
            self.groups.add(group)

    def __str__(self):
        return self.name or self.username

    @action('Alterar Senha', input='ChangePasswordForm', inline=True)
    def change_password(self, new_password, confirm_password):
        self.set_password(new_password)
        self.save()

    @action('Enviar Convite de Acesso', inline=True, condition='email', category=None)
    def send_access_invitation(self):
        self.send_access_invitation_for_group(None)

    def send_access_invitation_for_group(self, group):
        project_name = Settings.default().initials
        subject = 'Acesso ao Sistema - "{}"'.format(project_name)
        if group:
            message = '''Você foi cadastrado no sistema <b>{}</b> como <b>{}</b>.
                Caso já seja um usuário, clique no botão "Acessar agora!" para acessar o sistema.
                Caso nunca tenha acessado o sistema, clique no botão "Definir senha!" para informar sua senha de acesso.
            '''.format(project_name, group)
            actions = [
                ('Acessar agora!', '/admin/'),
                ('Definir senha!', '/admin/password/{}/{}/'.format(self.pk, encrypt(self.password)))
            ]
        else:
            message = '''Você foi cadastrado no sistema <b>{}</b>.
                Para (re)definir sua senha de acesso, clique no botão abaixo.
            '''.format(project_name)
            actions = [('Acessar agora!', '/admin/password/{}/{}/'.format(self.pk, encrypt(self.password)))]
        send_mail(subject, message, self.email, actions=actions)

    def units(self, group_name=None):
        qs = self.role_set.all()
        if group_name:
            qs = qs.filter(group__name=group_name)
        return qs.values_list('units', flat=True)

    def in_group(self, *group_names):
        return self.role_set.filter(group__name__in=group_names).exists()

    def in_other_group(self, group_name):
        return self.is_superuser or self.role_set.exclude(group__name=group_name).exists()

    def get_permission_mapping(self, model, obj=None):
        from djangoplus.cache import loader
        permission_mapping_key = obj and '{}:{}'.format(model.__name__, type(obj).__name__) or model.__name__
        if not settings.DEBUG and permission_mapping_key in self.permission_mapping:
            return self.permission_mapping[permission_mapping_key]

        organization_lookups = []
        unit_lookups = []
        role_lookups = dict()
        lookups = dict(list_lookups=[], edit_lookups=[], delete_lookups=[])

        for lookup in get_metadata(model, 'list_lookups', (), iterable=True):
            field = get_field(model, lookup)
            if hasattr(field.remote_field.model, 'organization_ptr') or hasattr(field.remote_field.model, 'unit_ptr'):
                if hasattr(field.remote_field.model, 'organization_ptr'):
                    organization_lookups.append(lookup)
                if hasattr(field.remote_field.model, 'unit_ptr'):
                    unit_lookups.append(lookup)
            else:
                role_username = get_metadata(field.remote_field.model, 'role_username')
                if role_username:
                    role_lookups[get_metadata(field.remote_field.model, 'verbose_name')] = '{}__{}'.format(lookup, role_username)
                for subclass in field.remote_field.model.__subclasses__():
                    role_username = get_metadata(subclass, 'role_username')
                    if role_username:
                        role_lookups[get_metadata(subclass, 'verbose_name')] = '{}__{}__{}'.format(
                            lookup, subclass.__name__.lower(), role_username)

        if hasattr(model, 'organization_ptr') and 'id' not in organization_lookups:
            organization_lookups.append('id')

        if hasattr(model, 'unit_ptr') and 'id' not in unit_lookups:
            unit_lookups.append('id')

        if get_metadata(model, 'role_username') and 'id' not in role_lookups:
            role_lookups[get_metadata(model, 'verbose_name')] = get_metadata(model, 'role_username')

        for field in get_metadata(model, 'fields') + get_metadata(model, 'many_to_many'):
            if field.remote_field and field.remote_field.model:
                if field.remote_field.model in loader.role_models:
                    role_lookups[get_metadata(field.remote_field.model, 'verbose_name')] = '{}__{}'.format(field.name, loader.role_models[field.remote_field.model]['username_field'])
                if field.remote_field.model in loader.abstract_role_models:
                    for to in loader.abstract_role_models[field.remote_field.model]:
                        role_lookups[get_metadata(to, 'verbose_name')] = '{}__{}__{}'.format(
                            field.name, to.__name__.lower(), loader.role_models[to])
                if hasattr(field.remote_field.model, 'unit_ptr_id') and field.name not in unit_lookups:
                    unit_lookups.append(field.name)
                if hasattr(field.remote_field.model, 'organization_ptr_id') and field.name not in organization_lookups:
                    organization_lookups.append(field.name)

        for organization_lookup in organization_lookups:
            if loader.unit_model:
                for field in get_metadata(loader.organization_model, 'fields'):
                    if field.remote_field and hasattr(field.remote_field.model, 'unit_ptr'):
                        if organization_lookup == 'id':
                            unit_lookup = field.name
                        else:
                            unit_lookup = '{}__{}'.format(organization_lookup, field.name)
                        if unit_lookup not in unit_lookups and not hasattr(model, 'unit_ptr'):
                            unit_lookups.append(unit_lookup)
                        break

        for unit_lookup in unit_lookups:
            if loader.organization_model:
                for field in get_metadata(loader.unit_model, 'fields'):
                    if field.remote_field and hasattr(field.remote_field.model, 'organization_ptr'):
                        if unit_lookup == 'id':
                            organization_lookup = field.name
                        else:
                            organization_lookup = '{}__{}'.format(unit_lookup, field.name)
                        if organization_lookup not in organization_lookups and not hasattr(model, 'organization_ptr'):
                            organization_lookups.append(organization_lookup)

        groups = dict()
        unit_organization_lookup = 'scope__organization'
        unit_organization_field_name = Unit.get_organization_field_name()
        if loader.unit_model and unit_organization_field_name:
            unit_organization_lookup = 'scope__unit__{}__{}'.format(
                loader.unit_model.__name__.lower(), unit_organization_field_name
            )
        scope_queryset = self.role_set.filter(
            active=True).values_list('group__name', 'scope__organization', 'scope__unit', unit_organization_lookup)
        for group_name, organization_id, unit_id, unit_organization_id in scope_queryset:
            if group_name not in groups:
                groups[group_name] = dict(username_lookups=[], organization_ids=[], unit_ids=[])
            if group_name in role_lookups:
                groups[group_name]['username_lookups'].append(role_lookups[group_name])
            if organization_id:
                groups[group_name]['organization_ids'].append(organization_id)
            if unit_id:
                groups[group_name]['unit_ids'].append(unit_id)
                if unit_organization_id:
                    groups[group_name]['organization_ids'].append(unit_organization_id)

        if model in loader.permissions_by_scope:
            can_view_globally = can_edit_globally = can_delete_globally = False
            for group_name in groups:

                username_lookups = groups[group_name]['username_lookups']
                unit_ids = list(set(groups[group_name]['unit_ids']))
                organization_ids = list(set(groups[group_name]['organization_ids']))

                can_view = can_view_by_role = can_view_by_unit = can_view_by_organization = False

                if obj:

                    if type(obj) in loader.permissions_by_scope:
                        can_view = group_name in loader.permissions_by_scope[type(obj)].get('add', [])
                        can_view_by_unit = group_name in loader.permissions_by_scope[type(obj)].get('add_by_unit', [])
                        can_view_by_organization = group_name in loader.permissions_by_scope[type(obj)].get('add_by_organization', [])

                if (can_view or can_view_by_role or can_view_by_unit or can_view_by_organization) is False:
                    can_view = group_name in loader.permissions_by_scope[model].get('view', [])
                    can_view_by_role = group_name in loader.permissions_by_scope[model].get('view_by_role', [])
                    can_view_by_unit = group_name in loader.permissions_by_scope[model].get('view_by_unit', [])
                    can_view_by_organization = group_name in loader.permissions_by_scope[model].get('view_by_organization', [])

                if can_view:
                    can_view_globally = True
                else:
                    if can_view_by_role:
                        for username_lookup in username_lookups:
                            lookups['list_lookups'].append((username_lookup, (self.username,)))
                    if can_view_by_unit:
                        if unit_ids:
                            for unit_lookup in unit_lookups:
                                lookups['list_lookups'].append(('{}'.format(unit_lookup), unit_ids))
                    if can_view_by_organization:
                        if organization_ids:
                            for organization_lookup in organization_lookups:
                                lookups['list_lookups'].append(('{}'.format(organization_lookup), organization_ids))

                can_edit = group_name in loader.permissions_by_scope[model].get('edit', [])
                can_edit_by_role = group_name in loader.permissions_by_scope[model].get('edit_by_role', [])
                can_edit_by_unit = group_name in loader.permissions_by_scope[model].get('edit_by_unit', [])
                can_edit_by_organization = group_name in loader.permissions_by_scope[model].get('edit_by_organization', [])

                if can_edit:
                    can_edit_globally = True
                else:
                    if can_edit_by_role:
                        for username_lookup in username_lookups:
                            lookups['edit_lookups'].append((username_lookup, (self.username,)))
                    if can_edit_by_unit and unit_ids:
                        for unit_lookup in unit_lookups:
                            lookups['edit_lookups'].append((unit_lookup, unit_ids))
                    if can_edit_by_organization and organization_ids:
                        for organization_lookup in organization_lookups:
                            lookups['edit_lookups'].append((organization_lookup, organization_ids))

                can_delete = group_name in loader.permissions_by_scope[model].get('delete', [])
                can_delete_by_role = group_name in loader.permissions_by_scope[model].get('delete_by_role', [])
                can_delete_by_unit = group_name in loader.permissions_by_scope[model].get('delete_by_unit', [])
                can_delete_by_organization = group_name in loader.permissions_by_scope[model].get('delete_by_organization', [])

                if can_delete:
                    can_delete_globally = True
                else:
                    if can_delete_by_role:
                        for username_lookup in username_lookups:
                            lookups['delete_lookups'].append((username_lookup, (self.username,)))
                    if can_delete_by_unit and unit_ids:
                        for unit_lookup in unit_lookups:
                            lookups['delete_lookups'].append((unit_lookup, unit_ids))
                    if can_delete_by_organization and organization_ids:
                        for organization_lookup in organization_lookups:
                            lookups['delete_lookups'].append((organization_lookup, organization_ids))

                for actions_dict in (loader.actions, loader.class_actions):
                    for category in actions_dict.get(model, ()):
                        for key in list(actions_dict[model][category].keys()):
                            execute_lookups = []
                            view_name = actions_dict[model][category][key]['view_name']
                            can_execute = group_name in loader.permissions_by_scope[model].get('{}'.format(view_name), [])
                            can_execute_by_role = group_name in loader.permissions_by_scope[model].get('{}_by_role'.format(view_name), [])
                            can_execute_by_unit = group_name in loader.permissions_by_scope[model].get('{}_by_unit'.format(view_name), [])
                            can_execute_by_organization = group_name in loader.permissions_by_scope[model].get('{}_by_organization'.format(view_name), [])
                            if can_execute:
                                execute_lookups = None
                            else:
                                if can_execute_by_role:
                                    for username_lookup in username_lookups:
                                        execute_lookups.append((username_lookup, (self.username,)))
                                if can_execute_by_unit and unit_ids:
                                    for unit_lookup in unit_lookups:
                                        execute_lookups.append((unit_lookup, unit_ids))
                                if can_execute_by_organization and organization_ids:
                                    for organization_lookup in organization_lookups:
                                        execute_lookups.append((organization_lookup, organization_ids))
                            if execute_lookups:
                                if view_name not in lookups:
                                    lookups[view_name] = []
                                lookups[view_name] += execute_lookups

            if can_view_globally:
                lookups['list_lookups'] = []
            if can_edit_globally:
                lookups['edit_lookups'] = []
            if can_delete_globally:
                lookups['delete_lookups'] = []

        for codename in ('view', 'list'):
            if model in loader.permissions_by_scope:
                if loader.permissions_by_scope[model].get('{}_by_unit'.format(codename)) and not unit_lookups:
                    raise Exception('A "lookup" meta-attribute must point to a Unit model in {}'.format(model))
                if loader.permissions_by_scope[model].get('{}_by_organization'.format(codename)) and (not organization_lookups and not unit_lookups):
                    raise Exception('A "lookup" meta-attribute must point to a Unit or Organization model in {}'.format(model))
                if loader.permissions_by_scope[model].get('{}_by_role'.format(codename)) and not role_lookups:
                    raise Exception('A "lookup" meta-attribute must point to a role model in {}'.format(model))

        self.permission_mapping[permission_mapping_key] = lookups
        self.save()

        return self.permission_mapping[permission_mapping_key]

    # gieve a set of group or permission names, this method returns the groups the user belongs to
    def find_groups(self, perm_or_group, exclude=None):
        qs = self.groups.all()
        if perm_or_group:
            permissions = []
            groups = []
            for item in perm_or_group:
                if '.' in item:
                    permissions.append(item.split('.')[1])
                else:
                    groups.append(item)
            if permissions:
                qs = qs.filter(permissions__codename__in=permissions)
            if groups:
                qs = qs.filter(name__in=groups)

        if exclude:
            qs = qs.exclude(name=exclude)
        return qs

    def email_user(self, subject, message, from_email=None, **kwargs):
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def check_role_groups(self):
        for group in self.groups.all():
            self.groups.remove(group)
        for group in self.role_set.filter(active=True).values_list('group', flat=True).distinct():
            self.groups.add(group)


class Role(models.Model):
    user = models.ForeignKey('admin.User', verbose_name='Usuário', composition=True)
    group = models.ForeignKey('admin.Group', verbose_name='Grupo')
    scope = models.ForeignKey('admin.Scope', verbose_name='Scope', null=True, blank=True)
    active = models.BooleanField(verbose_name='Active', default=True)
    fieldsets = (
        ('Dados Gerais', {'fields': ('user', 'group')}),
        ('Scope', {'fields': ('scope', 'active')}),
    )

    objects = models.Manager()

    class Meta:
        verbose_name = 'Função'
        verbose_name_plural = 'Funções'
        can_admin = 'Gerenciador de Usuários'

    def save(self, *args, **kwargs):
        super(Role, self).save(*args, **kwargs)
        if self.active:
            self.user.groups.add(self.group)

    def __str__(self):
        return '{}'.format(self.group)


class PermissionManager(models.Manager):

    def get_queryset(self):
        app_labels = []
        for app_label in settings.INSTALLED_APPS:
            if '.' not in app_label:
                app_labels.append(app_label)
        return super(PermissionManager, self).get_queryset().filter(content_type__app_label__in=app_labels)

    # @action('Give to Users')
    def give_to_users(self):
        pass


class Permission(Permission):
    class Meta:
        verbose_name = 'Permissão'
        verbose_name_plural = 'Permissões'
        proxy = True
        icon = 'fa-check'

    fieldsets = (
        ('Dados Gerais', {'fields': ('name',)}),
        ('Usuários', {'relations': ('user_set',)}),
    )

    objects = PermissionManager()

setattr(Permission._meta, 'search_fields', ['codename', 'name'])
setattr(Permission._meta, 'list_filter', ['content_type'])


class Group(Group):
    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        proxy = True
        icon = 'fa-users'
        add_form = 'GroupForm'

    fieldsets = (
        ('Dados Gerais', {'fields': ('name',)}),
        ('Permissões::Permissões', {'relations': ('permissions',)}),
        ('Usuários::Usuários', {'relations': ('user_set',)}),
    )

    objects = models.Manager()


class Settings(models.Model):

    class Meta:
        verbose_name = 'Configuração'
        verbose_name_plural = 'Configurações'

    fieldsets = (
        ('Configuração Geral', {'fields': (('initials', 'name'), ('logo', 'logo_pdf'), ('icon', 'background'))}),
        ('Social', {'fields': (('twitter', 'facebook'), ('google', 'pinterest'), ('linkedin', 'rss'))}),
        ('Direitos Autorais', {'fields': ('company', ('phone_1', 'phone_2'), 'address', 'email')}),
        ('Aparência', {'fields': ('default_color',)}),
        ('Servidor', {'fields': (('server_address', 'system_email_address'),)}),
        ('Versão', {'fields': ('version',)}),
    )

    # Application
    initials = models.CharField('Nome', default='Django+')
    name = models.CharField('Descrição', default='Django Plus')
    logo = models.ImageField('Logotipo', upload_to='config', null=True, blank=True, default='')
    logo_pdf = models.ImageField('Logotipo para PDF', upload_to='config', help_text='Imagem sem fundo transparente',
                                 null=True, blank=True, default='')
    icon = models.ImageField('Ícone', upload_to='config', null=True, blank=True)
    background = models.ImageField('Background', upload_to='config', default='', blank=True)

    # Social params
    twitter = models.CharField('Twitter', null=True, blank=True)
    facebook = models.CharField('Facebook', null=True, blank=True)
    google = models.CharField('Google', null=True, blank=True)
    pinterest = models.CharField('pinterest', null=True, blank=True)
    linkedin = models.CharField('Linkedin', null=True, blank=True)
    rss = models.CharField('RSS', null=True, blank=True)

    # Company
    company = models.CharField('Empresa', null=True, blank=True)
    address = models.TextField('Endereço', null=True, blank=True)
    phone_1 = models.PhoneField('Telefone Principal', null=True, blank=True)
    phone_2 = models.PhoneField('Telefone Secundário', null=True, blank=True)
    email = models.CharField('E-mail', null=True, blank=True)

    # Server configuration
    version = models.CharField('Versão do Sistema', exclude=True)
    server_address = models.CharField('Endereço de Acesso', default='http://localhost:8000')
    system_email_address = models.CharField('E-mail de Notificação', default='no-reply@djangoplus.net')

    @staticmethod
    def default():
        from djangoplus.cache import loader
        if not loader.settings_instance:
            loader.settings_instance = Settings.objects.first()
        if not loader.settings_instance:
            settings = Settings()
            settings.initials = 'Sistema'
            settings.name = 'Sistema de gerenciamento online, responsivo e multiplataforma'
            settings.twitter = 'https://twitter.com/'
            settings.facebook = 'https://www.facebook.com/'
            settings.google = 'https://plus.google.com/'
            settings.pinterest = 'https://www.pinterest.com/'
            settings.linkedin = 'https://www.linkedin.com/'
            settings.rss = 'https://www.rss.com/'
            settings.company = ''
            settings.address = ''
            settings.phone_1 = ''
            settings.phone_2 = ''
            settings.email = ''
            settings.version = '1.0'
            settings.save()
            loader.settings_instance = settings
        return loader.settings_instance

    def save(self, *args, **kwargs):
        from djangoplus.cache import loader
        super(Settings, self).save(*args, **kwargs)
        loader.settings_instance = self
