# -*- coding: utf-8 -*-
import base64
from django.conf import settings

try:
    from cryptography.fernet import Fernet
    cipher = Fernet(base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[0:32]).decode())
except ImportError:
    cipher = None


def encrypt(text, b16=False):
    if cipher:
        s = cipher.encrypt(str(text).encode('utf-8'))
    else:
        s = base64.b64encode(text.encode('utf-8'))
    if b16:
        s = base64.b16encode(s)
    return s.decode('utf-8')


def decrypt(text, b16=False):
    if b16:
        text = base64.b16decode(text.encode('utf-8'))
    else:
        text = text.encode('utf-8')
    if cipher:
        s = cipher.decrypt(text)
    else:
        s = base64.b64decode(text.decode('utf-8'))
    return s.decode('utf-8')
