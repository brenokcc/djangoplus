# -*- coding: utf-8 -*-
import io
import json
import sys
import shutil
from decimal import Decimal
from django.db import models
from django.core.files.base import ContentFile
from djangoplus.utils.formatter import to_ascii
from djangoplus.ui.components.forms import fields as form_fields
from django.db.models.fields.files import ImageFieldFile
from djangoplus.utils.metadata import get_metadata, getattr2


# Superclass #


class FieldPlus(models.Field):
    def __init__(self, *args, **kwargs):
        self.search = kwargs.pop('search', False)
        self.filter = kwargs.pop('filter', False)
        self.exclude = kwargs.pop('exclude', False)
        self.example = kwargs.pop('example', False)
        self.display = kwargs.pop('display', True)
        self.formatter = kwargs.pop('formatter', None)
        if self.exclude and kwargs.get('default', None) is None:
            kwargs.update(null=True)
        super(FieldPlus, self).__init__(*args, **kwargs)


# Base Fields #

class AutoField(models.AutoField):
    pass


class CharField(models.CharField, FieldPlus):
    def __init__(self, *args, **kwargs):
        max_length = kwargs.pop('max_length', 255)
        choices = kwargs.get('choices')
        if choices and type(choices[0]) not in (list, tuple):
            kwargs.update(choices=[[choice, choice] for choice in choices])
        super(CharField, self).__init__(*args, max_length=max_length, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CharField)
        kwargs.setdefault('choices_form_class', form_fields.TypedChoiceField)
        field = super(CharField, self).formfield(**kwargs)
        return field


class EmailField(CharField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.EmailField)
        return super(EmailField, self).formfield(**kwargs)


class UrlField(CharField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.UrlField)
        return super(UrlField, self).formfield(**kwargs)


class AddressField(CharField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.AddressField)
        return super(AddressField, self).formfield(**kwargs)


class TextField(models.TextField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.TextField)
        return super(TextField, self).formfield(**kwargs)


class JsonField(TextField, FieldPlus):

    def get_prep_value(self, value):
        if not value:
            return '{}'
        if isinstance(value, dict):
            return json.dumps(value)
        else:
            return value

    def to_python(self, value):
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        return json.loads(value)

    def from_db_value(self, value, *args, **kwargs):
        return self.to_python(value)


class FormattedTextField(models.TextField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.FormattedTextField)
        return super(FormattedTextField, self).formfield(**kwargs)


class IntegerField(models.IntegerField, FieldPlus):
    def __init__(self, *args, **kwargs):
        self.min_value = kwargs.pop('min_value', None)
        self.max_value = kwargs.pop('max_value', None)
        self.suffix = kwargs.pop('suffix', None)
        super(IntegerField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.IntegerField)
        kwargs.setdefault('choices_form_class', form_fields.TypedChoiceField)
        kwargs.setdefault('min_value', self.min_value)
        kwargs.setdefault('max_value', self.max_value)
        return super(IntegerField, self).formfield(**kwargs)


class DecimalField(models.DecimalField, FieldPlus):
    def __init__(self, *args, **kwargs):
        decimal_places = kwargs.pop('decimal_places', 2)
        max_digits = kwargs.pop('max_digits', 9)
        self.suffix = kwargs.pop('suffix', None)
        super(DecimalField, self).__init__(*args, decimal_places=decimal_places, max_digits=max_digits, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.DecimalField)
        return super(DecimalField, self).formfield(**kwargs)


class MoneyField(DecimalField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.MoneyField)
        return super(MoneyField, self).formfield(**kwargs)


class DateField(models.DateField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.DateField)
        return super(DateField, self).formfield(**kwargs)


class CurrentDateField(DateField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CurrentDateField)
        return super(CurrentDateField, self).formfield(**kwargs)


class PastDateField(DateField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.PastDateField)
        return super(PastDateField, self).formfield(**kwargs)


class FutureDateField(DateField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.FutureDateField)
        return super(FutureDateField, self).formfield(**kwargs)


class DateTimeField(models.DateTimeField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.DateTimeField)
        return super(DateTimeField, self).formfield(**kwargs)


class CurrentDateTimeField(DateTimeField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CurrentDateTimeField)
        return super(CurrentDateTimeField, self).formfield(**kwargs)


class PastDateTimeField(DateTimeField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.PastDateTimeField)
        return super(PastDateTimeField, self).formfield(**kwargs)


class FutureDateTimeField(DateTimeField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.FutureDateTimeField)
        return super(FutureDateTimeField, self).formfield(**kwargs)


class BooleanField(models.BooleanField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.BooleanField)
        return super(BooleanField, self).formfield(**kwargs)


class NullBooleanField(models.NullBooleanField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.NullBooleanField)
        return super(NullBooleanField, self).formfield(**kwargs)


# One-to-One Relation Field #

class OneToOneField(models.OneToOneField, FieldPlus):

    def __init__(self, *args, **kwargs):
        if kwargs.get('null'):
            kwargs.update(on_delete=models.SET_NULL)
        else:
            kwargs.update(on_delete=models.CASCADE)
        super(OneToOneField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.OneToOneField)
        return super(OneToOneField, self).formfield(**kwargs)


# Model Choice Field #

class ForeignKey(models.ForeignKey, FieldPlus):
    def __init__(self, *args, **kwargs):
        self.lazy = kwargs.pop('lazy', False)
        self.pick = kwargs.pop('pick', False)
        self.ignore_lookup = kwargs.pop('ignore_lookup', False)
        self.form_filter = kwargs.pop('form_filter', None)
        self.composition = kwargs.pop('composition', False)
        self.tree = kwargs.pop('tree', False)
        if self.tree:
            kwargs.update(null=True)
            kwargs.update(blank=True)
        kwargs.update(on_delete=models.CASCADE)
        if self.form_filter and type(self.form_filter) not in (tuple, list):
            self.form_filter = self.form_filter.split('__')[-1], self.form_filter
        self.queryset_filter = kwargs.pop('queryset_filter', None)
        super(ForeignKey, self).__init__(*args, **kwargs)
        if 'test' in sys.argv:
            self.form_filter = None

    def formfield(self, **kwargs):
        kwargs.setdefault('lazy', self.lazy)
        kwargs.setdefault('pick', self.pick)
        kwargs.setdefault('ignore_lookup', self.ignore_lookup)
        kwargs.setdefault('form_filters', self.form_filter and [self.form_filter] or [])
        kwargs.setdefault('form_class', form_fields.ModelChoiceField)

        field = super(ForeignKey, self).formfield(**kwargs)
        if self.queryset_filter:
            field.queryset = field.queryset.filter(**self.queryset_filter)
        return field


ModelChoiceField = ForeignKey


# Multiple Model Choice Fields #

class ManyToManyField(models.ManyToManyField, FieldPlus):
    def __init__(self, *args, **kwargs):
        self.lazy = kwargs.pop('lazy', False)
        self.pick = kwargs.pop('pick', False)
        self.ignore_lookup = kwargs.pop('ignore_lookup', False)
        self.form_filter = kwargs.pop('form_filter', None)
        self.add_label = kwargs.pop('add_label', None)
        self.can_add = kwargs.pop('can_add', None)
        if self.form_filter and type(self.form_filter) not in (tuple, list):
            self.form_filter = self.form_filter.split('__')[-1], self.form_filter
        self.queryset_filter = kwargs.pop('queryset_filter', None)
        super(ManyToManyField, self).__init__(*args, **kwargs)
        if 'test' in sys.argv:
            self.form_filter = None

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.MultipleModelChoiceField)
        kwargs.setdefault('pick', self.pick)
        kwargs.setdefault('ignore_lookup', self.ignore_lookup)
        kwargs.setdefault('form_filters', self.form_filter and [self.form_filter] or [])
        kwargs.setdefault('lazy', self.lazy)
        field = super(ManyToManyField, self).formfield(**kwargs)
        if self.queryset_filter:
            field.queryset = field.queryset.filter(**self.queryset_filter)
        return field

MultipleModelChoiceField = ManyToManyField


class OneToManyField(ManyToManyField):

    def __init__(self, *args, **kwargs):
        self.one_to_many_count = kwargs.pop('count', None)
        self.one_to_many_max = kwargs.pop('max', 3)
        super(OneToManyField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.OneToManyField)
        form_field = super(OneToManyField, self).formfield(**kwargs)
        form_field.one_to_many_count = self.one_to_many_count
        form_field.one_to_many_max = self.one_to_many_max
        return form_field

# File Fields #

class FileField(models.FileField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.FileField)
        return super(FileField, self).formfield(**kwargs)


class ImageFieldFile(ImageFieldFile):
    def __init__(self, *args, **kwargs):
        super(ImageFieldFile, self).__init__(*args, **kwargs)

        if self.field.sizes:
            def get_size(self, size):
                if not self:
                    return ''
                else:
                    split = self.url.rsplit('.', 1)
                    thumb_url = '{}.{}x{}.{}'.format(split[0], w, h, split[1])
                    return thumb_url

            first = True
            for size in self.field.sizes:
                (w, h) = size
                if first:
                    first = False
                    if self:
                        setattr(self, 'url_{}x{}'.format(w, h), self.url)
                        setattr(self, 'small', self.url)
                    else:
                        setattr(self, 'url_{}x{}'.format(w, h), '')
                        setattr(self, 'small', '')
                else:
                    setattr(self, 'url_{}x{}'.format(w, h), get_size(self, size))
                    setattr(self, 'large', get_size(self, size))

    def generate_thumb(self, img, thumb_size, file_format):
        try:
            from PIL import Image
        except ImportError:
            return img
        img.seek(0)  # see http://code.djangoproject.com/ticket/8222 for details
        image = Image.open(img)

        # Convert to RGB if necessary
        if image.mode not in ('L', 'RGB', 'RGBA'):
            image = image.convert('RGB')

        # get size
        thumb_w, thumb_h = thumb_size
        # If you want to generate a square thumbnail
        if thumb_w == thumb_h and False:
            # quad
            xsize, ysize = image.size
            # get minimum size
            minsize = min(xsize, ysize)
            # largest square possible in the image
            xnewsize = (xsize - minsize) / 2
            ynewsize = (ysize - minsize) / 2
            # crop it
            image2 = image.crop((xnewsize, ynewsize, xsize - xnewsize, ysize - ynewsize))
            # load is necessary after crop                
            image2.load()
            # thumbnail of the cropped image (with ANTIALIAS to make it look better)
            image2.thumbnail(thumb_size, Image.ANTIALIAS)
        else:
            # not quad
            image2 = image
            image2.thumbnail(thumb_size, Image.ANTIALIAS)

        tmp = io.BytesIO()
        # PNG and GIF are the same, JPG is JPEG
        if file_format.upper() == 'JPG':
            file_format = 'JPEG'

        image2.save(tmp, file_format)
        return ContentFile(tmp.getvalue())

    def save(self, name, content, save=True):
        super(ImageFieldFile, self).save(name, content, save)

        first = True
        if self.field.sizes:
            for size in self.field.sizes:
                (w, h) = size
                split = self.name.rsplit('.', 1)
                thumb_name = '{}.{}x{}.{}'.format(split[0], w, h, split[1])

                # you can use another thumbnailing function if you like
                thumb_content = self.generate_thumb(content, size, split[1])

                thumb_name_ = self.storage.save(thumb_name, thumb_content)

                if not thumb_name == thumb_name_:
                    raise ValueError('There is already a file named {}'.format(thumb_name))

                if first:
                    first = False
                    shutil.move(self.path.replace(self.name, thumb_name), self.path)

    def delete(self, save=True):
        name = self.name
        super(ImageFieldFile, self).delete(save)
        if self.field.sizes:
            for size in self.field.sizes:
                (w, h) = size
                split = name.rsplit('.', 1)
                thumb_name = '{}.{}x{}.{}'.format(split[0], w, h, split[1])
                try:
                    self.storage.delete(thumb_name)
                except:
                    pass


class ImageField(models.ImageField, FieldPlus):
    attr_class = ImageFieldFile

    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, sizes=None, **kwargs):
        self.verbose_name = verbose_name
        self.name = name
        self.width_field = width_field
        self.height_field = height_field
        self.sizes = sizes
        default = '/static/images/blank.png'
        if 'default' in kwargs:
            default = kwargs.pop('default')
        super(ImageField, self).__init__(default=default, verbose_name=self.verbose_name, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.ImageField)
        return super(ImageField, self).formfield(**kwargs)


class PhotoField(models.ImageField, FieldPlus):
    attr_class = ImageFieldFile

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.PhotoField)
        return super(PhotoField, self).formfield(**kwargs)


# Regional Fields #

class CpfField(CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CpfField)
        return super(CpfField, self).formfield(**kwargs)


class CnpjField(CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CnpjField)
        return super(CnpjField, self).formfield(**kwargs)


class CpfCnpjField(CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CpfCnpjField)
        return super(CpfCnpjField, self).formfield(**kwargs)


class CepField(CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CepField)
        return super(CepField, self).formfield(**kwargs)


class CarPlateField(CharField, FieldPlus):
    def __init__(self, **kwargs):
        super(CarPlateField, self).__init__(**kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CarPlateField)
        return super(CarPlateField, self).formfield(**kwargs)


class PhoneField(CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.PhoneField)
        return super(PhoneField, self).formfield(**kwargs)


# Utilitary Fields #

class SearchField(TextField):
    def pre_save(self, model_instance, add):
        search_text = []
        for attr_name in get_metadata(model_instance, 'search_fields'):
            tokens = attr_name.split('__')
            if len(tokens) == 1:
                if attr_name != 'ascii':
                    val = getattr2(model_instance, attr_name)
                    if val:
                        search_text.append(str(to_ascii(val).upper().strip()))
        return ' '.join(search_text)


class HtmlTextField(models.TextField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.TextField)
        return super(HtmlTextField, self).formfield(**kwargs)

    def to_python(self, value):
        return None


class PasswordField(models.CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.PasswordField)
        return super(PasswordField, self).formfield(**kwargs)


class Decimal3(Decimal):
    def __new__(cls, value="0", context=None):
        cls.decimal3 = True
        return Decimal.__new__(cls, value=value or "0", context=context)


class DecimalField3(models.DecimalField, FieldPlus):
    def __init__(self, *args, **kwargs):
        decimal_places = kwargs.pop('decimal_places', 3)
        max_digits = kwargs.pop('max_digits', 9)
        super(DecimalField3, self).__init__(*args, decimal_places=decimal_places, max_digits=max_digits, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.DecimalField3)
        return super(DecimalField3, self).formfield(**kwargs)

    def from_db_value(self, value, expression, connection, context):
        value = Decimal3(value)
        return value


class CreditCardField(CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CreditCardField)
        return super(CreditCardField, self).formfield(**kwargs)


class OneDigitValidationField(CharField, FieldPlus):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.OneDigitValidationField)
        return super(OneDigitValidationField, self).formfield(**kwargs)


class CurrentUserField(models.ForeignKey, FieldPlus):
    def __init__(self, *args, **kwargs):
        kwargs['to'] = 'admin.User'
        kwargs['null'] = True
        kwargs['blank'] = True
        super(CurrentUserField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.CurrentUserField)
        return super(CurrentUserField, self).formfield(**kwargs)


class PositiveIntegerField(models.PositiveIntegerField, FieldPlus):
    def __init__(self, *args, **kwargs):
        self.min_value = kwargs.pop('min_value', 0)
        self.max_value = kwargs.pop('max_value', None)
        self.suffix = kwargs.pop('suffix', None)
        super(PositiveIntegerField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', form_fields.IntegerField)
        kwargs.setdefault('min_value', self.min_value)
        kwargs.setdefault('max_value', self.max_value)
        return super(PositiveIntegerField, self).formfield(**kwargs)


class TreeIndexField(CharField):
    def __init__(self, *args, **kwargs):
        self.ref = kwargs.pop('ref', None)
        self.sep = kwargs.pop('sep', '.')
        if not self.ref:
            kwargs.update(display=None)
        kwargs.update(blank=True, exclude=True, null=True)
        super(TreeIndexField, self).__init__(*args, **kwargs)
