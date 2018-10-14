# -*- coding: utf-8 -*-

import datetime
from djangoplus.ui.components import forms
from django.contrib import auth
from django.conf import settings
from djangoplus.cache import loader
from djangoplus.ui.components.navigation.breadcrumbs import httprr
from djangoplus.utils.aescipher import encrypt
from djangoplus.admin.models import Group, User, Unit, Settings, Organization
from django.contrib.auth.hashers import make_password


class LoginForm(forms.Form):
    
    ORGANIZATION = 'organization'
    UNIT = 'unit'
    
    username = forms.CharField(label='Usuário')
    password = forms.PasswordField(label='Senha',
                                   help_text='Caso tenha esquecido sua senha, clique aqui para '
                                   '<a class="popup" href="/admin/reset_password/">alterá-la</a>.')

    def __init__(self, request, scope=None, organization=None, unit=None, *args, **kwargs):
        super(LoginForm, self).__init__(request, *args, **kwargs)
        self.scope = None
        self.fields['username'].widget.attrs['class'] = 'input-sm bounceIn animation-delay2'
        if scope:
            if scope == LoginForm.ORGANIZATION or scope == (loader.organization_model and loader.organization_model.__name__.lower()):
                if organization:
                    self.scope_display = organization
                else:
                    organizations = Organization.objects.all()
                    self.fields['login_scope'] = forms.ModelChoiceField(organizations)
                self.scope = LoginForm.ORGANIZATION
            elif scope == LoginForm.UNIT or scope == (loader.unit_model and loader.unit_model.__name__.lower()):
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
            raise forms.ValidationError('Usuário não cadastrado.')
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            if user.active:
                user.permission_mapping = ''
                user.organization = None
                user.unit = None
                if self.scope == LoginForm.ORGANIZATION:
                    user.organization = cleaned_data.get('login_scope', self.organization)
                    is_organization_user = user.role_set.filter(organizations__in=(user.organization, 0)).exists()
                    if not is_organization_user:
                        raise forms.ValidationError('{} não é usuário de {}'.format(username, user.organization))
                elif self.scope == LoginForm.UNIT:
                    user.unit = cleaned_data.get('login_scope', self.unit)
                    is_unit_user = user.role_set.filter(units__in=(user.unit, 0)).exists()
                    is_organization_user = loader.organization_model and user.role_set.filter(organizations__in=(user.unit.get_organization(), 0)).exists()
                    if not is_unit_user and not is_organization_user:
                        raise forms.ValidationError('{} não é usuário de {}'.format(username, user.unit))
                else:
                    roles = user.role_set.all()
                    if roles.count() == 1:
                        role = roles.first()
                        if role.scope:
                            self.request.session['scope'] = str(role.scope)
                            self.request.session.save()
                user.save()
                auth.login(self.request, user)
                return cleaned_data
            else:
                raise forms.ValidationError('Usuário inativo.')
        else:
            raise forms.ValidationError('Senha não confere.')

    def submit(self):
        url = self.request.GET.get('next', '/admin/')
        return httprr(self.request, url, 'Usuário autenticado com sucesso.')


class GroupForm(forms.ModelForm):
    name = forms.CharField(label='Name')

    class Meta:
        title = 'Cadastro de Grupo'
        submit_label = 'Cadastrar'
        icon = 'fa-users'
        model = Group
        fields = ('name',)


class UserForm(forms.ModelForm):
    is_superuser = forms.BooleanField(label='Superusuário', required=False)
    new_password = forms.PasswordField(label='Senha', required=False)

    class Meta:
        model = User
        fields = ('username', 'name', 'active', 'email', 'is_superuser', 'photo')
        title = 'Cadastro de Usuário'
        submit_label = 'Cadastrar'
        icon = 'fa-user'

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        if not args[0].user.is_superuser:
            del (self.fields['is_superuser'])
            self.fieldsets = (
                ('Identificação', {'fields': (('name', 'email',), 'photo')}),
                ('Acesso', {'fields': (('username', 'new_password'), ('active',))}),
            )
        else:
            self.fieldsets = (
                ('Identificação', {'fields': (('name', 'email',), 'photo')}),
                ('Acesso', {'fields': (('username', 'new_password'), ('active', 'is_superuser'))}),
            )

    def save(self, *args, **kwargs):
        user = super(UserForm, self).save(commit=False)
        if 'new_password' in self.cleaned_data and self.cleaned_data['new_password']:
            user.set_password(self.cleaned_data['new_password'])
        user.save()


class RegisterForm(forms.Form):
    name = forms.CharField(label='Nome', required=True)
    email = forms.EmailField(label='E-mail', required=True)
    new_password = forms.PasswordField(label='Senha', required=True)
    confirm_password = forms.PasswordField(label='Senha', required=True,
                                           help_text='Repita a senha digitada anteriormente')

    class Meta:
        title = 'Novo Usuário'
        icon = 'fa-user'
        submit_label = 'Cadastrar'
        captcha = True

    fieldsets = (
        ('Dados Gerais', {'fields': ('name', 'email')}),
        ('Senha de Acesso', {'fields': (('new_password', 'confirm_password'))}),
    )

    def clean(self):
        if not self.data['new_password'] == self.data['confirm_password']:
            raise forms.ValidationError('As senhas devem ser iguais.')
        return self.cleaned_data

    def save(self, *args, **kwargs):
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
        if True:
            user.save()
            return user
        else:
            token = encrypt('{};{};{};{}'.format(user.first_name, user.last_name, user.email, password))
            url = '{}/admin/create_user/{}/'.format(settings.SERVER_ADDRESS, token)
            user.email_user('Criação de Conta', 'Clique para confirmar a criação de sua conta: {}'.format(url),
                            settings.SYSTEM_EMAIL_ADDRESS)
            return None


class ChangePasswordForm(forms.ModelForm):
    new_password = forms.PasswordField(label='Senha', required=True)
    confirm_password = forms.PasswordField(label='Confirmação', required=True,
                                           help_text='Repita a senha digitada anteriormente')

    fieldsets = (('Senhas', {'fields': ('new_password', 'confirm_password',)}),)

    class Meta:
        model = User
        fields = ('id',)
        title = 'Alteração de Senha'
        submit_label = 'Alterar'
        icon = 'fa-key'

    def clean(self):
        if not self.data.get('new_password') == self.data.get('confirm_password'):
            raise forms.ValidationError('As senhas devem ser iguais.')
        return self.cleaned_data

    def save(self, *args, **kwargs):
        super(ChangePasswordForm, self).save(*args, **kwargs)
        User.objects.filter(pk=self.instance.pk).update(password=make_password(self.cleaned_data['new_password']))
        user = auth.authenticate(username=self.instance.username, password=self.cleaned_data['new_password'])
        auth.login(self.request, user)


class RecoverPassowordForm(forms.Form):
    email = forms.EmailField(label='E-mail')

    class Meta:
        captcha = True

    def clean(self):
        cleaned_data = super(RecoverPassowordForm, self).clean()
        qs = User.objects.filter(
            email=cleaned_data['email']
        )
        if qs.exists():
            qs[0].send_access_invitation()
            return cleaned_data
        else:
            raise forms.ValidationError('Usuário não encontrado')


class ProfileForm(forms.ModelForm):
    new_password = forms.PasswordField(label='Senha', required=False)
    confirm_password = forms.PasswordField(label='Confirmação', required=False,
                                           help_text='Repita a senha digitada anteriormente')

    class Meta:
        model = User
        fields = ('name', 'photo', 'username', 'email')
        title = 'Atualização de Perfil'
        submit_label = 'Atualizar Perfil'
        icon = 'fa-user'

    fieldsets = (
        ('Dados do Usuário', {'fields': (('name', 'username'), 'email', 'photo')}),
        ('Senha de Acesso', {'fields': (('new_password', 'confirm_password'),)}),
    )

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.username = self.instance.username

    def clean_confirm_password(self):
        if not self.data.get('new_password') == self.data.get('confirm_password'):
            raise forms.ValidationError('As senhas devem ser iguais.')
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
            for model in loader.role_models:
                attr = loader.role_models[model]['username_field']
                model.objects.filter(**{attr: self.username}).update(**{attr: self.request.user.username})


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        exclude = ()

    def __init__(self, *args, **kwargs):
        kwargs['instance'] = Settings.default()
        super(SettingsForm, self).__init__(*args, **kwargs)
