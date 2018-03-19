# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import six
import sys
from django.core.exceptions import ValidationError
from django.db.models import base
from django.db.models import Q
from django.conf import settings
from django.db.models import query
from operator import __or__ as OR
from djangoplus.db.models.fields import *
import django.db.models.options as options
from django.db.models.aggregates import Sum, Avg
from django.db.models.deletion import Collector
from djangoplus.utils.metadata import get_metadata, getattr2, find_model, get_field
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

setattr(options, 'DEFAULT_NAMES', options.DEFAULT_NAMES + (
    'icon', 'verbose_female', 'order_by', 'pdf', 'menu',
    'list_display', 'list_per_page', 'list_template', 'list_total', 'list_shortcut', 'list_csv', 'list_xls', 'list_menu', 'list_lookups', 'list_pdf',
    'add_label', 'add_form', 'add_inline', 'add_message', 'add_shortcut', 'select_template', 'select_display',
    'role_name', 'role_username', 'role_email', 'role_scope', 'role_signup',
    'log', 'logging',
    'can_add', 'can_edit', 'can_delete', 'can_list', 'can_view', 'can_admin',
    'can_list_by_role', 'can_view_by_role', 'can_add_by_role', 'can_edit_by_role', 'can_admin_by_role',
    'can_list_by_unit', 'can_view_by_unit', 'can_add_by_unit', 'can_edit_by_unit', 'can_admin_by_unit',
    'can_list_by_organization', 'can_view_by_organization', 'can_add_by_organization', 'can_edit_by_organization', 'can_admin_by_organization',
    'sequence', 'class_diagram',
))


class QueryStatistics(object):
    def __init__(self, series, labels, groups=list(), title=None):
        self.title = title
        self.labels = labels
        self.groups = groups
        self.series = []
        self.xtotal = []
        self.ytotal = []

        for serie in series:
            self.add(serie)

    def add(self, serie, avg=False):
        self.series.append(serie)
        if avg:
            self.xtotal.append(sum(serie)/len(serie))
        else:
            self.xtotal.append(sum(serie))
        if not self.ytotal:
            for value in serie:
                self.ytotal.append(value)
        else:
            for i, value in enumerate(serie):
                self.ytotal[i] += value

    def total(self):
        return sum(self.xtotal)

    def __unicode__(self):
        return '{}\n{}\n{}'.format(self.labels, self.series, self.groups)

    def as_table(self, title=None, symbol=None):
        from djangoplus.ui.components.utils import StatisticsTable
        return StatisticsTable(None, self.title, self, symbol=symbol)

    def as_chart(self, title=None, symbol=None):
        return self.as_table(title=title, symbol=symbol).as_chart()


class ModelGeneratorWrapper:
    def __init__(self, generator, user):
        self.generator = generator
        self.user = user

    def __iter__(self):
        return self

    def next(self):
        obj = self.generator.next()
        obj._user = self.user
        return obj


class ModelIterable(query.ModelIterable):

    def __iter__(self):
        generator = super(ModelIterable, self).__iter__()
        return ModelGeneratorWrapper(generator, self.queryset.user)


class QuerySet(query.QuerySet):

    def __init__(self, *args, **kwargs):
        self.user = None
        super(QuerySet, self).__init__(*args, **kwargs)
        self._iterable_class = ModelIterable

    def _clone(self):
        clone = super(QuerySet, self)._clone()
        clone.user = self.user
        return clone

    def all(self, user=None, obj=None):
        app_label = get_metadata(self.model, 'app_label')
        if user:
            role_username = get_metadata(user, 'role_username')
            if role_username:
                user = get_user_model().objects.get(username=getattr(user, role_username))
        queryset = self._clone()
        queryset.user = user
        if user:
            self_permission = '{}.view_{}'.format(app_label, self.model.__name__.lower())
            obj_permission = obj and '{}.view_{}'.format(get_metadata(type(obj), 'app_label'), type(obj).__name__.lower())
            has_perm = obj_permission and user.has_perm(obj_permission) or user.has_perm(self_permission)
        else:
            has_perm = True
        if has_perm:
            if user and (user.organization_id or user.unit_id or not user.is_superuser):
                permission_mapping = user.get_permission_mapping(self.model, obj)
                if 'list_lookups' in permission_mapping and permission_mapping['list_lookups']:
                    l = []
                    for lookup, value in permission_mapping['list_lookups']:
                        l.append(Q(**{'{}__in'.format(lookup): value}))
                    return queryset.filter(reduce(OR, l))
            return queryset
        return self.none()
     
    def _calculate(self, vertical_key=None, horizontal_key=None, aggregate=None):
        verbose_name = get_metadata(self.model,  'verbose_name')
        if not vertical_key:
            if aggregate:
                value = 0
                mode, attr = aggregate
                if mode == 'sum':
                    value = self.aggregate(Sum(attr)).get('{}__sum'.format(attr)) or 0
                elif mode == 'avg':
                    value = self.aggregate(Avg(attr)).get('{}__avg'.format(attr)) or 0
                aggregation_field = get_field(self.model, attr)
                if type(aggregation_field).__name__ in ('DecimalField',):
                    value = Decimal(value)
                return value
            return None
        vertical_field = get_field(self.model, vertical_key)
        if type(vertical_field).__name__ in ('DateField', 'DateTimeField'):
            months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

            if horizontal_key:
                iterator_model = get_field(self.model, horizontal_key).rel.to
                iterators = iterator_model.objects.filter(pk__in=self.values_list(horizontal_key, flat=True).order_by(horizontal_key).distinct())
                horizontal_field = get_field(self.model, horizontal_key)
                title = '{} anual por {}'.format(verbose_name, horizontal_field.verbose_name)
                statistics = QueryStatistics([], [unicode(x) for x in iterators], months, title=title)

                for iterator in iterators:
                    serie = []
                    for i, month in enumerate(months):
                        qs = self.filter(**{'{}__month'.format(vertical_key): i+1, horizontal_key: iterator.pk})
                        serie.append(qs.count())
                    statistics.add(serie)
                return statistics
            else:
                title = '{} Anual'.format(verbose_name)
                statistics = QueryStatistics([], months, title=title)
                serie = []
                for i, month in enumerate(months):
                    if aggregate:
                        total = 0
                        mode, attr = aggregate
                        if mode == 'sum':
                            total = self.filter(**{'{}__month'.format(vertical_key): i+1}).aggregate(Sum(attr)).get('{}__sum'.format(attr)) or 0
                        elif mode == 'avg':
                            total = self.filter(**{'{}__month'.format(vertical_key): i+1}).aggregate(Avg(attr)).get('{}__avg'.format(attr)) or 0
                        aggregation_field = get_field(self.model, attr)
                        if type(aggregation_field).__name__ in ('DecimalField',):
                            total = Decimal(total)
                    else:
                        total = self.filter(**{'{}__month'.format(vertical_key): i+1}).count()
                    serie.append(total)
                statistics.add(serie)
                return statistics
        else:
            if vertical_field.choices:
                vertical_choices = vertical_field.choices
            elif vertical_field.__class__.__name__ == 'BooleanField':
                vertical_choices = [(True, 'Sim'), (False, 'Não')]
            else:
                vertical_model = find_model(self.model, vertical_key)
                vertical_choices = [(o.pk, unicode(o)) for o in vertical_model.objects.filter(id__in=self.values_list(vertical_key, flat=True))]
            if horizontal_key:
                horizontal_field = get_field(self.model, horizontal_key)
                if horizontal_field.choices:
                    horizontal_choices = horizontal_field.choices
                elif horizontal_field.__class__.__name__ == 'BooleanField':
                    vertical_choices = [(True, 'Sim'), (False, 'Não')]
                else:
                    horizontal_model = find_model(self.model, horizontal_key)
                    horizontal_choices = [(o.pk, unicode(o)) for o in horizontal_model.objects.filter(id__in=self.values_list(horizontal_key, flat=True))]

                title = '{} por {} e {}'.format(verbose_name, vertical_field.verbose_name.lower(), horizontal_field.verbose_name)
                statistics = QueryStatistics([], [choice[1] for choice in vertical_choices], [choice[1] for choice in horizontal_choices], title=title)
                for vertical_choice in vertical_choices:
                    serie = []
                    avg = False
                    for horizontal_choice in horizontal_choices:
                        value = 0
                        lookup = {vertical_key: vertical_choice[0], horizontal_key: horizontal_choice[0]}
                        if aggregate:
                            mode, attr = aggregate
                            if mode == 'sum':
                                value = self.filter(**lookup).aggregate(Sum(attr)).get('{}__sum'.format(attr)) or 0
                            elif mode == 'avg':
                                avg = True
                                value = self.filter(**lookup).aggregate(Avg(attr)).get('{}__avg'.format(attr)) or 0
                            aggregation_field = get_field(self.model, attr)
                            if type(aggregation_field).__name__ in ('DecimalField',):
                                value = Decimal(value)
                        else:
                            value = self.filter(**lookup).values('id').count()
                        serie.append(value)
                    statistics.add(serie, avg)
                return statistics
            else:
                title = '{} por {}'.format(verbose_name, vertical_field.verbose_name)
                statistics = QueryStatistics([], [choice[1] for choice in vertical_choices], title=title)
                serie = []
                avg = False
                for vertical_choice in vertical_choices:
                    lookup = {vertical_key: vertical_choice[0]}
                    value = 0
                    if aggregate:
                        mode, attr = aggregate
                        if mode == 'sum':
                            value = self.filter(**lookup).aggregate(Sum(attr)).get('{}__sum'.format(attr)) or 0
                        elif mode == 'avg':
                            avg = True
                            value = self.filter(**lookup).aggregate(Avg(attr)).get('{}__avg'.format(attr)) or 0
                        aggregation_field = get_field(self.model, attr)
                        if type(aggregation_field).__name__ in ('DecimalField',):
                            value = Decimal(value)
                    else:
                        value = self.filter(**lookup).count()
                    serie.append(value)
                statistics.add(serie, avg)
                return statistics

    def count(self, vertical_key=None, horizontal_key=None):
        if vertical_key:
            return self._calculate(vertical_key, horizontal_key, aggregate=None)
        else:
            return super(QuerySet, self).count()

    def sum(self, attr, vertical_key=None, horizontal_key=None):
        return self._calculate(vertical_key, horizontal_key, aggregate=('sum', attr))

    def avg(self, attr, vertical_key=None, horizontal_key=None):
        return self._calculate(vertical_key, horizontal_key, aggregate=('avg', attr))
    
    @classmethod
    def as_manager(cls):
        return Manager(queryset_class=cls)


class Manager(models.Manager):

    def __init__(self, *args, **kwargs):
        self.queryset_class = kwargs.pop('queryset_class', QuerySet)
        self.request = None
        super(Manager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        return self.queryset_class(self.model, using=self._db)

    def all(self, user=None, obj=None):
        return self.get_queryset().all(user, obj=obj)

    def count(self, vertical_key=None, horizontal_key=None):
        return self.get_queryset().count(vertical_key, horizontal_key)

    def sum(self, attr, vertical_key=None, horizontal_key=None):
        return self.get_queryset().sum(attr, vertical_key, horizontal_key)


class ModelBase(base.ModelBase):
    def __new__(mcs, name, bases, attrs):
        meta_new = super(ModelBase, mcs).__new__
        module = __import__(attrs['__module__'], fromlist=list(map(str, attrs['__module__'].split('.'))))
        if hasattr(module, '{}Manager'.format(name)):
            queryset_class = getattr(module, '{}Manager'.format(name))
            if issubclass(queryset_class, QuerySet):
                attrs.update(objects=Manager(queryset_class=queryset_class))

        cls = meta_new(mcs, name, bases, attrs)
        for attr_name in attrs:
            if attr_name not in ('objects',):
                attr = getattr(cls, attr_name)
                if hasattr(attr, '_action'):
                    pass

        requires_tree_index = False
        declared_tree_index = False
        for field in cls._meta.fields:
            if field.__class__.__name__ == 'TreeIndexField':
                declared_tree_index = True
            if field.__class__.__name__ == 'ForeignKey' and field.tree:
                requires_tree_index = True

        if requires_tree_index:
            if not hasattr(cls._meta, 'select_template'):
                setattr(cls._meta, 'select_template', 'tree_node_option.html')
            if not declared_tree_index:
                from fields import TreeIndexField
                cls.add_to_class('tree_index', TreeIndexField())

        return cls

DefaultManager = QuerySet


class Model(six.with_metaclass(ModelBase, models.Model)):

    class Meta:
        abstract = True

    objects = DefaultManager.as_manager()

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        self.request = None
        self._user = None

    def __unicode__(self):
        for subclass in self.__class__.__subclasses__():
            if hasattr(self, subclass.__name__.lower()):
                subinstance = getattr(self, subclass.__name__.lower())
                if hasattr(subinstance, '__unicode__'):
                    return subinstance.__unicode__()
        return '{}{}'.format(get_metadata(self.__class__, 'verbose_name'), self.pk and ' #{}'.format(self.pk or ''))

    @classmethod
    def update_metadata(cls, **kwargs):
        for attr in kwargs:
            value = kwargs[attr]
            setattr(getattr(cls, '_meta'), attr, value)

    @classmethod
    def is_tree(cls):
        return cls.get_tree_index_field()

    @classmethod
    def get_tree_index_field(cls):
        for field in cls._meta.fields:
            if type(field).__name__ == 'TreeIndexField':
                return field
        return None

    @classmethod
    def get_parent_field(cls):
        for field in cls._meta.fields:
            if hasattr(field, 'rel') and field.rel and field.rel.to == cls:
                return field
        return None

    def get_depth(self):
        tree_index_field = self.get_tree_index_field()
        if tree_index_field:
            return len((getattr(self, tree_index_field.name) or '').split(tree_index_field.sep))-1
        return 0

    def get_children(self):
        tree_index = getattr(self, self.get_tree_index_field().name)
        return type(self).objects.filter(**{'{}__startswith'.format(tree_index):tree_index}).exclude(pk=self.pk)

    def save(self, *args, **kwargs):
        log_data = get_metadata(self.__class__, 'log', False)
        log_index = get_metadata(self.__class__, 'logging', (), iterable=True)

        # edited changes logging
        if (log_data or log_index) and self.pk and self._user:
            log_indexes = list(log_index)
            qs = self.__class__.objects.filter(pk=self.pk).select_related(*log_indexes)

            self._diff = False
            if qs.exists():
                from djangoplus.admin.models import Log
                old = qs[0]
                log = Log()
                log.operation = Log.EDIT
                log.user = self._user
                log.content_type = ContentType.objects.get_for_model(self.__class__)
                log.object_id = self.pk
                log.object_description = unicode(self)
                diff = []

                for field in get_metadata(self, 'fields'):
                    o1 = getattr(old, field.name)
                    o2 = getattr(self, field.name)
                    v1 = unicode(o1)
                    v2 = unicode(o2)
                    if not hasattr(o2, '__iter__') and v1 != v2:
                        self._diff = True
                        diff.append((field.verbose_name, v1, v2))

                log.content = json.dumps(diff)
                log.save()
                log.create_indexes(old)

        # tree model
        tree_index_field = self.get_tree_index_field()
        if tree_index_field:
            recursive = kwargs.pop('recursive', False)
            parent_field = self.get_parent_field()
            parent = getattr(self, parent_field.name)
            if tree_index_field.ref:
                tree_index_end = getattr(self, tree_index_field.ref)
                if not tree_index_end:
                    raise Exception('{} deve ser informado.'.format(tree_index_field.base))
            else:
                tree_index_end = self.pk and getattr(self, tree_index_field.name).split('.')[-1] or None
                if recursive or not self.pk or not type(self).objects.filter(
                        **{'id': self.pk, parent_field.name: parent}).exists():
                    tree_index_end = '1'
                    qs = type(self).objects.filter(**{parent_field.name: parent}).order_by(
                        '-{}'.format(tree_index_field.name)).values_list(tree_index_field.name, flat=True)
                    if qs.exists():
                        tree_index_end = int(qs[0].split('.')[-1]) + 1
            if parent:
                parent_index = getattr(parent, tree_index_field.name)
                tree_index = '{}{}{}'.format(parent_index, tree_index_field.sep, tree_index_end)
            else:
                tree_index = tree_index_end

            setattr(self, tree_index_field.name, tree_index)

        super(Model, self).save(*args, **kwargs)

        # make many-to-many and one-to-many relations available after save
        if hasattr(self, '_post_save_form'):
            post_save_form = getattr(self, '_post_save_form')
            getattr(post_save_form, 'save_121_and_12m')()
            getattr(post_save_form, '_save_m2m')()
            super(Model, self).save(*args, **kwargs)

        if tree_index_field:
            for obj in type(self).objects.filter(**{parent_field.name: self}):
                kwargs['recursive'] = True
                obj.save(*args, **kwargs)

        # registration logging
        if (log_data or log_index) and not hasattr(self, '_diff') and self._user:
            from djangoplus.admin.models import Log
            log = Log()
            log.operation = Log.ADD
            log.user = self._user
            log.content_type = ContentType.objects.get_for_model(self.__class__)
            log.object_id = self.pk
            log.object_description = unicode(self)
            log.content = '[]'
            log.save()
            log.create_indexes(self)

        self._check_role()

    def as_user(self):
        role_username = get_metadata(self.__class__, 'role_username')
        if role_username:
            return get_user_model().objects.get(username=getattr(self, role_username))
        return None

    def _check_role(self, saving=True):
        role_name = get_metadata(self.__class__, 'role_name')
        role_username = get_metadata(self.__class__, 'role_username')
        verbose_name = get_metadata(self.__class__, 'verbose_name')
        concrete_fields = get_metadata(self.__class__, 'concrete_fields')
        role_email = get_metadata(self.__class__, 'role_email', '')
        role_scope = get_metadata(self.__class__, 'role_scope')

        if role_username:

            from django.contrib.auth.models import Group
            from djangoplus.admin.models import Role, Organization, OrganizationRole, Unit, UnitRole

            group_name = verbose_name
            username = getattr2(self, role_username)
            name = role_name and getattr2(self, role_name) or None

            if username:
                unit = Unit.objects.get(pk=0)
                organization = organization = Organization.objects.get(pk=0)

                if issubclass(self.__class__, Organization):
                    organization = self
                    unit = None
                elif issubclass(self.__class__, Unit):
                    unit = self
                    organization = None
                elif role_scope:
                    scope = getattr2(self, role_scope)
                    if issubclass(scope.__class__, Organization):
                        organization = scope
                        unit = None
                    elif issubclass(scope.__class__, Unit):
                        unit = scope
                        organization = None
                else:
                    for field in concrete_fields:
                        if hasattr(field, 'rel') and hasattr(field.rel, 'to'):
                            if issubclass(field.rel.to, Organization):
                                organization = getattr(self, field.name)
                                unit = None
                                break
                            if issubclass(field.rel.to, Unit):
                                unit = getattr(self, field.name)
                                organization = None
                                break

                email = role_email and getattr2(self, role_email) or ''

                User = get_user_model()
                group = Group.objects.get_or_create(name=group_name)[0]

                if unit and not organization:
                    for field in get_metadata(unit.__class__, 'concrete_fields'):
                        if hasattr(field, 'rel') and hasattr(field.rel, 'to'):
                            if issubclass(field.rel.to, Organization):
                                organization = getattr(unit, field.name)

                if saving:
                    qs = User.objects.filter(username=username)
                    if qs.exists():
                        user = qs[0]
                        user.email = email
                        user.name = name or unicode(self)
                        user.save()
                    else:
                        user = User()
                        user.username = username
                        user.name = name or unicode(self)
                        user.email = email
                        user.save()
                        if user.email and not (settings.DEBUG or 'test' in sys.argv):
                            user.send_access_invitation()

                    user.groups.add(group)
                    if organization:
                        role = Role.objects.get(user=user, group=group)
                        if not OrganizationRole.objects.filter(role=role, organization=organization).exists():
                            organization_role = OrganizationRole()
                            organization_role.role = role
                            organization_role.organization = organization
                            organization_role.save()
                    if unit:
                        role = Role.objects.get(user=user, group=group)
                        if not UnitRole.objects.filter(role=role, unit=unit).exists():
                            unit_role = UnitRole()
                            unit_role.role = role
                            unit_role.unit = unit
                            unit_role.save()
                else:
                    user = User.objects.get(username=username)
                    if unit or organization:
                        keep_in_group = False
                        if organization:
                            OrganizationRole.objects.filter(role__user=user, role__group=group, organization=organization).delete()
                            if OrganizationRole.objects.filter(role__user=user, role__group=group).exists():
                                keep_in_group=True
                        if unit:
                            UnitRole.objects.filter(role__user=user, role__group=group, unit=unit).delete()
                            if UnitRole.objects.filter(role__user=user, role__group=group).exists():
                                keep_in_group = True
                        if not keep_in_group:
                            user.groups.remove(group)
                    else:
                        UnitRole.objects.filter(role__user=user, role__group=group).delete()
                        user.groups.remove(group)

    def delete(self, *args, **kwargs):
        log_data = get_metadata(self.__class__, 'log', False)
        log_index = get_metadata(self.__class__, 'logging', ())

        if (log_data or log_index) and self._user:
            from djangoplus.admin.models import Log

            collector = Collector(using='default')
            collector.collect([self], keep_parents=False)
            for cls, objs in collector.data.items():
                content_type = ContentType.objects.get_for_model(cls)
                for obj in objs:
                    log = Log()
                    log.operation = Log.DELETE
                    log.user = self._user
                    log.content_type = content_type
                    log.object_id = obj.pk
                    log.object_description = unicode(obj)
                    diff = []
                    for field in get_metadata(obj.__class__, 'fields'):
                        if not isinstance(field, models.FileField):
                            o1 = getattr(obj, field.name)
                            v1 = unicode(o1)
                            diff.append((field.verbose_name, v1))

                    log.content = json.dumps(diff)
                    log.save()
                    log.create_indexes(obj)

        super(Model, self).delete(*args, **kwargs)

        self._check_role(False)

    def get_logs(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        from djangoplus.admin.models import Log
        qs1 = Log.objects.filter(content_type=content_type, object_id=self.pk)
        qs2 = Log.objects.filter(logindex__content_type=content_type, logindex__object_id=self.pk)
        return (qs1 | qs2).order_by('-date')

    def can_edit(self):
        if self._user:
            if self._user.organization_id or self._user.unit_id or not self._user.is_superuser:
                model = type(self)
                app_label = get_metadata(model, 'app_label')
                perm_name = '{}.edit_{}'.format(app_label, model.__name__.lower())
                if self._user.has_perm(perm_name):
                    permission_mapping = self._user.get_permission_mapping(model)
                    if 'edit_lookups' in permission_mapping and permission_mapping['edit_lookups']:
                        for lookup, values in permission_mapping['edit_lookups']:
                            value = getattr2(self, lookup)
                            value = hasattr(value, 'pk') and value.pk or value
                            if value in values:
                                return True
                        return False
                else:
                    return False
        return True

    def can_delete(self):
        if self._user:
            if self._user.organization_id or self._user.unit_id or not self._user.is_superuser:
                model = type(self)
                app_label = get_metadata(model, 'app_label')
                perm_name = '{}.delete_{}'.format(app_label, model.__name__.lower())
                if self._user.has_perm(perm_name):
                    permission_mapping = self._user.get_permission_mapping(model)
                    if 'delete_lookups' in permission_mapping and permission_mapping['delete_lookups']:
                        for lookup, values in permission_mapping['delete_lookups']:
                            value = getattr2(self, lookup)
                            value = hasattr(value, 'pk') and value.pk or value
                            if value in values:
                                return True
                        return False
                else:
                    return False
        return True


class AsciiModel(Model):
    class Meta:
        abstract = True

    ascii = SearchField(blank=True, default='', editable=False, search=True, exclude=True)

