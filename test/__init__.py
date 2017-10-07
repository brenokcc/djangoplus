# -*- coding: utf-8 -*-
import datetime
from selenium import webdriver
import traceback, time, json
from django.conf import settings
from djangoplus.test import cache
from django.core import serializers
from django.core.management import call_command
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
        try:
            self.driver = webdriver.Chrome()
        except:
            self.driver = webdriver.Firefox()

        self.driver.set_window_size(1400, 1000)


        data = '''[{"model": "admin.organization", "pk": 0, "fields": {"ascii": ""}}, {"model": "admin.unit", "pk": 0, "fields": {"ascii": ""}}]'''
        for obj in serializers.deserialize("json", data):
            obj.save()

        settings.DEBUG = True

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
            raw_input('Type enter to continue...')

    def slow_down(self):
        self.slowly = True

    def wait(self, seconds=1):
        seconds = self.slowly and 3 or seconds
        time.sleep(seconds)

    def open(self, url):
        self.driver.get(u"%s%s" % (self.live_server_url, url))

    def enter(self, name, value, submit=False):

        if callable(value):
            value = value()
        if type(value) == datetime.date:
            value = value.strftime('%d/%m/%Y')

        print u'Entering ', value
        try:
            if submit:
                self.driver.execute_script(u"enter('%s', '%s', 1)" % (name, value))
            else:
                self.driver.execute_script(u"enter('%s', '%s')" % (name, value))
        except WebDriverException, e:
            self.watch(e)

    def choose(self, name, value):
        print u'Choosing', value
        try:
            self.driver.execute_script("return choose('%s', '%s')" % (name, value))
            self.wait(2)
        except WebDriverException, e:
            self.watch(e)

    def look_for(self, text):
        print u'Looking for', text
        self.wait()
        try:
            assert text in self.driver.find_element_by_tag_name('body').text
        except WebDriverException, e:
            self.watch(e)

    def look_at_popup_window(self):
        print u'Looking at popup window'
        self.wait()
        try:
            self.driver.execute_script(u"lookAtPopupWindow()")
        except WebDriverException, e:
            self.watch(e)

    def look_at(self, text):
        print u'Loking at', text
        self.wait()
        try:
            self.driver.execute_script(u"lookAt('%s')" % text)
        except WebDriverException, e:
            self.watch(e)

    def look_at_panel(self, text):
        print u'Looking at panel', text
        self.wait()
        try:
            self.driver.execute_script(u"lookAtPanel('%s')" % text)
        except WebDriverException, e:
            self.watch(e)

    def click_menu(self, *texts):
        print u'Clicking menu', '->'.join(texts)
        for text in texts:
            self.wait()
            try:
                self.driver.execute_script(u"clickMenu('%s')" % text.strip())
            except WebDriverException, e:
                self.watch(e)
        self.wait()

    def click_link(self, text):
        print u'Clicking link', text
        try:
            self.driver.execute_script(u"clickLink('%s')" % text)
        except WebDriverException, e:
            self.watch(e)
        self.wait()

    def click_button(self, text):
        print u'Clicking button', text
        try:
            self.driver.execute_script(u"clickButton('%s')" % text)
        except WebDriverException, e:
            self.watch(e)
        self.wait()

    def click_icon(self, name):
        print u'Clicking icon', name
        try:
            self.driver.execute_script(u"clickIcon('%s')" % name)
        except WebDriverException, e:
            self.watch(e)
        self.wait()

    def login(self, username, password):
        print u'Logging as', username
        self.login_count += 1
        self.current_username = username
        self.current_password = password

        if self.login_count >= cache.LOGIN_COUNT:

            self.dump()

            self.open('/admin/login/')
            self.enter(_(u'Username'), username)
            self.enter(_(u'Password'), password, True)
            self.wait()

            return True

        else:
            if not self.restored:
                self.restore()
            return False

    def logout(self):
        print u'Logging out'
        self.click_icon(u'Configurações')
        self.click_link('Sair')
        self.wait()
        self.username = None

    def tearDown(self):
        super(TestCase, self).tearDown()
        #self.driver.close()
        self.driver.service.stop()
        # len(self._resultForDoCleanups.errors)>0

    def dump(self, failed=False):
        file_path = '/tmp/%s.test' % settings.PROJECT_NAME
        dump_file_path = '/tmp/%s.json' % settings.PROJECT_NAME

        data = dict(login_count=self.login_count, username=self.current_username, password=self.current_password)
        open(file_path, 'w').write(json.dumps(data))
        output = open(dump_file_path,'w')
        call_command('dumpdata', *[x.split('.')[-1] for x in settings.INSTALLED_APPS], format='json', indent=3, stdout=output)
        output.close()

    def restore(self):
        dump_file_path = '/tmp/%s.json' % settings.PROJECT_NAME
        call_command('loaddata', dump_file_path)
        self.restored = True

    def pause(self):
        import pdb
        pdb.set_trace()
