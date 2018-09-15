# -*- coding: utf-8 -*-


# list - Allows the user to access the Admin page to view all registered objects
# add - Allows the user to add objects from the Admin page and the Relation tables
# edit - Allows the user to edit objects from the Admin page and the Relation tables
# delete - Allows the user to delete objects from Admin page and Relation tables


def has_permission(request, model, perm):
    app_label = getattr(model, '_meta').app_label
    model_name = model.__name__.lower()
    return request.user.has_perm('{}.{}_{}'.format(app_label, perm, model_name))


def has_list_permission(request, model):
    return has_permission(request, model, 'list')


def has_view_permission(request, model):
    return has_permission(request, model, 'view')


def has_add_permission(request, model):
    return has_permission(request, model, 'add')


def has_relate_permission(request, model):
    return has_permission(request, model, 'relate')


def has_edit_permission(request, model):
    return has_permission(request, model, 'edit')


def has_delete_permission(request, model):
    return has_permission(request, model, 'delete')


def can(request, obj, action):
    if request.user.is_superuser:
        return True
    if has_permission(request, type(obj), action):
        func_name = 'can_{}'.format(action)
        if hasattr(obj, func_name):
            obj.request = request
            return getattr(obj, func_name)()
        else:
            return True
    else:
        return False


def can_add(request, obj):
    return can(request, obj, 'add')


def can_edit(request, obj):
    return can(request, obj, 'edit')


def can_delete(request, obj):
    return can(request, obj, 'delete')


def can_view(request, obj):
    return can(request, obj, 'view')


def can_edit_field(request, obj, related_field_name):
    field = getattr(type(obj), related_field_name).field
    return can_add(request, obj) or check_group_or_permission(request, field.can_add)


def check_group_or_permission(request, perm_or_group, ignore_superuser=False):
    if perm_or_group:
        satisfied = False
        for perm_or_group in (type(perm_or_group) not in (list, tuple) and (perm_or_group,) or perm_or_group):
            if perm_or_group:
                if request.user.is_superuser and not ignore_superuser:
                    satisfied = True
                elif '.' not in perm_or_group:
                    satisfied = request.user.groups.filter(name=perm_or_group).exists()
                else:
                    satisfied = request.user.has_perm(perm_or_group)
            else:
                satisfied = True
            if satisfied: break
        return satisfied
    return True
