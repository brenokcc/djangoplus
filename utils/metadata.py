# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# DJANGO FIELDS
import inspect
from django.utils.text import camel_case_to_spaces
from django.utils.safestring import mark_safe


def is_many_to_many(model, name):
    attr = hasattr(model, name) and getattr(model, name) or None
    return attr and hasattr(attr, 'field') and attr.field.__class__.__name__ == 'ManyToManyField' or False


def is_one_to_many(model, name):
    attr = hasattr(model, name) and getattr(model, name) or None
    return attr and hasattr(attr, 'field') and attr.field.__class__.__name__ == 'OneToManyField' or False


def is_one_to_one(model, name):
    attr = hasattr(model, name) and getattr(model, name) or None
    return attr and hasattr(attr, 'field') and attr.field.__class__.__name__ == 'OneToOneField' or False


def is_many_to_one(model, name):
    attr = hasattr(model, name) and getattr(model, name) or None
    return attr and attr.__class__.__name__ == 'ForwardManyToOneDescriptor' or False


def is_one_to_many_reverse(model, name):
    attr = hasattr(model, name) and getattr(model, name) or None
    return attr and attr.__class__.__name__ == 'ReverseManyToOneDescriptor' or False


def list_m2m_fields_with_model(cls):
    return [(f, f.model if f.model != cls else None) for f in cls._meta.get_fields() if f.many_to_many and not f.auto_created]


def list_related_objects(cls):
    return [f for f in cls._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created]


def find_field_by_name(model, field_name):
    return model._meta.get_field(field_name)


def list_field_names(model, include_m2m=False):
    l = [field.name for field in model._meta.local_fields]
    if include_m2m:
        for field in model._meta.local_many_to_many:
            l.append(field.name)
    return l


def get_field(model, lookup):
    tokens = lookup.split('__')
    tokens.reverse()
    field_name = tokens.pop()
    field = find_field_by_name(model, field_name)
    return get_field_recursively(field, tokens)


def get_field_recursively(field, tokens):
    if tokens:
        field_name = tokens.pop()
        if hasattr(field, 'rel'):
            field = find_field_by_name(field.rel.to, field_name)
        else:
            field = find_field_by_name(field.related_model, field_name)
        return get_field_recursively(field, tokens)
    else:
        return field


def get_fiendly_name(model_or_field, lookup, as_tuple=False):
    l = []
    tokens = lookup.split('__')
    tokens.reverse()
    pronoun = None
    to = None
    while (tokens):
        token = tokens.pop()

        if hasattr(model_or_field, token):
            field_or_function = getattr(model_or_field, token)
            if hasattr(field_or_function, 'field'):
                field_or_function = field_or_function.field
            elif hasattr(field_or_function, 'field_name'):
                field_or_function = model_or_field._meta.get_field(token)
        else:
            field_or_function = model_or_field._meta.get_field(token)

        if pronoun and l:
            l.append(pronoun)

        if hasattr(field_or_function, 'rel') and field_or_function.rel:

            pronoun = get_metadata(field_or_function.rel.to, 'verbose_female') and 'da' or 'do'

            if tokens:
                model_or_field = field_or_function.rel.to
                name = field_or_function.verbose_name
            else:
                model_or_field = field_or_function
                name = model_or_field.verbose_name
            sortable = True
            to = field_or_function.rel.to

        elif hasattr(field_or_function, 'verbose_name'):
            model_or_field = field_or_function
            name = model_or_field.verbose_name
            sortable = True

        elif hasattr(field_or_function, '_metadata'):
            model_or_field = field_or_function
            name = field_or_function._metadata['{}:verbose_name'.format(token)]
            sortable = False
        else:
            model_or_field = field_or_function
            name = token
            sortable = False
        l.append(unicode(name))
    l.reverse()
    verbose_name = ' '.join(l)
    verbose_name = l[0]
    return as_tuple and (verbose_name, lookup, sortable, to) or verbose_name

# META DATA


def set_metadata(cls, attr, value):
    if not hasattr(cls, '_metadata'):
        cls._metadata = dict()
    cls._metadata['{}:{}'.format(cls.__name__, attr)] = value


def get_metadata(model, attr, default=None, iterable=False):
    _metadata = None

    if not hasattr(model._meta, attr):
        field_attr = None

        if attr == 'search_fields':
            field_attr = 'search'
        elif attr == 'exclude_fields':
            field_attr = 'exclude'
        elif attr == 'list_filter':
            field_attr = 'filter'

        if field_attr:
            _metadata = []
            fields = []
            for field in model._meta.fields:
                fields.append(field)
            for m2m in list_m2m_fields_with_model(model):
                fields.append(m2m[0])
            for field in fields:
                if hasattr(field, field_attr):
                    value = getattr(field, field_attr)
                    if value:
                        if type(value) == bool and value:
                            _metadata.append(field.name)
                        elif type(value) in (list, tuple) and value:
                            for lookup in value:
                                if lookup in ('pk', 'id'):
                                    _metadata.append(field.name)
                                else:
                                    _metadata.append('{}__{}'.format(field.name, lookup))
            setattr(model._meta, field_attr, _metadata)
    else:
        _metadata = getattr(model._meta, attr)
        if callable(_metadata):
            _metadata = _metadata()

    if _metadata is None:
        if attr == 'list_display':
            _metadata = []
            fields = []
            for field in model._meta.fields:
                fields.append(field)
            for field in model._meta.local_many_to_many:
                fields.append(field)
            for field in fields[1:6]:
                if not field.name.endswith('_ptr') and not field.name == 'ascii' and not field.name == 'tree_index':
                    _metadata.append(field.name)
        else:
            _metadata = default

    if attr == 'fieldsets' and hasattr(model, 'fieldsets'):
        _metadata = model.fieldsets or default
    elif attr == 'view_fieldsets':
        if hasattr(model, 'view_fieldsets'):
            _metadata = model.view_fieldsets
        else:
            _metadata = hasattr(model, 'fieldsets') and model.fieldsets or default

    check_recursively = not _metadata
    if attr in ('verbose_name', 'verbose_name_plural'):
        if unicode(_metadata) in (camel_case_to_spaces(model.__name__), '{}s'.format(camel_case_to_spaces(model.__name__))):
            check_recursively = True
    if attr in ('list_menu', 'verbose_female'):
        check_recursively = False

    if check_recursively:
        if hasattr(model, '__bases__') and model.__bases__ and hasattr(model.__bases__[0], '_meta'):
            _metadata = get_metadata(model.__bases__[0], attr)

    if iterable:
        if _metadata:
            if not hasattr(_metadata, '__iter__'):
                _metadata = _metadata,
        else:
            _metadata = ()

    return _metadata

# REFLECTION


def iterable(string_or_iterable):
    if string_or_iterable and not type(string_or_iterable) in (list, tuple):
        return string_or_iterable,
    return string_or_iterable


def getattr2(obj, args):
    if args == '__unicode__':
        splitargs = [args]
    else:
        splitargs = args.split('__')
    return getattr_rec(obj, splitargs)


def getattr_rec(obj, args):
    if not obj:
        return None
    if callable(obj):
        obj = obj()
    if len(args) > 1:
        attr = args.pop(0)
        return getattr_rec(getattr2(obj, attr), args)
    else:
        from django.core.exceptions import ObjectDoesNotExist
        from djangoplus.cache import loader

        try:
            model = type(obj)
            attr_name = args[0]
            attr = getattr(model, attr_name)
            value = getattr(obj, attr_name)
            field = None
            if hasattr(attr, 'field_name'):
                field = getattr(model, '_meta').get_field(attr.field_name)
            elif hasattr(attr, 'field'):
                field = attr.field

            if field:
                if hasattr(field, 'formatter') and field.formatter:
                    func = loader.formatters[field.formatter]
                    if len(func.func_code.co_varnames) == 1:
                        value = func(value)
                    else:
                        value = func(value, request=obj.request, verbose_name=field.verbose_name, instance=obj)
                    return mark_safe(unicode(value))
                elif hasattr(field, 'display') and field.display not in (True, False, None):
                    if hasattr(obj, field.display):
                        args[0] = field.display
                        return getattr_rec(obj, args)
                elif hasattr(field, 'suffix') and field.suffix:
                    suffix = field.suffix
                    if hasattr(obj, field.suffix):
                        suffix = getattr(obj, field.suffix)
                        if callable(suffix):
                            suffix = suffix()
                    return value, suffix
                elif hasattr(obj, 'get_{}_display'.format(args[0])):
                    return getattr(obj, 'get_{}_display'.format(args[0]))()
            else:
                # it is a method decorated with @attr
                _metadata = hasattr(value, '_metadata') and getattr(value, '_metadata') or None
                if _metadata:
                    verbose_name = _metadata.get('{}:verbose_name'.format(args[0]))
                    if verbose_name:
                        value = value()
                        formatter = _metadata.get('{}:formatter'.format(args[0]))
                        if formatter:
                            func = loader.formatters[formatter]
                            if len(func.func_code.co_varnames) == 1:
                                value = func(value)
                            else:
                                value = func(value, request=obj.request, verbose_name=verbose_name, instance=obj)
                            return mark_safe(unicode(value))

            if callable(value):
                if type(value).__name__ in ('ManyRelatedManager' or 'RelatedManager'):
                    value = value.all()
                else:
                    value = value()
            return value

        except ObjectDoesNotExist:
            return None


def get_scope(model, organization_model, unit_model):
    scope = 'systemic'
    role_scope = get_metadata(model, 'role_scope')
    if role_scope:
        field = get_field(model, role_scope)
        if field.rel.to == unit_model:
            scope = 'unit'
        elif field.rel.to == organization_model:
            scope = 'organization'
    else:
        for field in get_metadata(model, 'concrete_fields'):
            if hasattr(field, 'rel') and hasattr(field.rel, 'to'):
                if field.rel.to == unit_model:
                    scope = 'unit'
                elif field.rel.to == organization_model:
                    scope = 'organization'
    return scope


def should_filter_or_display(request, model, to):
    if get_metadata(to, 'role_username'):
        can_view = list(
            get_metadata(model, 'can_admin', (), iterable=True) +
            get_metadata(model, 'can_admin_by_organization', (), iterable=True) +
            get_metadata(model,'can_admin_by_unit',(), iterable=True) +
            get_metadata(model, 'can_view', (), iterable=True) +
            get_metadata(model, 'can_view_by_organization', (), iterable=True) +
            get_metadata(model, 'can_view_by_unit', (), iterable=True))
        if not request.user.is_superuser and can_view and not request.user.in_group(*can_view):
            return False
    return True


def find_action(model, action_name):
    from djangoplus.cache import loader
    for actions in (loader.actions, loader.class_actions):
        for action_group in actions[model]:
            for func_name, action in actions[model][action_group].items():
                if action['title'] == action_name:
                    return action
    return None


def find_model_by_verbose_name(verbose_name):
    from django.apps import apps
    for model in apps.get_models():
        app_label = get_metadata(model, 'app_label')
        if not app_label.startswith('admin'):
            if get_metadata(model, 'verbose_name') == verbose_name:
                return model
    return None


def find_model_by_verbose_name_plural(verbose_name_plural):
    from django.apps import apps
    for model in apps.get_models():
        app_label = get_metadata(model, 'app_label')
        if not app_label.startswith('admin'):
            if get_metadata(model, 'verbose_name_plural') == verbose_name_plural:
                return model
    return None


def find_subset_by_title(title, model):
    from djangoplus.cache import loader
    for subset in loader.subsets[model]:
        if subset['title'] == title:
            return subset
    return None


def find_model_by_add_label(add_label):
    from django.apps import apps
    for model in apps.get_models():
        if get_metadata(model, 'add_label') == add_label:
            return model
    return None


def find_model(model, key):
    tokens = key.split('__')
    tokens.reverse()
    return find_model_recursively(model, tokens)


def find_model_recursively(cls, tokens):
    if tokens:
        token = tokens.pop()
        attr = getattr(cls, token)
        if not hasattr(attr, 'field'):
            return cls
        return find_model_recursively(attr.field.rel.to, tokens)
    else:
        return cls


def check_condition(condition, obj):
    satisfied = True
    if obj.pk and condition:
        attr_name = condition.replace('not ', '')
        attr = getattr(obj, attr_name)
        if callable(attr):
            satisfied = attr()
        else:
            satisfied = bool(attr)
        if 'not ' in condition:
            satisfied = not satisfied
    return satisfied



