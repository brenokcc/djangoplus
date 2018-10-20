# -*- coding: utf-8 -*-

import uuid
import re
import base64
from datetime import datetime, date
from django import forms
from decimal import Decimal
from django.apps import apps
from django.core import validators
from djangoplus.ui.components.forms import widgets
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile


# Base Fields #


class CharField(forms.fields.CharField):
    widget = widgets.TextInput


class EmailField(CharField):
    widget = widgets.EmailInput


class UrlField(CharField):
    widget = widgets.UrlInput


class AddressField(CharField):
    widget = widgets.AddressInput


class TypedChoiceField(forms.fields.TypedChoiceField):
    widget = widgets.SelectWidget


class TextField(forms.fields.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.pop('widget', widgets.Textarea)
        super(TextField, self).__init__(*args, widget=widgets.Textarea, **kwargs)


class FormattedTextField(forms.fields.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.pop('widget', widgets.Textarea)
        super(FormattedTextField, self).__init__(*args, widget=widgets.FormattedTextarea, **kwargs)


class IntegerField(forms.fields.IntegerField):
    widget = widgets.NumberInput

    def __init__(self, *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)
        self.widget.min_value = self.min_value
        self.widget.max_value = self.max_value


class DecimalField(forms.fields.DecimalField):
    widget = widgets.DecimalInput

    def to_python(self, value):
        if not value in validators.EMPTY_VALUES:
            return Decimal(value.replace('.', '').replace(',', '.'))
        return None


class MoneyField(DecimalField):
    widget = widgets.MoneyInput


class DateField(forms.fields.DateField):
    widget = widgets.DateWidget


class CurrentDateTimeField(DateField):
    widget = widgets.HiddenInput

    def clean(self, value):
        return date.today()


class PastDateField(forms.fields.DateField):
    widget = widgets.DateWidget

    def clean(self, value):
        value = super(PastDateField, self).clean(value)
        if value and value > date.today():
            raise ValidationError('Informe uma data atual ou passada')
        return value


class FutureDateField(forms.fields.DateField):
    widget = widgets.DateWidget

    def clean(self, value):
        value = super(FutureDateField, self).clean(value)
        if value and value < date.today():
            raise ValidationError('Informe uma data atual ou futura')
        return value


class DateTimeField(forms.fields.DateTimeField):
    widget = widgets.DateTimeWidget


class CurrentDateTimeField(DateTimeField):
    widget = widgets.HiddenInput

    def clean(self, value):
        return datetime.now()


class PastDateTimeField(forms.fields.DateTimeField):
    widget = widgets.DateTimeWidget

    def clean(self, value):
        value = super(PastDateTimeField, self).clean(value)
        if value and value > datetime.now():
            raise ValidationError('Informe uma data/hora atual ou passada')
        return value


class FutureDateTimeField(forms.fields.DateTimeField):
    widget = widgets.DateTimeWidget

    def clean(self, value):
        value = super(FutureDateTimeField, self).clean(value)
        if value and value < datetime.now():
            raise ValidationError('Informe uma data/hora atual ou futura')
        return value


class BooleanField(forms.fields.BooleanField):
    widget = widgets.CheckboxInput


class NullBooleanField(forms.fields.NullBooleanField):
    widget = widgets.NullBooleanSelect


# Model Choice Field #

class ChoiceField(forms.fields.ChoiceField):
    widget = widgets.SelectWidget


class ModelChoiceField(forms.models.ModelChoiceField):
    widget = widgets.SelectWidget

    def __init__(self, *args, **kwargs):
        minimum_input_length = kwargs.pop('minimum_input_length', 3)
        self.lazy = kwargs.pop('lazy', False)
        self.pick = kwargs.pop('pick', False)
        self.ignore_lookup = kwargs.pop('ignore_lookup', False)
        self.form_filters = kwargs.pop('form_filters', [])
        super(ModelChoiceField, self).__init__(*args, **kwargs)
        if self.pick:
            self.widget = widgets.PickWidget()
        else:
            self.widget.lazy = self.lazy
            self.widget.form_filters = self.form_filters
            self.widget.minimum_input_length = minimum_input_length


class OneToOneField(ModelChoiceField):
    pass


# Multiple Model Choice Fields #

class MultipleModelChoiceField(forms.models.ModelMultipleChoiceField):
    widget = widgets.SelectMultipleWidget

    def __init__(self, *args, **kwargs):
        minimum_input_length = kwargs.pop('minimum_input_length', 3)
        self.lazy = kwargs.pop('lazy', False)
        self.pick = kwargs.pop('pick', False)
        self.ignore_lookup = kwargs.pop('ignore_lookup', False)
        self.form_filters = kwargs.pop('form_filters', [])
        super(MultipleModelChoiceField, self).__init__(*args, **kwargs)
        if self.pick:
            if type(self.pick) is not bool:
                grouper = self.pick
            else:
                grouper = None
            self.widget = widgets.PickWidget(multiple=True, grouper=grouper)
        else:
            self.widget.lazy = self.lazy
            self.widget.form_filters = self.form_filters
            self.widget.minimum_input_length = minimum_input_length


class OneToManyField(MultipleModelChoiceField):
    pass


# File Fields #


class FileField(forms.fields.FileField):
    widget = widgets.FileInput

    def clean(self, data, initial=None):
        cleaned_data = super(FileField, self).clean(data, initial=initial)
        if cleaned_data and cleaned_data.name != initial:
            extension = cleaned_data.name.split('.')[-1]
            cleaned_data.name = '{}.{}'.format(str(uuid.uuid1()), extension)
        return cleaned_data


class ImageField(forms.fields.ImageField):
    widget = widgets.ImageInput

    def clean(self, data, initial=None):
        cleaned_data = super(ImageField, self).clean(data, initial=initial)
        if cleaned_data and hasattr(cleaned_data, 'name') and cleaned_data.name != initial:
            extension = cleaned_data.name.split('.')[-1]
            cleaned_data.name = '{}.{}'.format(str(uuid.uuid1()), extension)
        return cleaned_data


class PhotoField(ImageField):
    widget = widgets.PhotoWidget

    def to_python(self, data):
        if data:
            data = ContentFile(base64.b64decode(data.split(',')[1]))
            data.name = 'Image.png'
        return super(PhotoField, self).to_python(data)


# Regional Fields #

class CpfField(CharField):
    widget = widgets.CpfWidget

    default_error_messages = {
        'invalid': 'Número de CPF inválido.',
        'max_digits': 'O CPF deve conter 11 dígitos',
        'digits_only': 'O CPF deve conter apenas dígitos',
    }

    def __init__(self, *args, **kwargs):
        super(CpfField, self).__init__(min_length=11, *args, **kwargs)

    def dv(self, v):
        if v >= 2:
            return 11 - v
        return 0

    def clean(self, value):
        value = super(CpfField, self).clean(value)
        if value in validators.EMPTY_VALUES:
            return ''
        orig_value = value[:]
        if not value.isdigit():
            value = re.sub("[-\.]", "", value)
        try:
            int(value)
        except ValueError:
            raise ValidationError(self.error_messages['digits_only'])
        if len(value) != 11:
            raise ValidationError(self.error_messages['max_digits'])
        orig_dv = value[-2:]

        new_1dv = sum([i * int(value[idx]) for idx, i in enumerate(range(10, 1, -1))])
        new_1dv = self.dv(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum([i * int(value[idx]) for idx, i in enumerate(range(11, 1, -1))])
        new_2dv = self.dv(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise ValidationError(self.error_messages['invalid'])

        return orig_value


class CnpjField(CharField):
    widget = widgets.CnpjWidget
    default_error_messages = {
        'invalid': 'Número de CNPJ inválido.',
        'max_digits': 'O CNPJ deve conter 18 dígitos',
        'digits_only': 'O CNPJ deve conter apenas dígitos',
    }

    def dv(self, v):
        if v >= 2:
            return 11 - v
        return 0

    def clean(self, value):
        value = super(CnpjField, self).clean(value)
        if value in validators.EMPTY_VALUES:
            return ''
        orig_value = value[:]
        if not value.isdigit():
            value = re.sub("[-/\.]", "", value)
        try:
            int(value)
        except ValueError:
            raise ValidationError(self.error_messages['digits_only'])
        if len(value) != 14:
            raise ValidationError(self.error_messages['max_digits'])
        orig_dv = value[-2:]

        new_1dv = sum([i * int(value[idx]) for idx, i in enumerate(list(range(5, 1, -1)) + list(range(9, 1, -1)))])
        new_1dv = self.dv(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum([i * int(value[idx]) for idx, i in enumerate(list(range(6, 1, -1)) + list(range(9, 1, -1)))])
        new_2dv = self.dv(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise ValidationError(self.error_messages['invalid'])

        return orig_value


class CpfCnpjField(CharField):
    widget = widgets.CpfCnpjWidget


class CepField(forms.fields.RegexField):
    widget = widgets.CepWidget

    default_error_messages = {
        'invalid': 'O CEP deve estar no formato XX.XXX-XXX.',
    }

    def __init__(self, *args, **kwargs):
        super(CepField, self).__init__(r'^\d{2}\.\d{3}-\d{3}$',
                                       *args, **kwargs)


class CarPlateField(CharField):
    widget = widgets.CarPlateWidget

    def __init__(self, *args, **kwargs):
        super(CarPlateField, self).__init__(min_length=8, *args, **kwargs)


class PhoneField(CharField):
    PHONE_DIGITS_RE = re.compile(r'^(\d{2})[-\.]?(\d{4,5})[-\.]?(\d{4})$')

    widget = widgets.PhoneWidget

    default_error_messages = {
        'invalid': 'O telefone deve estar no formato (XX) XXXX-XXXX.',
    }

    def clean(self, value):
        super(PhoneField, self).clean(value)
        if value in validators.EMPTY_VALUES:
            return ''
        value = re.sub('(\(|\)|\s+)', '', str(value))
        m = PhoneField.PHONE_DIGITS_RE.search(value)
        if m:
            return '({}) {}-{}'.format(m.group(1), m.group(2), m.group(3))
        raise ValidationError(self.error_messages['invalid'])


# Utilitary Fields #

class PasswordField(CharField):
    widget = widgets.PasswordInput


class DecimalField3(CharField):
    widget = widgets.DecimalInput3

    def __init__(self, *args, **kwargs):
        kwargs.pop('max_digits')
        kwargs.pop('decimal_places')
        super(DecimalField3, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value in validators.EMPTY_VALUES:
            return Decimal(value.replace('.', '').replace(',', '.'))
        return None


class CurrentUserField(ModelChoiceField):
    widget = widgets.HiddenInput

    def __init__(self, *args, **kwargs):
        User = apps.get_app_config('admin').models['user']
        kwargs['queryset'] = User.objects.all()
        super(CurrentUserField, self).__init__(*args, **kwargs)


class DateRangeField(forms.fields.MultiValueField):
    widget = widgets.DateRangeWidget

    def __init__(self, fields=(DateField(required=False), DateField(required=False)), sum_end_date=False, *args,
                 **kwargs):
        super(forms.fields.MultiValueField, self).__init__(*args, **kwargs)

    def clean(self, value):
        """
        Returns [(data), (data+1 dia)] in order to make  .filter(date__gt=start_date, date__lt=end_date) easier
        """
        datefield = DateField(required=False)
        try:
            start_date, end_date = [datefield.clean(i) for i in value]
        except:
            raise ValidationError('A faixa de datas está inválida.')
        if start_date > end_date:
            raise ValidationError('A data final é menor que a inicial.')
        return [start_date, end_date]


class DateFilterField(DateRangeField):
    widget = widgets.DateFilterWidget

    def __init__(self, *args, **kwargs):
        super(DateFilterField, self).__init__(*args, **kwargs)
        self.widget.label = self.label


class CreditCardField(CharField):
    widget = widgets.CreditCardWidget

    def __init__(self, *args, **kwargs):
        super(CreditCardField, self).__init__(min_length=19, *args, **kwargs)


class OneDigitValidationField(CharField):
    widget = widgets.OneDigitValidationInput