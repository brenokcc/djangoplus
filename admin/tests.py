# -*- coding: utf-8 -*-

from django.conf import settings
from djangoplus.test import TestCase
from djangoplus.admin.models import User
from djangoplus.test.decorators import testcase


class AdminTestCase(TestCase):

    def test(self):
        User.objects.create_superuser(settings.DEFAULT_SUPERUSER, None, settings.DEFAULT_PASSWORD)
        self.execute_flow()

    @testcase('Configure')
    def configure(self):
        self.click_icon('Configurações')
        self.click_link('Editar Perfil')
        self.enter('Nome', 'Administrador')
        self.enter('Senha', '123')
        self.enter('Confirmação', '123')
        self.click_button('Atualizar Perfil')
        self.logout()
        self.login('admin', '123')
        self.click_icon('Configurações')
        self.click_link('Configurações')
        self.enter('Nome', 'My Project')
        self.click_button('Atualizar')

    @testcase('Create User')
    def create_user(self):
        self.click_icon('Usuários')
        self.click_link('Cadastrar')
        self.enter('Nome', 'Carlos Breno')
        self.enter('E-mail', 'brenokcc@yahoo.com.br')
        self.enter('Login', 'brenokcc')
        self.enter('Senha', 'senha')
        self.click_button('Cadastrar')

    @testcase('Check User Password', username='brenokcc', password='senha')
    def check_user_password(self):
        self.look_at('Carlos Breno')

    @testcase('Check User Password')
    def check_user_password(self):
        self.click_icon('Usuários')
        self.look_at('Carlos Breno')
        self.click_button('Alterar Senha')
        self.enter('Senha', '321')
        self.enter('Confirmação', '321')
        self.click_button('Alterar')

    @testcase('Check User Password', username='brenokcc', password='321')
    def check_user_password(self):
        self.look_at('Carlos Breno')
