# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib
import binascii
from Crypto import Random
from django.conf import settings
from Crypto.Cipher import AES


class AESCipher(object):
    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return binascii.hexlify(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = binascii.unhexlify(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]

AESCIPHER = AESCipher(settings.SECRET_KEY)


def encrypt(text):
    return AESCIPHER.encrypt('{}'.format(text))


def decrypt(text):
    return AESCIPHER.decrypt(text)
