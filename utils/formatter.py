# -*- coding: utf-8 -*-

import re
import datetime
import unicodedata
from decimal import Decimal
from django.conf import settings
from collections import Iterable
from django.utils.safestring import mark_safe


def normalyze(nome):
    nome = str(nome)

    if nome.isupper():
        return nome

    ponto = '\.'
    ponto_espaco = '. '
    espaco = ' '
    regex_multiplos_espacos = '\s+'
    regex_numero_romano = '^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$'

    nome = re.sub(ponto, ponto_espaco, nome)  # colocando espaço após nomes abreviados
    nome = re.sub(regex_multiplos_espacos, espaco, nome)  # retirando espaços múltiplos
    nome = nome.title()  # alterando os nomes para CamelCase
    partes_nome = nome.split(espaco)  # separando as palavras numa lista
    excecoes = [
        'de', 'di', 'do', 'da', 'dos', 'das', 'dello', 'della', 'dalla',
        'dal', 'del', 'e', 'em', 'na', 'no', 'nas', 'nos', 'van', 'von', 'y', 'para', 'pela', 'pelo', 'por',
    ]

    resultado = []

    for palavra in partes_nome:
        if palavra.lower() in excecoes:
            resultado.append(palavra.lower())
        elif re.match(regex_numero_romano, palavra.upper()):
            resultado.append(palavra.upper())
        else:
            resultado.append(palavra)

    nome = espaco.join(resultado)
    return nome


def format_bool(value):
    return value and '<span class="label label-success">Sim</span>' or '<span class="label label-danger">Não</span>'


def format_value(value, html=True):
    from djangoplus.db.models.fields import ImageFieldFile
    from django.db.models.fields.files import FieldFile, ImageFieldFile as DjangoImageFieldFile
    if value in (None, '', ()):
        return '-'
    elif isinstance(value, str) or type(value).__name__ == '__proxy__':  # lazy i18n
        return value
    elif isinstance(value, bool):
        return value and 'Sim' or 'Não'
    elif isinstance(value, datetime.datetime):
        return value.strftime('%d/%m/%Y %H:%M')
    elif isinstance(value, datetime.date):
        return value.strftime('%d/%m/%Y')
    elif isinstance(value, tuple):
        return '{} {}'.format(value[0], value[1])
    elif isinstance(value, Decimal):
        if hasattr(value, 'decimal3'):
            return format_decimal3(value)
        elif hasattr(value, 'decimal1'):
            return format_decimal1(value)
        else:
            return format_decimal(value)
    elif isinstance(value, ImageFieldFile) or isinstance(value, DjangoImageFieldFile):
        if html:
            return mark_safe(
                '<img width="75" class="materialboxed" src="{}"/>'.format(value.url)
            )
        else:
            return value.url
    elif isinstance(value, FieldFile):
        file_name = value.name.split('/')[-1]
        if value.url.lower().endswith('.pdf'):
            if html:
                return mark_safe('''
                    <a class="ajax pdf" href="{}">{}</a>{}
                    <a href="{}"><i class="mdi-file-file-download"></i></a>
                '''.format(value.url, file_name, '&nbsp;'*6, value.url))
            else:
                return value.url
        else:
            if html:
                return mark_safe('<a target="_blank" href="{}">{}</a>'.format(value.url, file_name))
            else:
                return value.url
    elif isinstance(value, Iterable):
        if html:
            ul = ['<ul style="display: inline-block; padding-left:20px">']
            for obj in value:
                ul.append('<li style="list-style-type:square">{}</li>'.format(obj))
            ul.append('</ul>')
            return mark_safe(''.join(ul))
        else:
            items = []
            for obj in value:
                items.append(str(obj))
            return ', '.join(items)
    else:
        return str(value)


def format_decimal(value, decimal_places=2):
    str_format = '{{:.{}f}}'.format(decimal_places)
    if value is not None:
        value = str_format.format(Decimal(value))
        if settings.LANGUAGE_CODE == 'pt-br':
            value = value.replace('.', ',')
    return value


def format_decimal3(value):
    if value is None:
        return ''
    return format_decimal(value, 3)


def format_decimal1(value):
    if value is None:
        return ''
    return format_decimal(value, 1)


def to_ascii(txt, codif='utf-8'):
    if not isinstance(txt, str):
        txt = str(txt)
    if isinstance(txt, str):
        txt = txt.encode('utf-8')
    return unicodedata.normalize(
        'NFKD', txt.decode(codif)
    ).encode('ASCII', 'ignore').decode('utf-8')
