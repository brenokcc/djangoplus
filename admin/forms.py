# -*- coding: utf-8 -*-
import datetime
from djangoplus.ui.components import forms
from django.contrib import auth
from django.conf import settings
from djangoplus.cache import loader
from djangoplus.ui.components.breadcrumbs import httprr
from djangoplus.utils.aescipher import encrypt
from djangoplus.admin.models import Group, User, Unit, Role, Settings, Organization


class LoginForm(forms.Form):
    
    ORGANIZATION = 'organization'
    UNIT = 'unit'
    
    username = forms.CharField(label=u'Usuário')
    password = forms.PasswordField(label=u'Senha',
                                   help_text=u'Caso tenha esquecido sua senha, clique aqui para '
                                   u'<a class="popup" href="/admin/reset_password/">alterá-la</a>.')

    def __init__(self, request, scope=None, organization=None, unit=None, *args, **kwargs):
        super(LoginForm, self).__init__(request, *args, **kwargs)
        self.scope = None
        self.fields['username'].widget.attrs['class'] = 'input-sm bounceIn animation-delay2'
        if scope:
            if scope == LoginForm.ORGANIZATION or scope == (loader.organization_model and loader.organization_model.__name__.lower()):
                if organization:
                    self.scope_display = organization
                else:
                    organizations = Organization.objects.exclude(pk=0)
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
                        units = Unit.objects.exclude(pk=0)
                    self.fields['login_scope'] = forms.ModelChoiceField(units)
                self.scope = LoginForm.UNIT
        self.organization = organization
        self.unit = unit

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if not User.objects.filter(username=username).exists():
            raise forms.ValidationError(u'Usuário não cadastrado.')
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            if user.active:
                user.permission_mapping = ''
                user.organization = None
                user.unit = None
                if self.scope == LoginForm.ORGANIZATION:
                    user.organization = self.cleaned_data.get('login_scope', self.organization)
                    is_organization_user = user.role_set.filter(organizations__in=(user.organization, 0)).exists()
                    if not is_organization_user:
                        raise forms.ValidationError(u'%s não é usuário de %s' % (username, user.organization))
                elif self.scope == LoginForm.UNIT:
                    user.unit = self.cleaned_data.get('login_scope', self.unit)
                    is_unit_user = user.role_set.filter(units__in=(user.unit, 0)).exists()
                    is_organization_user = loader.organization_model and user.role_set.filter(organizations__in=(user.unit.get_organization(), 0)).exists()
                    if not is_unit_user and not is_organization_user:
                        raise forms.ValidationError(u'%s não é usuário de %s' % (username, user.unit))
                user.save()
                auth.login(self.request, user)
                return self.cleaned_data
            else:
                raise forms.ValidationError(u'Usuário inativo.')
        else:
            raise forms.ValidationError(u'Senha não confere.')

    def submit(self):
        url = self.request.GET.get('next', '/admin/')
        return httprr(self.request, url, u'Usuário autenticado com sucesso.')


class GroupForm(forms.ModelForm):
    name = forms.CharField(label=u'Name')

    class Meta:
        title = 'Cadastro de Grupo'
        submit_label = 'Cadastrar'
        icon = 'fa-users'
        model = Group
        fields = ('name',)


class UserForm(forms.ModelForm):
    is_superuser = forms.BooleanField(label=u'Superusuário', required=False)
    new_password = forms.PasswordField(label=u'Senha', required=False)

    class Meta:
        model = User
        fields = ('username', 'name', 'active', 'email', 'is_superuser')
        title = 'Cadastro de Usuário'
        submit_label = 'Cadastrar'
        icon = 'fa-user'

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        if not args[0].user.is_superuser:
            del (self.fields['is_superuser'])
            self.fieldsets = (
                (u'Identificação', {'fields': ('name', 'email',)}),
                (u'Acesso', {'fields': (('username', 'new_password'), ('active',))}),
            )
        else:
            self.fieldsets = (
                (u'Identificação', {'fields': ('name', 'email',)}),
                (u'Acesso', {'fields': (('username', 'new_password'), ('active', 'is_superuser'))}),
            )

    def save(self, *args, **kwargs):
        user = super(UserForm, self).save(commit=False)
        if 'new_password' in self.cleaned_data and self.cleaned_data['new_password']:
            user.set_password(self.cleaned_data['new_password'])
        user.save()


class RegisterForm(forms.Form):
    name = forms.CharField(label='Nome', required=True)
    email = forms.EmailField(label='E-mail', required=True)
    new_password = forms.PasswordField(label=u'Senha', required=True)
    confirm_password = forms.PasswordField(label=u'Senha', required=True,
                                           help_text=u'Repita a senha digitada anteriormente')

    class Meta:
        title = u'Novo Usuário'
        icon = u'fa-user'
        submit_label = 'Cadastrar'

    fieldsets = (
        (u'Dados Gerais', {'fields': ('name', 'email')}),
        (u'Senha de Acesso', {'fields': (('new_password', 'confirm_password'))}),
    )

    def clean(self):
        if not self.data['new_password'] == self.data['confirm_password']:
            raise forms.ValidationError(u'As senhas devem ser iguais.')
        return self.cleaned_data

    def save(self, *args, **kwargs):
        user = User()
        password = self.cleaned_data['new_password']
        user.name = self.cleaned_data['name']
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        user.active = True
        user.is_superuser = False
        user.last_login = datetime.datetime.now()
        user.date_joined = datetime.datetime.now()
        user.username = user.email
        user.set_password(password)
        if True:
            user.save()
            return user
        else:
            token = encrypt('%s;%s;%s;%s' % (user.first_name, user.last_name, user.email, password))
            url = u'%s/admin/create_user/%s/' % (settings.SERVER_ADDRESS, token)
            user.email_user(u'Criação de Conta', u'Clique para confirmar a criação de sua conta: %s' % url,
                            settings.SYSTEM_EMAIL_ADDRESS)
            return None


class ResetPasswordForm(forms.Form):
    mail = forms.CharField(label=u'E-mail')

    class Meta:
        title = u'Alteração de Senha'
        icon = u'mdi-content-mail'
        submit_label = u'Enviar E-mail'
        note = u'Ao preencher e submeter o formulário abaixo, um e-mail será enviado para vocêcontendo ' \
               u'um link através do qual você poderá alterar sua senha.'

    def clean_mail(self):
        self.qs = User.objects.filter(email=self.cleaned_data['mail'])
        if self.qs.exists():
            return self.cleaned_data['mail']
        else:
            raise forms.ValidationError(u'E-mail não cadastrado.')

    def submit(self):
        user = self.qs[0]
        token = encrypt('%s' % user.pk)
        url = '%s/admin/password/%s/' % (settings.SERVER_ADDRESS, token)
        user.email_user(u'Recuperação de Senha', u'Clique no link a seguir para alterar sua senha: %s' % url,
                        settings.SYSTEM_EMAIL_ADDRESS)


class ChangePasswordForm(forms.ModelForm):
    new_password = forms.PasswordField(label=u'Senha', required=True)
    confirm_password = forms.PasswordField(label=u'Confirmação', required=True,
                                           help_text=u'Repita a senha digitada anteriormente')

    fieldsets = ((u'Senhas', {'fields': ('new_password', 'confirm_password',)}),)

    class Meta:
        model = User
        fields = ('id',)
        title = u'Alteração de Senha'
        submit_label = 'Alterar'
        icon = 'fa-key'

    def clean(self):
        if not self.data.get('new_password') == self.data.get('confirm_password'):
            raise forms.ValidationError(u'As senhas devem ser iguais.')
        return self.cleaned_data

    def save(self, *args, **kwargs):
        super(ChangePasswordForm, self).save(*args, **kwargs)
        password = self.cleaned_data['new_password']

        if password:
            self.instance.set_password(password)
            self.instance.save()
            user = auth.authenticate(username=self.cleaned_data.get('username'), password=password)
        else:
            user = self.instance
        auth.login(self.request, user)


class ProfileForm(forms.ModelForm):
    new_password = forms.PasswordField(label=u'Senha', required=False)
    confirm_password = forms.PasswordField(label=u'Confirmação', required=False,
                                           help_text=u'Repita a senha digitada anteriormente')

    class Meta:
        model = User
        fields = ('name', 'photo', 'username')
        title = u'Atualização de Perfil'
        submit_label = u'Atualizar Perfil'
        icon = 'fa-edit'

    fieldsets = (
        (u'Dados do Usuário', {'fields': (('name', 'username'), 'photo')}),
        (u'Senha de Acesso', {'fields': (('new_password', 'confirm_password'),)}),
    )

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.username = self.instance.username

    def clean_confirm_password(self):
        if not self.data.get('new_password') == self.data.get('confirm_password'):
            raise forms.ValidationError(u'As senhas devem ser iguais.')
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


class RoleForm(forms.ModelForm):
    units = forms.MultipleModelChoiceField(Unit.objects.all(), label=u'Unidades', required=False)

    class Meta():
        model = Role
        fields = ('id',)

    def __init__(self, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.fields['units'].initial = self.instance.units.values_list('id', flat=True)


class SettingsForm(forms.ModelForm):
    class Meta():
        model = Settings
        exclude = ()

    def __init__(self, *args, **kwargs):
        kwargs['instance'] = Settings.default()
        super(SettingsForm, self).__init__(*args, **kwargs)
