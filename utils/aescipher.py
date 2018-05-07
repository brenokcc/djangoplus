# -*- coding: utf-8 -*-
import base64
from django.conf import settings
from cryptography.fernet import Fernet

cipher = Fernet(base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[0:32]).decode())


def encrypt(text, b16=False):
    s = cipher.encrypt(str(text).encode('utf-8'))
    if b16:
        s = base64.b16encode(s)
    return s.decode('utf-8')


def decrypt(text, b16=False):
    if b16:
        text = base64.b16decode(text.encode('utf-8'))
    else:
        text = text.encode('utf-8')
    s = cipher.decrypt(text)
    return s.decode('utf-8')
