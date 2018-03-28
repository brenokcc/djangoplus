# -*- coding: utf-8 -*-
from cryptography.fernet import Fernet
cipher = Fernet(Fernet.generate_key())


def encrypt(text):
    return cipher.encrypt(text.encode('utf-8')).decode('utf-8')


def decrypt(text):
    return cipher.decrypt(text.encode('utf-8')).decode('utf-8')
