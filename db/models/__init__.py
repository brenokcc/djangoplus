# -*- coding: utf-8 -*-

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
from djangoplus.utils.metadata import get_metadata, getattr2, find_model, get_field, check_role
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from functools import reduce

setattr(options, 'DEFAULT_NAMES', options.DEFAULT_NAMES + (
    'icon', 'verbose_female', 'order_by', 'pdf', 'menu',
    'list_display', 'list_per_page', 'list_template', 'list_total', 'list_shortcut', 'list_csv', 'list_xls', 'list_menu', 'list_lookups', 'list_pdf',
    'add_label', 'add_form', 'add_inline', 'add_message', 'add_shortcut', 'select_template', 'select_display', 'select_related',
    'log', 'logging',
    'can_add', 'can_edit', 'can_delete', 'can_list', 'can_view', 'can_admin',
    'can_list_by_role', 'can_view_by_role', 'can_add_by_role', 'can_edit_by_role', 'can_admin_by_role',
    'can_list_by_unit', 'can_view_by_unit', 'can_add_by_unit', 'can_edit_by_unit', 'can_admin_by_unit',
    'can_list_by_organization', 'can_view_by_organization', 'can_add_by_organization', 'can_edit_by_organization', 'can_admin_by_organization',
    'usecase', 'class_diagram', 'dashboard'
))


class QueryStatistics(object):
    def __init__(self, title, symbol=None):
        self.title = title
        self.symbol = symbol
        self.labels = []
        self.groups = []
        self.series = []
        self.querysets = []
        self.xtotal = []
        self.ytotal = []
        self.avg = False

    def add(self, label, qs, value=None, group=None, avg=False):

        if label not in self.labels:
            self.labels.append(label)

        # if the group changed or there is no series and querysets, the lists must be initilized
        if group and group not in self.groups or not self.series:
            self.series.append([])
            self.querysets.append([])

        # when the group changes, it must be inserted in the group list
        if group and group not in self.groups:
            self.groups.append(group)

        # add queryset and value to the end of the respective lists
        if value is None:
            value = qs.count()
        self.series[-1].append(value)
        self.querysets[-1].append(qs)

        # indicate if the value is an avarage value
        self.avg = avg

    def _totalize(self, avg=False):
        for serie in self.series:
            if avg:
                self.xtotal.append(sum(serie) / len(serie))
            else:
                self.xtotal.append(sum(serie))
            if not self.ytotal:
                for value in serie:
                    self.ytotal.append(value)
            else:
                for i, value in enumerate(serie):
                    self.ytotal[i] += value

    def as_table(self, request=None):
        from djangoplus.ui.components.utils import QueryStatisticsTable
        self._totalize()
        return QueryStatisticsTable(request, self)

    def as_chart(self, request=None):
        from djangoplus.ui.components.utils import QueryStatisticsChart
        if not self.groups:
            chart = QueryStatisticsChart(request, self)
            return chart.donut()
        else:
            chart = QueryStatisticsChart(request, self)
            if self.labels and self.labels[0] == 'Jan':
                return chart.line()
            else:
                return chart.bar()

    def total(self):
        return sum(self.xtotal)

    def __str__(self):
        return '{}\n{}\n{}'.format(self.labels, self.series, self.groups)


class ModelGeneratorWrapper:
    def __init__(self, generator, user):
        self.generator = generator
        self._user = user

    def __iter__(self):
        return self

    def __next__(self):
        obj = next(self.generator)
        obj._user = self._user
        return obj


class ModelIterable(query.ModelIterable):

    def __iter__(self):
        generator = super(ModelIterable, self).__iter__()
        return ModelGeneratorWrapper(generator, self.queryset._user)


class QuerySet(query.QuerySet):

    def __init__(self, *args, **kwargs):
        self._user = None
        super(QuerySet, self).__init__(*args, **kwargs)
        self._iterable_class = ModelIterable

    def _clone(self):
        clone = super(QuerySet, self)._clone()
        clone._user = self._user
        return clone

    def __add__(self, other):
        return self | other

    def __sub__(self, other):
        return self.difference(other)

    def all(self, user=None, obj=None):
        app_label = get_metadata(self.model, 'app_label')
        if user:
            role_username = get_metadata(user, 'role_username')
            if role_username:
                user = get_user_model().objects.get(username=getattr(user, role_username))
        queryset = self._clone()
        queryset._user = user
        if user:
            self_permission = '{}.view_{}'.format(app_label, self.model.__name__.lower())
            obj_permission = obj and '{}.view_{}'.format(get_metadata(type(obj), 'app_label'), type(obj).__name__.lower())
            has_perm = obj_permission and user.has_perm(obj_permission) or user.has_perm(self_permission)
        else:
            has_perm = True
        if has_perm:
            if user and not user.is_superuser:
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
                iterator_model = get_field(self.model, horizontal_key).remote_field.model
                iterators = iterator_model.objects.filter(pk__in=self.values_list(horizontal_key, flat=True).order_by(horizontal_key).distinct())
                horizontal_field = get_field(self.model, horizontal_key)
                title = '{} anual por {}'.format(verbose_name, horizontal_field.verbose_name)
                statistics = QueryStatistics(title)
                for iterator in iterators:
                    group = str(iterator)
                    for i, month in enumerate(months):
                        label = month
                        qs = self.filter(**{'{}__month'.format(vertical_key): i+1, horizontal_key: iterator.pk})
                        statistics.add(label, qs, qs.count(), group)
                return statistics
            else:
                title = '{} Anual'.format(verbose_name)
                statistics = QueryStatistics(title)
                for i, month in enumerate(months):
                    label = month
                    avg = False
                    if aggregate:
                        total = 0
                        mode, attr = aggregate
                        if mode == 'sum':
                            qs = self.filter(**{'{}__month'.format(vertical_key): i+1})
                            total = qs.aggregate(Sum(attr)).get('{}__sum'.format(attr)) or 0
                        elif mode == 'avg':
                            avg = True
                            qs = self.filter(**{'{}__month'.format(vertical_key): i+1})
                            total = qs.aggregate(Avg(attr)).get('{}__avg'.format(attr)) or 0
                        aggregation_field = get_field(self.model, attr)
                        if type(aggregation_field).__name__ in ('DecimalField',):
                            total = Decimal(total)
                    else:
                        qs = self.filter(**{'{}__month'.format(vertical_key): i+1})
                        total = qs.count()
                    statistics.add(label, qs, total, avg=avg)
                return statistics
        else:
            if vertical_field.choices:
                used_choices = self.values_list(vertical_key, flat=True).order_by(vertical_key).distinct()
                vertical_choices = []
                for choice in vertical_field.choices:
                    if choice[0] in used_choices:
                        vertical_choices.append(choice)
            elif vertical_field.__class__.__name__ == 'BooleanField':
                vertical_choices = [(True, 'Sim'), (False, 'Não')]
            else:
                vertical_model = find_model(self.model, vertical_key)
                vertical_choices = [(o.pk, str(o)) for o in vertical_model.objects.filter(id__in=self.values_list(vertical_key, flat=True))]
            if horizontal_key:
                horizontal_field = get_field(self.model, horizontal_key)
                if horizontal_field.choices:
                    used_choices = self.values_list(horizontal_key, flat=True).order_by(horizontal_key).distinct()
                    horizontal_choices = []
                    for choice in horizontal_field.choices:
                        if choice[0] in used_choices:
                            horizontal_choices.append(choice)
                elif horizontal_field.__class__.__name__ == 'BooleanField':
                    vertical_choices = [(True, 'Sim'), (False, 'Não')]
                else:
                    horizontal_model = find_model(self.model, horizontal_key)
                    horizontal_choices = [(o.pk, str(o)) for o in horizontal_model.objects.filter(id__in=self.values_list(horizontal_key, flat=True))]

                title = '{} por {} e {}'.format(verbose_name, vertical_field.verbose_name.lower(), horizontal_field.verbose_name)
                statistics = QueryStatistics(title)
                for vertical_choice in vertical_choices:
                    group = vertical_choice[1]
                    avg = False
                    for horizontal_choice in horizontal_choices:
                        label = horizontal_choice[1]
                        value = 0
                        lookup = {vertical_key: vertical_choice[0] or None, horizontal_key: horizontal_choice[0] or None}
                        qs = self.filter(**lookup).distinct()
                        if aggregate:
                            mode, attr = aggregate
                            if mode == 'sum':
                                value = qs.aggregate(Sum(attr)).get('{}__sum'.format(attr)) or 0
                            elif mode == 'avg':
                                avg = True
                                value = qs.aggregate(Avg(attr)).get('{}__avg'.format(attr)) or 0
                            aggregation_field = get_field(self.model, attr)
                            if type(aggregation_field).__name__ in ('DecimalField',):
                                value = Decimal(value)
                        else:
                            value = qs.values('id').count()
                        statistics.add(label, qs, value, group, avg=avg)
                return statistics
            else:
                title = '{} por {}'.format(verbose_name, vertical_field.verbose_name)
                statistics = QueryStatistics(title)
                avg = False
                for vertical_choice in vertical_choices:
                    label = vertical_choice[1]
                    lookup = {vertical_key: vertical_choice[0] or None}
                    value = 0
                    qs = self.filter(**lookup).distinct()
                    if aggregate:
                        mode, attr = aggregate
                        if mode == 'sum':
                            value = qs.aggregate(Sum(attr)).get('{}__sum'.format(attr)) or 0
                        elif mode == 'avg':
                            avg = True
                            value = qs.aggregate(Avg(attr)).get('{}__avg'.format(attr)) or 0
                        aggregation_field = get_field(self.model, attr)
                        if type(aggregation_field).__name__ in ('DecimalField',):
                            value = Decimal(value)
                    else:
                        value = qs.count()
                    statistics.add(label, qs, value, avg=avg)
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
        if self.queryset_class != self.model.objects.queryset_class:
            return self.model.objects.filter(pk=0).union(self.get_queryset().all(user, obj=obj))
        return self.get_queryset().all(user, obj=obj)

    def count(self, vertical_key=None, horizontal_key=None):
        return self.get_queryset().count(vertical_key, horizontal_key)

    def sum(self, attr, vertical_key=None, horizontal_key=None):
        return self.get_queryset().sum(attr, vertical_key, horizontal_key)

    def authenticated(self, obj):
        lookup = get_metadata(self.model, 'role_username')
        qs = self.model.objects.filter(**{lookup: obj._user.username})
        if qs.count():
            if qs.count() == 1:
                return qs[0]
            else:
                return qs
        else:
            return None


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
                from .fields import TreeIndexField
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

    def __str__(self):
        for subclass in self.__class__.__subclasses__():
            if hasattr(self, subclass.__name__.lower()):
                subinstance = getattr(self, subclass.__name__.lower())
                if hasattr(subinstance, '__str__'):
                    return subinstance.__str__()
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
            if field.remote_field and field.remote_field.model == cls:
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
                log.object_description = str(self)
                diff = []

                for field in get_metadata(self, 'fields'):
                    o1 = getattr(old, field.name)
                    o2 = getattr(self, field.name)
                    v1 = str(o1)
                    v2 = str(o2)
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
            log.object_description = str(self)
            log.content = '[]'
            log.save()
            log.create_indexes(self)

        check_role(self)

    def as_user(self):
        role_username = get_metadata(self.__class__, 'role_username')
        if role_username:
            return get_user_model().objects.get(username=getattr(self, role_username))
        return None

    def delete(self, *args, **kwargs):
        log_data = get_metadata(self.__class__, 'log', False)
        log_index = get_metadata(self.__class__, 'logging', ())

        if (log_data or log_index) and self._user:
            from djangoplus.admin.models import Log

            collector = Collector(using='default')
            collector.collect([self], keep_parents=False)
            for cls, objs in list(collector.data.items()):
                content_type = ContentType.objects.get_for_model(cls)
                for obj in objs:
                    log = Log()
                    log.operation = Log.DELETE
                    log.user = self._user
                    log.content_type = content_type
                    log.object_id = obj.pk
                    log.object_description = str(obj)
                    diff = []
                    for field in get_metadata(obj.__class__, 'fields'):
                        if not isinstance(field, models.FileField):
                            o1 = getattr(obj, field.name)
                            v1 = str(o1)
                            diff.append((field.verbose_name, v1))

                    log.content = json.dumps(diff)
                    log.save()
                    log.create_indexes(obj)

        super(Model, self).delete(*args, **kwargs)

        check_role(self, False)

    def get_logs(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        from djangoplus.admin.models import Log
        qs1 = Log.objects.filter(content_type=content_type, object_id=self.pk)
        qs2 = Log.objects.filter(logindex__content_type=content_type, logindex__object_id=self.pk)
        return (qs1 | qs2).order_by('-date')

    def can_edit(self):
        if self._user:
            if not self._user.is_superuser:
                model = type(self)
                app_label = get_metadata(model, 'app_label')
                perm_name = '{}.edit_{}'.format(app_label, model.__name__.lower())
                if self._user.has_perm(perm_name):
                    permission_mapping = self._user.get_permission_mapping(model)
                    if 'edit_lookups' in permission_mapping and permission_mapping['edit_lookups']:
                        for lookup, values in permission_mapping['edit_lookups']:
                            for value in model.objects.filter(pk=self.pk).values_list(lookup, flat=True).distinct():
                                if value in values:
                                    return True
                        return False
                else:
                    return False
        return True

    def can_delete(self):
        if self._user:
            if not self._user.is_superuser:
                model = type(self)
                app_label = get_metadata(model, 'app_label')
                perm_name = '{}.delete_{}'.format(app_label, model.__name__.lower())
                if self._user.has_perm(perm_name):
                    permission_mapping = self._user.get_permission_mapping(model)
                    if 'delete_lookups' in permission_mapping and permission_mapping['delete_lookups']:
                        for lookup, values in permission_mapping['delete_lookups']:
                            for value in model.objects.filter(pk=self.pk).values_list(lookup, flat=True).distinct():
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

