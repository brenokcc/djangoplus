# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import json
import urllib2
from djangoplus.cache import loader
from django.contrib import auth
from django.http.response import HttpResponse
from djangoplus.decorators.views import view
from djangoplus.ui.components.breadcrumbs import httprr
from djangoplus.admin.models import User, Unit, Organization
from djangoplus.utils.aescipher import decrypt
from djangoplus.ui.components.panel import DashboardPanel
from djangoplus.admin.forms import ProfileForm, ChangePasswordForm, \
    ResetPasswordForm, SettingsForm, LoginForm


@view('Public', login_required=False)
def public(request):
    return locals()


@view('Index', login_required=True)
def index(request):
    widget_panel = DashboardPanel(request)
    return locals()


@view('Login', login_required=False)
def login(request, scope=None, organization=None, unit=None):
    auth.logout(request)
    can_register = loader.signup_model is not None
    organization = organization and Organization.objects.get(pk=organization) or None
    unit = unit and Unit.objects.get(pk=unit) or None
    form = LoginForm(request, scope, organization, unit)
    if form.is_valid():
        return form.submit()
    return locals()


@view('Logout', login_required=False)
def logout(request):
    url = '/'
    unit_id = request.session.get('unit_id', None)
    if unit_id:
        url = '/admin/login/{}/'.format(unit_id)
    auth.logout(request)
    return httprr(request, url, 'Logout realizado com sucesso.')


@view('404')
def error(request):
    return locals()


@view('Change Password')
def password(request, pk=None):
    title = 'Alterar Senha'

    if not pk:
        user = request.user
    else:
        pk = len(pk) < 10 and pk or decrypt(pk)
        user = User.objects.get(pk=pk)

    form = ChangePasswordForm(request, instance=user)

    if form.is_valid():
        form.instance.set_password(form.cleaned_data['new_password'])
        form.save()
        return httprr(request, '..', 'Senha alterada com sucesso')
    return locals()


@view('Reset Password')
def reset_password(request):
    form = ResetPasswordForm(request)
    if form.is_valid():
        form.submit()
        return httprr(request, '..', 'E-mail enviado com sucesso.')
    return locals()


@view('Register', login_required=False)
def register(request, token=None, userid=None):
    from djangoplus.ui.components import forms
    from djangoplus.utils.metadata import get_metadata

    initial = {}
    username_field = get_metadata(loader.signup_model, 'role_username')
    email_field = get_metadata(loader.signup_model, 'role_email')
    name_field = get_metadata(loader.signup_model, 'role_name')

    if not loader.signup_model:
        return httprr(request, '/admin/login/', 'O cadastrado externo não está habilitado.')

    if token:
        if token and userid:
            url = 'https://graph.facebook.com/{}?fields=email,first_name,last_name&access_token={}'.format(userid, token)
        elif token:
            url = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token={}'.format(token)
        data = json.loads(urllib2.urlopen(url).read())
        qs = User.objects.filter(username=data['email'])
        if qs.exists():
            user = qs[0]
            auth.login(request, user)
            return httprr(request, '/admin/', 'Usuário autenticado com sucesso.')
        else:
            initial = {name_field: data['name'], username_field : data['email'], email_field : data['email']}

    class RegisterForm(forms.ModelForm):
        class Meta:
            model = loader.signup_model
            fields = get_metadata(loader.signup_model, 'form_fields', '__all__')
            exclude = get_metadata(loader.signup_model, 'exclude_fields', ())
            submit_label = 'Cadastrar'
            title = 'Cadastro de {}'.format(get_metadata(loader.signup_model, 'verbose_name'))
            icon = get_metadata(loader.signup_model, 'icon', None)


    form = RegisterForm(request, initial=initial)
    form.fields[username_field].help_text='Utilizado para acessar o sistema.'

    save_instance = True
    for field_name in form.fields:
        if not initial.get(field_name):
            save_instance = False
    if save_instance:
        instance = loader.signup_model()
        for field_name in form.fields:
            setattr(instance, field_name, initial[field_name])
        instance.save()
        user = User.objects.get(username=initial[username_field])
        auth.login(request, user)
        return httprr(request, '/admin/', 'Usuário cadastrado com sucesso.')

    if form.is_valid():
        instance = form.save()
        extra = email_field and 'Um e-mail será enviado para você tão logo sua conta seja ativada.' or ''
        if instance:
            user = User.objects.get(username=form.cleaned_data[username_field])
            auth.login(request, user)
            return httprr(request, '/admin/', 'Usuário cadastrado com sucesso.')
        else:
            return httprr(request, '..', 'Acesse o link enviado para seu e-mail para confirmar a criação da sua conta.')
    return locals()


@view('Register Confirmation')
def create_user(request, token):
    user = User()
    user.first_name, user.last_name, user.email, password = decrypt(token).split(';')
    user.is_active = True
    user.is_superuser = False
    user.last_login = datetime.datetime.now()
    user.date_joined = datetime.datetime.now()
    user.username = user.email
    user.set_password(password)
    user.save()
    return httprr(request, '/admin/login/', 'Conta confirmada com sucesso.')


@view('Profile')
def profile(request):
    form = ProfileForm(request, instance=request.user)
    if form.is_valid():
        form.save()
        return httprr(request, '..', 'Perfil atualizado com sucesso')
    return locals()


@view('Configure')
def configure(request):
    if not request.user.is_superuser:
        return httprr(request, '/', 'Você não tem permissão para realizar isto!', 'error')
    title = 'Configurações'
    form = SettingsForm(request)
    if form.is_valid():
        form.save()
        return httprr(request, '..', 'Configuração salva com sucesso')
    return locals()


@view('Sidebar')
def toggle_menu(request):
    if 'hidden_menu' in request.session and request.session['hidden_menu']:
        request.session['hidden_menu'] = False
    else:
        request.session['hidden_menu'] = True
    request.session.save()
    return HttpResponse()





