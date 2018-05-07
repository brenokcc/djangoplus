# -*- coding: utf-8 -*-
import os
import datetime
from selenium import webdriver
import traceback, time, json
from django.conf import settings
from djangoplus.test import cache
from django.core import serializers
from django.core.management import call_command
from selenium.webdriver.firefox.options import Options
from django.utils.translation import ugettext_lazy as _
from selenium.common.exceptions import WebDriverException
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class TestCase(StaticLiveServerTestCase):

    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)
        self.login_count = 0
        self.current_username = None
        self.current_password = None
        self.restored = False
        self.watched = False

    def setUp(self):
        super(TestCase, self).setUp()
        self.slowly = False
        self.username = None
        options = Options()
        options.add_argument("--window-size=1920x1080")
        if 'HEADLESS' in os.environ:
            options.add_argument("--headless")
        self.driver = webdriver.Firefox(options=options)

    def create_superuser(self, username, password):
        from djangoplus.admin.models import User
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, None, password)

    def watch(self, e):
        if self.watched:
            raise e
        else:
            traceback.print_exc()
            self.watched = True
            self.driver.save_screenshot('/tmp/test.png')
            if 'HEADLESS' not in os.environ:
                input('Type enter to continue...')

    def slow_down(self):
        self.slowly = True

    def wait(self, seconds=1):
        seconds = self.slowly and 3 or seconds
        time.sleep(seconds)

    def open(self, url):
        self.driver.get("{}{}".format(self.live_server_url, url))

    def enter(self, name, value, submit=False, count=2):

        if callable(value):
            value = value()
        if type(value) == datetime.date:
            value = value.strftime('%d/%m/%Y')
        if value:
            print('{} "{}" for "{}"'.format('Entering', value, name))
        try:
            if submit:
                self.driver.execute_script("enter('{}', '{}', 1)".format(name, value))
            else:
                self.driver.execute_script("enter('{}', '{}')".format(name, value))
        except WebDriverException as e:
            if count:
                self.wait()
                self.enter(name, value, submit, count-1)
            else:
                self.watch(e)

    def choose(self, name, value, count=2):
        print('{} "{}" for "{}"'.format('Choosing', value, name))
        try:
            headless = 'HEADLESS' in os.environ and 'true' or 'false'
            self.driver.execute_script("return choose('{}', '{}', {})".format(name, value, headless))
            self.wait(2)
        except WebDriverException as e:
            if count:
                self.wait()
                self.choose(name, value, count-1)
            else:
                self.watch(e)

    def look_for(self, text, count=2):
        print('Looking for "{}"'.format(text))
        try:
            assert text in self.driver.find_element_by_tag_name('body').text
        except WebDriverException as e:
            if count:
                self.wait()
                self.look_for(text, count-1)
            else:
                self.watch(e)

    def look_at_popup_window(self, count=2):
        print('Looking at popup window')
        try:
            self.driver.execute_script("lookAtPopupWindow()")
        except WebDriverException as e:
            if count:
                self.wait()
                self.look_at_popup_window(count-1)
            else:
                self.watch(e)

    def look_at(self, text, count=2):
        print('Loking at "{}"'.format(text))
        try:
            self.driver.execute_script("lookAt('{}')".format(text))
        except WebDriverException as e:
            if count:
                self.wait()
                self.look_at(text, count-1)
            else:
                self.watch(e)

    def look_at_panel(self, text, count=2):
        print('Looking at panel "{}"'.format(text))
        try:
            self.driver.execute_script("lookAtPanel('{}')".format(text))
        except WebDriverException as e:
            if count:
                self.wait()
                self.look_at_panel(text, count-1)
            else:
                self.watch(e)

    def click_menu(self, *texts):
        print('Clicking menu "{}"'.format('->'.join(texts)))
        self.wait()
        for text in texts:
            self.wait()
            try:
                self.driver.execute_script("clickMenu('{}')".format(text.strip()))
            except WebDriverException as e:
                self.watch(e)
        self.wait()

    def click_link(self, text):
        print('Clicking link "{}"'.format(text))
        try:
            self.driver.execute_script("clickLink('{}')".format(text))
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def click_button(self, text):
        print('Clicking button "{}"'.format(text))
        try:
            self.driver.execute_script("clickButton('{}')".format(text))
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def click_tab(self, text):
        print('Clicking tab "{}"'.format(text))
        try:
            self.driver.execute_script("clickTab('{}')".format(text))
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def click_icon(self, name):
        print('Clicking icon "{}"'.format(name))
        try:
            self.driver.execute_script("clickIcon('{}')".format(name))
        except WebDriverException as e:
            self.watch(e)
        self.wait()

    def login(self, username, password):
        print('Logging as', username)
        self.login_count += 1
        self.current_username = username
        self.current_password = password

        if self.login_count >= cache.LOGIN_COUNT:

            self.dump()

            self.open('/admin/login/')
            self.enter(_('Username'), username)
            self.enter(_('Password'), password, True)
            self.wait()

            return True

        else:
            if not self.restored:
                self.restore()
            return False

    def logout(self):
        print('Logging out')
        self.click_icon('Configurações')
        self.wait()
        self.click_link('Sair')
        self.wait()
        self.username = None

    def tearDown(self):
        super(TestCase, self).tearDown()
        self.driver.close()
        self.driver.service.stop()
        # len(self._resultForDoCleanups.errors)>0

    def dump(self, failed=False):
        file_path = '/tmp/{}.test'.format(settings.PROJECT_NAME)
        dump_file_path = '/tmp/{}.json'.format(settings.PROJECT_NAME)

        data = dict(login_count=self.login_count, username=self.current_username, password=self.current_password)
        open(file_path, 'w').write(json.dumps(data))
        output = open(dump_file_path,'w')
        app_labels = []
        for app in settings.INSTALLED_APPS:
            app_label = app.split('.')[-1]
            if app_label not in 'auth':
                app_labels.append(app_label)
        call_command('dumpdata', *app_labels, format='json', indent=3, stdout=output)
        output.close()

    def restore(self):
        dump_file_path = '/tmp/{}.json'.format(settings.PROJECT_NAME)
        call_command('loaddata', dump_file_path)
        self.restored = True

    def pause(self):
        import pdb
        pdb.set_trace()
