# -*- coding: utf-8 -*-

from django.utils import termcolors


def bold(text):
    return termcolors.make_style(fg='black', opts=('bold',))(text)


def info(text):
    return termcolors.make_style(fg='cyan')(text)


def error(text):
    return termcolors.make_style(fg='red', opts=('bold',))(text)
