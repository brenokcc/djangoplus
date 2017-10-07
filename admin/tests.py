# -*- coding: utf-8 -*-
from djangoplus.admin.models import User
from djangoplus.test import TestCase
from django.conf import settings


class AdminTestCase(TestCase):

    def test_app(self):

        User.objects.create_superuser('admin', None, settings.DEFAULT_PASSWORD)

        self.open('/')
        self.wait(2)

        self.login(u'admin', settings.DEFAULT_PASSWORD)
        self.click_icon(u'Configurações')
        self.click_link('Editar Perfil')
        self.enter(u'Nome', u'Administrador')
        self.enter(u'Senha', '123')
        self.enter(u'Confirmação', '123')
        self.click_button(u'Atualizar Perfil')
        self.logout()
        self.login(u'admin', u'123')
        self.click_icon(u'Configurações')
        self.click_link(u'Configurações')
        self.enter(u'Nome', u'My Project')
        self.click_button(u'Atualizar')

        self.click_icon(u'Usuários')
        self.click_link(u'Cadastrar')
        self.enter(u'Nome', u'Carlos Breno')
        self.enter(u'E-mail', u'brenokcc@yahoo.com.br')
        self.enter(u'Login', u'brenokcc')
        self.enter(u'Senha', u'senha')
        self.click_button(u'Cadastrar')
        self.logout()
        self.login(u'brenokcc', 'senha')
        self.logout()

        self.login(u'admin', u'123')
        self.click_icon(u'Usuários')
        self.look_at(u'Carlos Breno')

        self.click_button(u'Alterar Senha')
        self.enter(u'Senha', '321')
        self.enter(u'Confirmação', '321')
        self.click_button(u'Alterar')
        self.logout()

        self.login(u'brenokcc', u'321')
        self.logout()
