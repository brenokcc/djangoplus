# -*- coding: utf-8 -*-
import os
import json
from django.conf import settings

DEBUG_EMAIL_FILE_PATH = os.path.join(settings.MEDIA_ROOT, 'mail.json')


def dump_emails(emails):
    messagens = []
    if not os.path.exists(settings.MEDIA_ROOT):
        os.mkdir(settings.MEDIA_ROOT)
    for message in emails:
        data = dict(
            from_email=message.from_email, to=', '.join(message.to), body=message.body,
            alternatives=message.alternatives
        )
        messagens.append(data)
    open(DEBUG_EMAIL_FILE_PATH, 'w').write(json.dumps(messagens))


def load_emails():
    messages = []
    if os.path.exists(DEBUG_EMAIL_FILE_PATH):
        messages = json.loads(open(DEBUG_EMAIL_FILE_PATH).read())
        os.unlink(DEBUG_EMAIL_FILE_PATH)
    return messages


def should_display():
    return os.path.exists(DEBUG_EMAIL_FILE_PATH)

