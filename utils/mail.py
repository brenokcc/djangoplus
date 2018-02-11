# -*- coding: utf-8 -*-
from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives


def send_mail(subject, dictionary, template_name, to, reply_to=None):
    reply_to = reply_to and [reply_to] or None
    from_email = u'Não-Responder <%s>' % settings.SERVER_EMAIL
    template_name = 'html' in template_name and template_name or '%s.html' % template_name
    html = loader.render_to_string(template_name, dictionary)
    email = EmailMultiAlternatives(subject, u'Mensagem em anexo.', from_email, [to], reply_to=reply_to)
    email.attach_alternative(html, "text/html")
    return email.send()

# from djangoplus.utils.mail import send_mail;send_mail('oi', dict(), 'email_notification', 'brenokcc@yahoo.com.br')

