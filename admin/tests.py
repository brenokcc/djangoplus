# -*- coding: utf-8 -*-

from djangoplus.admin.models import User
from djangoplus.test import TestCase
from django.conf import settings


class AdminTestCase(TestCase):

    def test_app(self):

        User.objects.create_superuser('admin', None, settings.DEFAULT_PASSWORD)

        self.open('/')
        self.wait(2)

        self.login('admin', settings.DEFAULT_PASSWORD)
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

        self.click_icon('Usuários')
        self.click_link('Cadastrar')
        self.enter('Nome', 'Carlos Breno')
        self.enter('E-mail', 'brenokcc@yahoo.com.br')
        self.enter('Login', 'brenokcc')
        self.enter('Senha', 'senha')
        self.click_button('Cadastrar')
        self.logout()
        self.login('brenokcc', 'senha')
        self.logout()

        self.login('admin', '123')
        self.click_icon('Usuários')
        self.look_at('Carlos Breno')

        self.click_button('Alterar Senha')
        self.enter('Senha', '321')
        self.enter('Confirmação', '321')
        self.click_button('Alterar')
        self.logout()

        self.login('brenokcc', '321')
        self.logout()
