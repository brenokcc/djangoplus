# -*- coding: utf-8 -*-
import re
from django.conf import settings
from djangoplus.test import TestCase
from djangoplus.admin.models import User
from djangoplus.mail.utils import load_emails
from djangoplus.test.decorators import testcase
from django.utils.translation import ugettext as _


class AdminTestCase(TestCase):

    def test(self):
        User.objects.create_superuser(settings.DEFAULT_SUPERUSER, None, settings.DEFAULT_PASSWORD)
        self.execute_flow()

    @testcase('Configure')
    def configure(self):
        self.click_icon(_('Settings'))
        self.click_link(_('Edit Profile'))
        self.enter(_('Name'), 'Administrador')
        self.enter(_('Password'), '123')
        self.enter(_('Confirm Password'), '123')
        self.click_button(_('Save'))
        self.logout()
        self.login('admin', '123')
        self.click_icon(_('Settings'))
        self.click_link(_('Settings'))
        self.enter(_('Name'), 'My Project')
        self.click_button(_('Save'))

    @testcase('Create User')
    def create_user(self):
        self.click_icon(_('Users'))
        self.click_link(_('Add'))
        self.enter(_('Name'), 'Carlos Breno')
        self.enter(_('E-mail'), 'brenokcc@yahoo.com.br')
        self.enter(_('Username'), 'brenokcc')
        self.enter(_('Password'), 'senha')
        self.click_button(_('Save'))

    @testcase('Check User Password', username='brenokcc', password='senha')
    def check_user_password(self):
        self.look_at('Carlos Breno')

    @testcase('Check User Password')
    def check_user_password(self):
        self.click_icon(_('Users'))
        self.look_at('Carlos Breno')
        self.click_button(_('Change Password'))
        self.enter(_('Password'), '321')
        self.enter(_('Confirm Password'), '321')
        self.click_button(_('Save'))

    @testcase('Check User Password', username='brenokcc', password='321')
    def check_user_password_again(self):
        self.look_at('Carlos Breno')

    @testcase('Reset Password', username=None, password=None)
    def reset_password(self):
        self.open('/admin/logout/')
        self.open('/admin/login/')
        self.click_link(_('Reset Password'))
        self.enter('E-mail', 'brenokcc@yahoo.com.br')
        settings.EMAIL_BACKEND = 'djangoplus.mail.backends.EmailDebugBackend'
        self.click_button(_('Send E-mail'))
        emails = load_emails()
        url = re.findall('/admin/password/.*/"', '\n'.join(emails[0]['alternatives'][0]))[0][0:-1]
        self.open(url)
        self.enter(_('Password'), '111')
        self.enter(_('Confirm Password'), '111')
        self.click_button(_('Save'))
        self.logout()
