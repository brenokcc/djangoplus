# -*- coding: utf-8 -*-
import sys
import json
from djangoplus.admin.models import Settings
import urllib
from djangoplus.test import cache
from djangoplus.mail import utils
from djangoplus.cache import loader
from django.contrib import auth
from django.conf import settings
from djangoplus.utils.aescipher import decrypt
from django.http.response import HttpResponse
from djangoplus.decorators.views import view, action
from djangoplus.ui.components.navigation.breadcrumbs import httprr
from djangoplus.admin.models import User, Unit, Organization
from djangoplus.ui.components.panel import DashboardPanel
from djangoplus.admin.forms import ProfileForm, ChangePasswordForm, SettingsForm, LoginForm, RecoverPassowordForm


@view('Public', login_required=False)
def public(request):
    app_settings = Settings.default()
    if not app_settings.background:
        return httprr(request, '/admin/')
    return locals()


@view('Principal', login_required=True)
def index(request):
    widget_panel = DashboardPanel(request)
    return locals()


@view('Acesso ao Sistema', login_required=False, template='login/login.html')
def login(request, scope=None, organization=None, unit=None):
    auth.logout(request)
    can_register = loader.signup_model is not None

    allow_social_login = 'test' not in sys.argv
    google_auth_key = settings.GOOGLE_AUTH_KEY
    google_auth_id = settings.GOOGLE_AUTH_ID
    facebook_auth_id = settings.FACEBOOK_AUTH_ID

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


@view('Alteração de Senha', login_required=False, template='login/password.html')
def password(request, pk, token):
    title = 'Alterar Senha'
    user = User.objects.get(pk=pk, password=decrypt(token))
    form = ChangePasswordForm(request, instance=user)
    if form.is_valid():
        form.save()
        return httprr(request, '/admin/', 'Parabéns! Sua senha foi alterada com sucesso.')
    return locals()


@view('Recuperação de Senha', login_required=False, template='login/recover.html')
def recover(request):
    title = 'Recuperar Senha'
    form = RecoverPassowordForm(request)
    if form.is_valid():
        return httprr(request, '/admin/login/', 'O link para redefinição da senha foi enviado para o e-mail informado.')
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
        data = json.loads(urllib.request.urlopen(url).read())
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
            captcha = settings.CAPTCHA_KEY and settings.CAPTCHA_SECRET and 'test' not in sys.argv or False

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


@action(User, 'Login as User', can_execute='Superuser')
def login_as(request, pk):
    auth.logout(request)
    user = User.objects.get(pk=pk)
    auth.login(request, user)
    return httprr(request, '/admin/', 'Login realizado com sucesso')


@view('View E-mails')
def emails(request):
    messages = utils.load_emails()
    return locals()




