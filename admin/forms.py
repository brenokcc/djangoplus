# -*- coding: utf-8 -*-

import sys
import datetime
from django.core import signing
from django.contrib import auth
from django.conf import settings
from djangoplus.cache import CACHE
from djangoplus.ui.components import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.hashers import make_password
from djangoplus.ui.components.navigation.breadcrumbs import httprr
from djangoplus.admin.models import Group, User, Unit, Settings, Organization


class LoginForm(forms.Form):
    
    ORGANIZATION = 'organization'
    UNIT = 'unit'
    
    username = forms.CharField(label=_('User'))
    password = forms.PasswordField(label=_('Password'))

    def __init__(self, request, scope=None, organization=None, unit=None, *args, **kwargs):
        super(LoginForm, self).__init__(request, *args, **kwargs)
        self.scope = None
        self.fields['username'].widget.attrs['class'] = 'input-sm bounceIn animation-delay2'
        if scope:
            if scope == LoginForm.ORGANIZATION or scope == (
                    CACHE['ORGANIZATION_MODEL'] and CACHE['ORGANIZATION_MODEL'].__name__.lower()):
                if organization:
                    self.scope_display = organization
                else:
                    organizations = Organization.objects.all()
                    self.fields['login_scope'] = forms.ModelChoiceField(organizations)
                self.scope = LoginForm.ORGANIZATION
            elif scope == LoginForm.UNIT or scope == (CACHE['UNIT_MODEL'] and CACHE['UNIT_MODEL'].__name__.lower()):
                if unit:
                    self.scope_display = unit
                else:
                    if organization:
                        self.scope_display = organization
                        units = organization.get_units()
                    else:
                        units = Unit.objects.all()
                    self.fields['login_scope'] = forms.ModelChoiceField(units)
                self.scope = LoginForm.UNIT
        self.organization = organization
        self.unit = unit

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        if not User.objects.filter(username=username).exists():
            raise forms.ValidationError(_('User not registered.'))
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            if user.active:
                user.permission_mapping = ''
                user.organization = None
                user.unit = None
                if self.scope == LoginForm.ORGANIZATION:
                    user.organization = cleaned_data.get('login_scope', self.organization)
                    is_organization_user = user.role_set.filter(scope__in=(user.organization, 0)).exists()
                    if not is_organization_user:
                        raise forms.ValidationError('{} {} {}'.format(username, _('is not user of'), user.organization))
                elif self.scope == LoginForm.UNIT:
                    user.unit = cleaned_data.get('login_scope', self.unit)
                    is_unit_user = user.role_set.filter(units__in=(user.unit, 0)).exists()
                    is_organization_user = CACHE['ORGANIZATION_MODEL'] and user.role_set.filter(
                        scope__in=(user.unit.get_organization(), 0)).exists()
                    if not is_unit_user and not is_organization_user:
                        raise forms.ValidationError('{} {} {}'.format(username, _('is not user of'), user.unit))
                else:
                    roles = user.role_set.all()
                    if roles.count() == 1:
                        role = roles.first()
                        if role.scope:
                            user.scope = role.scope
                user.save()
                auth.login(self.request, user)
                return cleaned_data
            else:
                raise forms.ValidationError(_('User is inactive.'))
        else:
            raise forms.ValidationError(_('Password is incorrect.'))

    def submit(self):
        url = self.request.GET.get('next', '/admin/')
        return httprr(self.request, url, _('You have successfully logged in.'))


class GroupForm(forms.ModelForm):
    name = forms.CharField(label='Name')

    class Meta:
        title = '{} {}'.format(_('Register'), _('Group'))
        submit_label = _('Save')
        icon = 'fa-users'
        model = Group
        fields = ('name',)


class UserForm(forms.ModelForm):
    is_superuser = forms.BooleanField(label=_('Superuser'), required=False)
    new_password = forms.PasswordField(label=_('Password'), required=False)

    class Meta:
        model = User
        fields = ('username', 'name', 'active', 'email', 'is_superuser', 'photo')
        title = '{} {}'.format(_('Register'), _('User'))
        submit_label = _('Save')
        icon = 'fa-user'

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        if not args[0].user.is_superuser:
            del (self.fields['is_superuser'])
            self.fieldsets = (
                (_('Identification'), {'fields': (('name', 'email',), 'photo')}),
                (_('Access'), {'fields': (('username', 'new_password'), ('active',))}),
            )
        else:
            self.fieldsets = (
                (_('Identification'), {'fields': (('name', 'email',), 'photo')}),
                (_('Access'), {'fields': (('username', 'new_password'), ('active', 'is_superuser'))}),
            )

    def save(self, *args, **kwargs):
        user = super(UserForm, self).save(commit=False)
        if 'new_password' in self.cleaned_data and self.cleaned_data['new_password']:
            user.set_password(self.cleaned_data['new_password'])
        user.save()


class RegisterForm(forms.Form):
    name = forms.CharField(label=_('Name'), required=True)
    email = forms.EmailField(label=_('E-mail'), required=True)
    new_password = forms.PasswordField(label=_('Password'), required=True)
    confirm_password = forms.PasswordField(label=_('Password'), required=True, help_text=_('Repeat Password'))

    class Meta:
        title = 'Novo Usuário'
        icon = 'fa-user'
        submit_label = 'Cadastrar'
        captcha = True

    fieldsets = (
        (_('User Data'), {'fields': ('name', 'email')}),
        (_('Access Password'), {'fields': (('new_password', 'confirm_password'),)}),
    )

    def clean(self):
        if not self.data['new_password'] == self.data['confirm_password']:
            raise forms.ValidationError(_('The passwords must be the same.'))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        create = True
        user = User()
        password = self.cleaned_data['new_password']
        user.name = self.cleaned_data['name']
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        user.active = True
        user.is_superuser = False
        user.last_login = None
        user.date_joined = datetime.datetime.now()
        user.username = user.email
        user.set_password(password)
        if create:
            user.save()
            return user
        else:
            token = signing.dumps('{};{};{}'.format(user.name, user.email, password))
            url = '{}/admin/create_user/{}/'.format(settings.SERVER_ADDRESS, token)
            msg = '{}: {}'.format(_('Click on the link to activate your account'), url), settings.SYSTEM_EMAIL_ADDRESS
            user.email_user(_('Account Activation'), msg)
            return None


class ChangePasswordForm(forms.ModelForm):
    new_password = forms.PasswordField(label=_('Password'), required=True)
    confirm_password = forms.PasswordField(label=_('Confirm Password'), required=True, help_text=_('Repeat the password'))

    fieldsets = ((_('Password'), {'fields': ('new_password', 'confirm_password',)}),)

    class Meta:
        model = User
        fields = ('id',)
        title = _('Change Password')
        submit_label = _('Save')
        icon = 'fa-key'

    def clean(self):
        if not self.data.get('new_password') == self.data.get('confirm_password'):
            raise forms.ValidationError(_('The passwords must be the same.'))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        super(ChangePasswordForm, self).save(*args, **kwargs)
        User.objects.filter(pk=self.instance.pk).update(password=make_password(self.cleaned_data['new_password']))
        user = auth.authenticate(username=self.instance.username, password=self.cleaned_data['new_password'])
        auth.login(self.request, user)


class RecoverPassowordForm(forms.Form):
    email = forms.EmailField(label='E-mail')

    class Meta:
        captcha = 'test' not in sys.argv

    def clean(self):
        cleaned_data = super(RecoverPassowordForm, self).clean()
        qs = User.objects.filter(
            email=cleaned_data['email']
        )
        if qs.exists():
            qs.first().send_reset_password_notification()
            return cleaned_data
        else:
            raise forms.ValidationError(_('User not found.'))


class ProfileForm(forms.ModelForm):
    new_password = forms.PasswordField(label=_('Password'), required=False)
    confirm_password = forms.PasswordField(label=_('Confirm Password'), required=False, help_text=_('Repeat the password'))

    class Meta:
        model = User
        fields = ('name', 'photo', 'username', 'email')
        title = _('Edit Profile')
        submit_label = _('Save')
        icon = 'fa-user'

    fieldsets = (
        (_('User Data'), {'fields': (('name', 'username'), 'email', 'photo')}),
        (_('Access Password'), {'fields': (('new_password', 'confirm_password'),)}),
    )

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.username = self.instance.username
        if not settings.USERNAME_CHANGE:
            self.fields['username'].widget.attrs.update(readonly='readonly')

    def clean_confirm_password(self):
        if not self.data.get('new_password') == self.data.get('confirm_password'):
            raise forms.ValidationError(_('The passwords must be the same.'))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        super(ProfileForm, self).save(*args, **kwargs)
        password = self.cleaned_data['new_password']

        if password:
            self.instance.set_password(password)
            self.instance.save()
            user = auth.authenticate(username=self.cleaned_data.get('username'), password=password)
        else:
            user = self.instance
        user.backend = self.request.session[auth.BACKEND_SESSION_KEY]
        auth.login(self.request, user)

        if self.username != user.username:
            for model in CACHE['ROLE_MODELS']:
                attr = CACHE['ROLE_MODELS'][model]['username_field']
                model.objects.filter(**{attr: self.username}).update(**{attr: self.request.user.username})


class SettingsForm(forms.ModelForm):
    class Meta:
        title = _('Settings')
        model = Settings
        exclude = ()

    def __init__(self, *args, **kwargs):
        kwargs['instance'] = Settings.default()
        super(SettingsForm, self).__init__(*args, **kwargs)
