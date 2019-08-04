# -*- coding: utf-8 -*-
import sys
import json
import urllib
from django.core import signing
from django.contrib import auth
from django.conf import settings
from djangoplus.mail import utils
from djangoplus.cache import CACHE
from djangoplus.utils.icons import ICONS
from djangoplus.admin.models import Settings
from django.http.response import HttpResponse
from django.utils.translation import ugettext as _
from djangoplus.decorators.views import view, action
from djangoplus.ui.components.panel import AppDashboard
from djangoplus.admin.models import User, Unit, Organization
from djangoplus.ui.components.navigation.breadcrumbs import httprr
from djangoplus.admin.forms import ProfileForm, ChangePasswordForm, SettingsForm, LoginForm, RecoverPassowordForm


@view(_('Public'), login_required=False)
def public(request):
    app_settings = Settings.default()
    if not app_settings.background:
        return httprr(request, '/admin/')
    return locals()


@view(_('Main'), login_required=True)
def index(request):
    widget_panel = AppDashboard(request)
    return locals()


@view(_('System Access'), login_required=False, template='login/login.html')
def login(request, scope=None, organization=None, unit=None):
    auth.logout(request)
    can_register = CACHE['SIGNUP_MODEL'] is not None

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


@view(_('Logout'), login_required=False)
def logout(request):
    url = '/'
    unit_id = request.session.get('unit_id', None)
    if unit_id:
        url = '/admin/login/{}/'.format(unit_id)
    auth.logout(request)
    return httprr(request, url, _('You have successfully logged out.'))


@view('404')
def error(request):
    return locals()


@view(_('Change Password'), login_required=False, template='login/password.html')
def password(request, pk, token):
    title = _('Change Password')
    user = User.objects.filter(pk=pk, password=signing.loads(token)).first()
    if user:
        form = ChangePasswordForm(request, instance=user)
        if form.is_valid():
            form.save()
            return httprr(request, '/admin/', _('Your password has been successfully changed.'))
    else:
        return httprr(request, '/', _('No records found'))
    return locals()


@view(_('Reset Password'), login_required=False, template='login/reset.html')
def reset(request):
    title = _('Reset Password')
    form = RecoverPassowordForm(request)
    if form.is_valid():
        msg = _('Click on the link sent to your e-mail to reset your password.')
        return httprr(request, '/admin/login/', msg)
    return locals()


@view(_('Register'), login_required=False)
def register(request, token=None, userid=None):
    from djangoplus.ui.components import forms
    from djangoplus.utils.metadata import get_metadata

    initial = {}
    username_field = get_metadata(CACHE['SIGNUP_MODEL'], 'role_username')
    email_field = get_metadata(CACHE['SIGNUP_MODEL'], 'role_email')
    name_field = get_metadata(CACHE['SIGNUP_MODEL'], 'role_name')

    if not CACHE['SIGNUP_MODEL']:
        return httprr(request, '/admin/login/', _('Sign-up not enabled.'))

    if token:
        if token and userid:
            url = 'https://graph.facebook.com/{}?fields=email,first_name,last_name&access_token={}'
            url = url.format(userid, token)
        elif token:
            url = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token={}'.format(token)
        data = json.loads(urllib.request.urlopen(url).read())
        qs = User.objects.filter(username=data['email'])
        if qs.exists():
            user = qs[0]
            auth.login(request, user)
            return httprr(request, '/admin/', _('You have successfully logged in.'))
        else:
            initial = {name_field: data.get('name'), username_field: data['email'], email_field: data['email']}

    class RegisterForm(forms.ModelForm):
        class Meta:
            model = CACHE['SIGNUP_MODEL']
            fields = get_metadata(CACHE['SIGNUP_MODEL'], 'form_fields', '__all__')
            exclude = get_metadata(CACHE['SIGNUP_MODEL'], 'exclude_fields', ())
            submit_label = _('Register')
            title = '{} {}'.format(_('Register'), get_metadata(CACHE['SIGNUP_MODEL'], 'verbose_name'))
            icon = get_metadata(CACHE['SIGNUP_MODEL'], 'icon', None)
            captcha = settings.CAPTCHA_KEY and settings.CAPTCHA_SECRET and 'test' not in sys.argv or False

    form = RegisterForm(request, initial=initial)
    form.fields[username_field].help_text = _('Used to access the system')

    save_instance = True
    for field_name in form.fields:
        if not initial.get(field_name):
            save_instance = False
    if save_instance:
        instance = CACHE['SIGNUP_MODEL']()
        for field_name in form.fields:
            setattr(instance, field_name, initial[field_name])
        instance.save()
        user = User.objects.get(username=initial[username_field])
        auth.login(request, user)
        return httprr(request, '/admin/', _('You were successfully registered.'))

    if form.is_valid():
        instance = form.save()
        extra = email_field and _('An e-mail will be sent to you as soon as your account is activated.') or ''
        if instance:
            user = User.objects.get(username=form.cleaned_data[username_field])
            auth.login(request, user)
            return httprr(request, '/admin/', _('User successfully registered.'))
        else:
            return httprr(request, '..', _('Click on the link sent to your e-mail to have you account activated.'))
    return locals()


@view(_('Profile'))
def profile(request):
    form = ProfileForm(request, instance=request.user)
    if form.is_valid():
        form.save()
        return httprr(request, '..', _('Profile successfully updated.'))
    return locals()


@view(_('Configure'))
def configure(request):
    if not request.user.is_superuser:
        return httprr(request, '/', _('You do not have permission to access this page!'), 'error')
    title = _('Settings')
    form = SettingsForm(request)
    if form.is_valid():
        form.save()
        return httprr(request, '..', _('Configuration successfully updated.'))
    return locals()


@view(_('Sidebar'))
def toggle_menu(request):
    if 'hidden_menu' in request.session and request.session['hidden_menu']:
        request.session['hidden_menu'] = False
    else:
        request.session['hidden_menu'] = True
    request.session.save()
    return HttpResponse()


@action(User, _('Login as User'), can_execute='Superuser')
def login_as(request, pk):
    auth.logout(request)
    user = User.objects.get(pk=pk)
    auth.login(request, user)
    return httprr(request, '/admin/', _('User successfully authenticated.'))


@view(_('View E-mails'), login_required=False)
def emails(request):
    messages = utils.load_emails()
    return locals()


@view(_('Icons'), login_required=False)
def icons(request):
    icon_names = ICONS
    return locals()



