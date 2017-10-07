# -*- coding: utf-8 -*-
import json
import datetime
from django.db.models import Q
from djangoplus.db import models
from django.core.mail import send_mail
from django.conf import settings
from operator import __or__ as OR
from djangoplus.decorators import action, meta, subset
from django.utils.translation import ugettext_lazy as _
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

    OPERATION_CHOICES = [[ADD, u'Cadastro'], [EDIT, u'Edição'], [DELETE, u'Exclusão']]

    content_type = models.ForeignKey(ContentType, verbose_name=u'Objeto', filter=True)
    operation = models.IntegerField(verbose_name=u'Operação', choices=OPERATION_CHOICES, filter=True)
    user = models.ForeignKey('admin.User', filter=True)
    date = models.DateTimeField(verbose_name=u'Data/Hora', auto_now=True, filter=True)
    object_id = models.IntegerField(verbose_name=u'Identificador', search=True)
    object_description = models.CharField(verbose_name=u'Descrição do Objeto')
    content = models.TextField(verbose_name=u'Conteúdo', null=True)

    fieldsets = (
        (u'Dados Gerais', {'fields': (
        ('content_type', 'operation'), ('user', 'date'), ('object_id', 'object_description'), 'get_tags')}),
        (u'Índices', {'relations': ('logindex_set',)}),
    )

    objects = models.Manager()

    class Meta:
        verbose_name = u'Log'
        verbose_name_plural = u'Logs'
        icon = 'fa-history'
        list_per_page = 25

    def __unicode__(self):
        return 'Log #%s' % self.pk

    def can_add(self):
        return False

    def can_edit(self):
        return False

    def can_delete(self):
        return False

    def get_action_description(self):
        return (u'adicionou', u'editou', u'removeu')[self.operation - 1]

    def get_style(self):
        return ('success', 'info', 'danger')[self.operation - 1]

    def get_icon(self):
        return ('plus', 'pencil', 'trash-o')[self.operation - 1]

    @meta(u'Tags', formatter='log_tags')
    def get_tags(self):
        return json.loads(self.content)

    def create_indexes(self, instance):
        for log_index in get_metadata(instance.__class__, 'logging', (), iterable=True):
            index_object = getattr2(instance, log_index)
            if index_object:
                index_content_type = ContentType.objects.get_for_model(index_object.__class__)
                LogIndex.objects.create(log=self, content_type=index_content_type, object_id=index_object.pk)


class LogIndex(models.Model):
    log = models.ForeignKey(Log, verbose_name=u'Log', composition=True)
    content_type = models.ForeignKey('contenttypes.ContentType', verbose_name=u'Dado')
    object_id = models.IntegerField(verbose_name=u'Identificador', search=True)

    class Meta:
        verbose_name = u'Index'
        verbose_name_plural = u'Indexes'

    def __unicode__(self):
        return u'Index #%s' % self.pk


class Organization(models.AsciiModel):
    class Meta:
        verbose_name = u'Organização'
        verbose_name_plural = u'Organizações'

    @classmethod
    def subclass(cls):
        return cls.__subclasses__() and cls.__subclasses__()[0] or None

    def get_units(self):
        unit_subclass = Unit.subclass()
        if unit_subclass:
            for field in get_metadata(unit_subclass, 'fields'):
                if hasattr(field, 'rel') and field.rel and hasattr(field.rel.to, 'organization_ptr'):
                    return field.rel.related_model.objects.filter(**{field.name:self.pk})
        return Unit.objects.none()

    def __unicode__(self):
        if self.pk == 0:
            return u'Todas'
        else:
            return super(Organization, self).__unicode__()


class Unit(models.AsciiModel):
    class Meta:
        verbose_name = u'Unidade'
        verbose_name_plural = u'Unidades'

    @classmethod
    def subclass(cls):
        return cls.__subclasses__() and cls.__subclasses__()[0] or None

    def get_organization(self):
        organization_subclass = Organization.subclass()
        if organization_subclass:
            for field in get_metadata(type(self), 'fields'):
                if hasattr(field, 'rel') and field.rel and hasattr(field.rel, 'to') and field.rel.to == organization_subclass:
                    return getattr(self, field.name)
        return None

    def __unicode__(self):
        if self.pk == 0:
            return u'Todas'
        else:
            return super(Unit, self).__unicode__()


class UserManager(DjangoUserManager):

    def all(self, *args, **kwargs):
        return super(UserManager, self).all()

    def get_queryset(self):
        return models.QuerySet(self.model, using=self._db)

    @subset(u'Ativos')
    def active(self):
        return self.filter(active=True)

    @subset(u'Inativos')
    def inactive(self):
        return self.filter(active=False)

    def create_user(self, username, email, password=None, is_superuser=False):
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, active=True, is_superuser=is_superuser,
                          last_login=datetime.datetime.now())
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        return self.create_user(username, email, password, True)


class User(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    name = models.CharField(u'Nome', max_length=30, blank=True, search=True)
    username = models.CharField(u'Login', max_length=30, unique=True)
    email = models.CharField(u'E-mail', max_length=75, blank=True, default='')
    active = models.BooleanField(verbose_name=u'Ativo?', default=True, filter=True)
    photo = models.ImageField(upload_to='profiles', null=True, blank=True, default='', verbose_name=u'Foto', exclude=True)

    permission_mapping = models.TextField(verbose_name=u'Mapeamento de Permissão', default='{}', exclude=True, display=False)
    organization = models.ForeignKey(Organization, verbose_name=u'Organização', null=True, blank=True, display=False)
    unit = models.ForeignKey(Unit, verbose_name=u'Unidade', null=True, blank=True, display=False)

    objects = UserManager()

    fieldsets = (
        (u'Identificação', {'fields': (('name', 'email'),)}),
        (u'Acesso', {'fields': (('username', 'is_superuser'), ('active',))}),
        (u'Funções', {'relations': ('role_set',)}),
        (u'Mapeamento de Permissão', {'fields': (('organization', 'unit'), 'permission_mapping')}),
    )

    class Meta():
        verbose_name = u'Usuário'
        verbose_name_plural = u'Usuários'
        list_display = 'username', 'name', 'groups'
        add_form = 'UserForm'
        can_admin = 'Gerenciador de Usuários'
        icon = 'fa-user'

    def save(self, *args, **kwargs):
        super(User, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name or self.username

    @action('Alterar Senha', input='ChangePasswordForm', inline=True)
    def change_password(self, new_password, confirm_password):
        self.set_password(new_password)
        self.save()

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
        import json
        permission_mapping = json.loads(self.permission_mapping or '{}')
        permission_mapping_key = obj and '%s:%s' % (model.__name__, type(obj).__name__) or model.__name__
        if 0 and permission_mapping_key in permission_mapping:
            return permission_mapping[permission_mapping_key]

        organization_lookups = []
        unit_lookups = []
        role_lookups = dict()
        lookups = dict(list_lookups=[], edit_lookups=[], delete_lookups=[])

        for lookup in get_metadata(model, 'list_lookups', (), iterable=True):
            field = get_field(model, lookup)
            if hasattr(field.rel.to, 'organization_ptr') or hasattr(field.rel.to, 'unit_ptr'):
                if hasattr(field.rel.to, 'organization_ptr'):
                    organization_lookups.append(lookup)
                if hasattr(field.rel.to, 'unit_ptr'):
                    unit_lookups.append(lookup)
            else:
                role_username = get_metadata(field.rel.to, 'role_username')
                if role_username:
                    role_lookups[get_metadata(field.rel.to, 'verbose_name')] = '%s__%s' % (lookup, role_username)
                for subclass in field.rel.to.__subclasses__():
                    role_username = get_metadata(subclass, 'role_username')
                    if role_username:
                        role_lookups[get_metadata(subclass, 'verbose_name')] = '%s__%s__%s' % (
                            lookup, subclass.__name__.lower(), role_username)

        if hasattr(model, 'organization_ptr') and 'id' not in organization_lookups:
            organization_lookups.append('id')

        if hasattr(model, 'unit_ptr') and 'id' not in unit_lookups:
            unit_lookups.append('id')

        if get_metadata(model, 'role_username') and 'id' not in role_lookups:
            role_lookups[get_metadata(model, 'verbose_name')] = get_metadata(model, 'role_username')

        for field in get_metadata(model, 'fields'):
            if hasattr(field, 'rel') and field.rel and hasattr(field.rel, 'to') and field.rel.to:
                if field.rel.to in loader.role_models:
                    role_lookups[get_metadata(field.rel.to, 'verbose_name')] = '%s__%s' % (field.name, loader.role_models[field.rel.to]['username_field'])
                if field.rel.to in loader.abstract_role_models:
                    for to in loader.abstract_role_models[field.rel.to]:
                        role_lookups[get_metadata(to, 'verbose_name')] = '%s__%s__%s' % (
                            field.name, to.__name__.lower(), loader.role_models[to])
                if hasattr(field.rel.to, 'unit_ptr_id') and field.name not in unit_lookups:
                    unit_lookups.append(field.name)
                if hasattr(field.rel.to, 'organization_ptr_id') and field.name not in organization_lookups:
                    organization_lookups.append(field.name)

        for organization_lookup in organization_lookups:
            if loader.unit_model:
                if organization_lookup == 'id':
                    unit_lookup = loader.unit_model.__name__.lower()
                else:
                    unit_lookup = '%s__%s' % (organization_lookup, loader.unit_model.__name__.lower())
                if unit_lookup not in unit_lookups and not hasattr(model, 'unit_ptr'):
                    unit_lookups.append(unit_lookup)

        for unit_lookup in unit_lookups:
            if loader.organization_model:
                if unit_lookup == 'id':
                    organization_lookup = loader.organization_model.__name__.lower()
                else:
                    organization_lookup = '%s__%s' % (unit_lookup, loader.organization_model.__name__.lower())
                if organization_lookup not in organization_lookups and not hasattr(model, 'organization_ptr'):
                    organization_lookups.append(organization_lookup)

        groups = dict()
        for group_name, organization_id, unit_id in self.role_set.values_list('group__name', 'organizations', 'units'):
            if group_name not in groups:
                groups[group_name] = dict(username_lookups=[], organization_ids=[], unit_ids=[])
            if group_name in role_lookups:
                groups[group_name]['username_lookups'].append(role_lookups[group_name])
            if organization_id and not self.unit_id and (organization_id == self.organization_id or not self.organization_id):
                groups[group_name]['organization_ids'].append(organization_id)
            if self.unit_id or unit_id:
                groups[group_name]['unit_ids'].append(self.unit_id or unit_id)

        if model in loader.permissions_by_scope:
            for group_name in groups:

                username_lookups = groups[group_name]['username_lookups']
                unit_ids = list(set(groups[group_name]['unit_ids']))
                organization_ids = list(set(groups[group_name]['organization_ids']))

                if obj:

                    can_list = can_list_by_role = can_list_by_unit = can_list_by_organization = False

                    if type(obj) in loader.permissions_by_scope:
                        can_list = group_name in loader.permissions_by_scope[type(obj)].get('add', [])
                        can_list_by_role = group_name in loader.permissions_by_scope[type(obj)].get('add_by_role', [])
                        can_list_by_unit = group_name in loader.permissions_by_scope[type(obj)].get('add_by_unit', [])
                        can_list_by_organization = group_name in loader.permissions_by_scope[type(obj)].get('add_by_organization', [])

                        if (can_list or can_list_by_role or can_list_by_unit or can_list_by_organization) is False:
                            can_list = group_name in loader.permissions_by_scope[type(obj)].get('list', [])
                            can_list_by_role = group_name in loader.permissions_by_scope[type(obj)].get('list_by_role', [])
                            can_list_by_unit = group_name in loader.permissions_by_scope[type(obj)].get('list_by_unit', [])
                            can_list_by_organization = group_name in loader.permissions_by_scope[type(obj)].get('list_by_organization', [])

                    if (can_list or can_list_by_role or can_list_by_unit or can_list_by_organization) is False:
                        can_list = group_name in loader.permissions_by_scope[model].get('list', [])
                        can_list_by_role = group_name in loader.permissions_by_scope[model].get('list_by_role', [])
                        can_list_by_unit = group_name in loader.permissions_by_scope[model].get('list_by_unit', [])
                        can_list_by_organization = group_name in loader.permissions_by_scope[model].get('list_by_organization', [])

                else:
                    can_list = group_name in loader.permissions_by_scope[model].get('list', [])
                    can_list_by_role = group_name in loader.permissions_by_scope[model].get('list_by_role', [])
                    can_list_by_unit = group_name in loader.permissions_by_scope[model].get('list_by_unit', [])
                    can_list_by_organization = group_name in loader.permissions_by_scope[model].get('list_by_organization', [])

                if can_list:
                    lookups['list_lookups'] = []
                else:
                    if can_list_by_role:
                        for username_lookup in username_lookups:
                            lookups['list_lookups'].append((username_lookup, (self.username,)))
                    if can_list_by_unit or self.unit_id:
                        if unit_ids and 0 not in unit_ids:
                            for unit_lookup in unit_lookups:
                                lookups['list_lookups'].append(('%s' % unit_lookup, unit_ids))
                    if can_list_by_organization:
                        if organization_ids and 0 not in organization_ids:
                            for organization_lookup in organization_lookups:
                                lookups['list_lookups'].append(('%s' % organization_lookup, organization_ids))

                can_edit = group_name in loader.permissions_by_scope[model].get('edit', [])
                can_edit_by_role = group_name in loader.permissions_by_scope[model].get('edit_by_role', [])
                can_edit_by_unit = group_name in loader.permissions_by_scope[model].get('edit_by_unit', [])
                can_edit_by_organization = group_name in loader.permissions_by_scope[model].get('edit_by_organization', [])

                if can_edit:
                    lookups['edit_lookups'] = None
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
                    lookups['delete_lookups'] = None
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
                        for key in actions_dict[model][category].keys():
                            execute_lookups = []
                            view_name = actions_dict[model][category][key]['view_name']
                            can_execute = group_name in loader.permissions_by_scope[model].get('%s' % view_name, [])
                            can_execute_by_role = group_name in loader.permissions_by_scope[model].get('%s_by_role' % view_name, [])
                            can_execute_by_unit = group_name in loader.permissions_by_scope[model].get('%s_by_unit' % view_name, [])
                            can_execute_by_organization = group_name in loader.permissions_by_scope[model].get('%s_by_organization' % view_name, [])
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

            if loader.permissions_by_scope[model].get('list_by_unit') and not unit_lookups:
                raise Exception('A "lookup" meta-attribute must point to a Unit model in %s' % model)
            if loader.permissions_by_scope[model].get('list_by_organization') and (not organization_lookups and not unit_lookups):
                raise Exception('A "lookup" meta-attribute must point to a Unit or Organization model in %s' % model)
            if loader.permissions_by_scope[model].get('list_by_role') and not role_lookups:
                raise Exception('A "lookup" meta-attribute must point to a role model in %s' % model)

        permission_mapping[permission_mapping_key] = lookups

        self.permission_mapping = json.dumps(permission_mapping)
        self.save()

        return permission_mapping[permission_mapping_key]

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


def role_list_display():
    from djangoplus.cache import loader
    list_display = ['user', 'group']
    if loader.organization_model:
        list_display.append('get_organizations')
    if loader.unit_model:
        list_display.append('get_units')
    return list_display


class Role(models.Model):
    user = models.ForeignKey('admin.User', verbose_name=u'Usuário', composition=True)
    group = models.ForeignKey('admin.Group', verbose_name=u'Grupo')
    organizations = models.ManyToManyField(Organization, through='admin.OrganizationRole', verbose_name=u'Organizações', exclude=True, blank=True)
    units = models.ManyToManyField(Unit, through='admin.UnitRole', verbose_name=u'Unidades', exclude=True, blank=True)

    fieldsets = (
        (u'Dados Gerais', {'fields': ('user', 'group')}),
        (u'Organizações', {'fields': ('organizations',)}),
        (u'Unidades', {'fields': ('units',)}),
    )

    objects = models.Manager()

    class Meta:
        verbose_name = u'Função'
        verbose_name_plural = u'Funções'
        db_table = 'admin_user_groups'
        managed = False
        list_display = role_list_display
        can_admin = u'Gerenciador de Usuários'

    def __unicode__(self):
        return u'%s' % self.group

    @meta(u'Organizações')
    def get_organizations(self):
        return self.organizations.all()

    @meta(u'Unidades')
    def get_units(self):
        return self.units.all()

    def can_edit(self):
        return False

    def can_add(self):
        return True

    def can_define_organizations(self):
        return Organization.objects.exclude(pk=0).exists()

    def can_define_roles(self):
        return Unit.objects.exclude(pk=0).exists()

    @action(u'Definir Organizações', condition='can_define_organizations', message=u'Organização(ões) definida(s) com sucesso.', inline=True)
    def define_organizations(self, organizations):
        self.organizationrole_set.all().delete()
        for organization in organizations:
            OrganizationRole.objects.get_or_create(role=self, organization=organization)

    @action(u'Definir Unidades', condition='can_define_roles', message=u'Unidade(s) definida(s) com sucesso.', inline=True)
    def define_units(self, units):
        self.unitrole_set.all().delete()
        for unit in units:
            UnitRole.objects.get_or_create(role=self, unit=unit)


class OrganizationRole(models.Model):
    role = models.ForeignKey(Role, verbose_name=u'Função', composition=True)
    organization = models.ForeignKey(Organization, verbose_name=u'Organização')

    class Meta:
        verbose_name = u'Papel na Organização'
        verbose_name_plural = u'Papeis na Organização'

    def __unicode__(self):
        return u'%s - %s' % (self.role, self.organization)


class UnitRole(models.Model):
    role = models.ForeignKey(Role, verbose_name=u'Função', composition=True)
    unit = models.ForeignKey(Unit, verbose_name=u'Unidade')

    class Meta:
        verbose_name = u'Função na Unidade'
        verbose_name_plural = u'Funções na Unidade'

    def __unicode__(self):
        return u'%s - %s' % (self.role, self.unit)


class PermissionManager(models.Manager):

    def get_queryset(self):
        app_labels = []
        for app_label in settings.INSTALLED_APPS:
            if '.' not in app_label:
                app_labels.append(app_label)
        return super(PermissionManager, self).get_queryset().filter(content_type__app_label__in=app_labels)

    # @action(u'Give to Users')
    def give_to_users(self):
        pass


class Permission(Permission):
    class Meta:
        verbose_name = u'Permissão'
        verbose_name_plural = u'Permissões'
        proxy = True
        icon = 'fa-check'

    fieldsets = (
        (u'Dados Gerais', {'fields': ('name',)}),
        (u'Usuários', {'relations': ('user_set',)}),
    )

    objects = PermissionManager()
setattr(Permission._meta, 'search_fields', ['codename', 'name'])
setattr(Permission._meta, 'list_filter', ['content_type'])


class Group(Group):
    class Meta:
        verbose_name = u'Grupo'
        verbose_name_plural = u'Grupos'
        proxy = True
        icon = 'fa-users'
        add_form = 'GroupForm'

    fieldsets = (
        (u'Dados Gerais', {'fields': ('name',)}),
        (u'Permissões::Permissões', {'relations': ('permissions',)}),
        (u'Usuários::Usuários', {'relations': ('user_set',)}),
    )

    objects = models.Manager()


class Settings(models.Model):

    class Meta:
        verbose_name = u'Configuração'
        verbose_name_plural = u'Configurações'

    fieldsets = (
        (u'Configuração Geral', {'fields': (('initials', 'name'), ('logo', 'logo_pdf'), ('icon', 'background'))}),
        (u'Social', {'fields': (('twitter', 'facebook'), ('google', 'pinterest'), ('linkedin', 'rss'))}),
        (u'Contato', {'fields': (('phone_1', 'phone_2'), 'address', 'email')}),
        (u'Aparência', {'fields': ('default_color',)}),
        (u'Servidor', {'fields': (('server_address', 'system_email_address'),)}),
        (u'Versão', {'fields': ('version',)}),
    )

    # Application
    initials = models.CharField(u'Nome', default=u'Django+')
    name = models.CharField(u'Descrição', default=u'Django Plus')
    logo = models.ImageField(u'Logotipo', upload_to='config', null=True, blank=True, default='')
    logo_pdf = models.ImageField(u'Logotipo para PDF', upload_to='config', help_text=u'Imagem sem fundo transparente',
                                 null=True, blank=True, default='')
    icon = models.ImageField(u'Ícone', upload_to='config', null=True, blank=True)
    background = models.ImageField(u'Background', upload_to='config', default='', blank=True)

    # Social params
    twitter = models.CharField(u'Twitter', null=True, blank=True)
    facebook = models.CharField(u'Facebook', null=True, blank=True)
    google = models.CharField(u'Google', null=True, blank=True)
    pinterest = models.CharField(u'pinterest', null=True, blank=True)
    linkedin = models.CharField(u'Linkedin', null=True, blank=True)
    rss = models.CharField(u'RSS', null=True, blank=True)

    # Contact info
    address = models.TextField(u'Endereço', null=True, blank=True)
    phone_1 = models.PhoneField(u'Telefone Principal', null=True, blank=True)
    phone_2 = models.PhoneField(u'Telefone Secundário', null=True, blank=True)
    email = models.CharField(u'E-mail', null=True, blank=True)

    # Server configuration
    version = models.CharField(u'Versão do Sistema', exclude=True)
    server_address = models.CharField(u'Endereço de Acesso', default=u'http://localhost:8000')
    system_email_address = models.CharField(u'E-mail de Notificação', default=u'no-reply@djangoplus.net')

    @staticmethod
    def default():
        qs = Settings.objects.all()
        if qs.exists():
            return qs[0]
        else:
            settings = Settings()
            settings.initials = u'Sistema'
            settings.name = u'Sistema de gerenciamento online, responsivo e multiplataforma'
            settings.twitter = u'https://twitter.com/'
            settings.facebook = u'https://www.facebook.com/'
            settings.google = u'https://plus.google.com/'
            settings.pinterest = u'https://www.pinterest.com/'
            settings.linkedin = u'https://www.linkedin.com/'
            settings.rss = u'https://www.rss.com/'
            settings.address = u''
            settings.phone_1 = u''
            settings.phone_2 = u''
            settings.email = u''
            settings.version = '1.0'
            settings.save()
            return settings