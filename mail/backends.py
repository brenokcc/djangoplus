# -*- coding: utf-8 -*-

from djangoplus.mail.utils import dump_emails
from django.core.mail.backends.base import BaseEmailBackend


class EmailDebugBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        return dump_emails(email_messages)
