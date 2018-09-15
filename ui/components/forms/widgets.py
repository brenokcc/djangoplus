# -*- coding: utf-8 -*-

from django.forms import widgets
from django.db.models.fields.files import FieldFile, ImageFieldFile
from djangoplus.ui.components.calendar.widgets import *
from djangoplus.ui.components.editor.widgets import *
from djangoplus.ui.components.select.widgets import *

# Base Widgets #


class TextInput(widgets.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs.update(**{'class':'form-control {}'.format(self.attrs.get('class', ''))})
        return super(TextInput, self).render(name, value, attrs, renderer)


class EmailInput(TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs['type'] = 'email'
        html = super(EmailInput, self).render(name, value, attrs)
        html = '''
        <div class="input-group">
            {}
            <span class="input-group-addon"><i class="fa fa-at"></i></span>
        </div>
        '''.format(html)
        return html


class UrlInput(TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs['type'] = 'url'
        html = super(UrlInput, self).render(name, value, attrs)
        html = '''
        <div class="input-group">
            {}
            <span class="input-group-addon"><i class="fa fa-link"></i></span>
        </div>
        '''.format(html)
        return html


class AddressInput(TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        html = super(AddressInput, self).render(name, value, attrs)
        html = '''
        <div class="input-group">
            {}
            <span class="input-group-addon"><i class="fa fa-envelope-o"></i></span>
        </div>
        '''.format(html)
        return html


class MaskWidget(widgets.TextInput):

    class Media:
        js = ('/static/js/jquery.mask.min-1.7.7.js',)

    def __init__(self, mask):
        super(MaskWidget, self).__init__()
        self.mask = mask

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        html = super(MaskWidget, self).render(name, value, attrs)
        script = '<script>$("#id_{}").mask("{}", {{clearIfNotMatch: true}});</script>'.format(name, self.mask)
        return mark_safe('{}\n\n{}'.format(html, script))


class HiddenInput(widgets.HiddenInput):
    pass


class ReadOnlyInput(TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        self.attrs['readonly'] = 'readonly'
        return super(ReadOnlyInput, self).render(name, value, attrs)


class DisplayInput(widgets.TextInput):
    def __init__(self, obj=None):
        super(DisplayInput, self).__init__()
        self.obj = obj

    def render(self, name, value, attrs=None, renderer=None):
        if value:
            if isinstance(value, FieldFile):
                value = value and str(value) or value.field.default
                url = '/static/' in value and value or '/media/{}'.format(value)
                height = value.split('.')[-1] in ('pdf', 'txt', 'xls', 'docx') and 500 or ''
                return mark_safe('<embed src="{}" width="100%" height="{}">'.format(url, height))
            return '<br>{}'.format(format_value(value))
        elif self.obj and hasattr(self.obj, 'pk'):
                return '<input class="form-control" type="text" value="{}" disabled /><input type="hidden" id="id_{}" name="{}" value="{}"/>'.format(self.obj, name, name, self.obj.pk)
        else:
            return ''

class Textarea(widgets.Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        if 'rows' not in attrs: # and 'rows' not in self.attrs
            attrs['rows'] = 3
        html = super(Textarea, self).render(name, value, attrs)
        return mark_safe(html)



class NumberInput(widgets.NumberInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        html = super(NumberInput, self).render(name, value, attrs)
        if self.max_value is not None and self.min_value is not None:
            html = html # TODO range widget

        return mark_safe(html)


class DecimalInput(widgets.TextInput):

    class Media:
        js = ('/static/js/jquery.mask.min-1.7.7.js',)

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        html = super(DecimalInput, self).render(name, value, attrs)
        html = html.replace('type="number"', 'type="text"')
        js = "<script>$('#id_{}').mask('###.###.##0,00', {{reverse: true}});</script>".format(name)
        return mark_safe('{}\n{}'.format(html, js))


class MoneyInput(DecimalInput):
    def render(self, name, value, attrs=None, renderer=None):
        html = super(MoneyInput, self).render(name, value, attrs)
        html = '''
        <div class="input-group">
            {}
            <span class="input-group-addon">R$</span>
        </div>
        '''.format(html)
        return mark_safe(html)


class CheckboxInput(widgets.CheckboxInput):
    def render(self, *args, **kwargs):
        html = super(CheckboxInput, self).render(*args, **kwargs)
        html = '{}<span class="custom-checkbox"></span>'.format(html)
        return mark_safe(html)


class RadioSelect(widgets.CheckboxInput):
    input_type = 'radio'

    def render(self, *args, **kwargs):
        html = super(RadioSelect, self).render(*args, **kwargs)
        html = '{}<span class="custom-radio"></span>'.format(html)
        return mark_safe(html)


class PickWidget(widgets.Select):
    def __init__(self, template_name='pick_widget.html', multiple=False, grouper=None, *args, **kwargs):
        super(PickWidget, self).__init__(*args, **kwargs)
        self.template_name = template_name
        self.allow_multiple_selected = multiple
        self.grouper = grouper

    def value_from_datadict(self, data, files, name):
        if self.allow_multiple_selected:
            getter = data.getlist
        else:
            getter = data.get
        return getter(name)

    def render(self, name, value, attrs=None, renderer=None, choices=()):
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs)
        values = value and (type(value) == int and [value] or [int(v) for v in value]) or []
        widget_cls = self.allow_multiple_selected and CheckboxInput or RadioSelect
        i = 0
        grouped_objects = []
        onclick = "var is=this.parentNode.parentNode.parentNode.parentNode.parentNode.getElementsByTagName('input');for(var i=0; i<is.length; i++) is[i].checked = {}".format(self.allow_multiple_selected and 'this.checked' or 'false')
        widget = widget_cls({'onclick': onclick}, check_test=lambda v: False).render(None, '')

        if self.choices:
            qs = hasattr(self.choices.queryset, 'all') and self.choices.queryset.all() or self.choices.queryset
            if self.grouper:
                groupers = qs.values_list(self.grouper, flat=True).order_by(self.grouper).distinct()
            else:
                groupers = [None]
            for grouper in groupers:
                objects = []
                if grouper:
                    grouped_qs = qs.filter(**{self.grouper : grouper})
                else:
                    grouped_qs = qs.all()
                for obj in grouped_qs:
                    option_value = obj.pk
                    if has_id:
                        final_attrs = dict(final_attrs, id='{}_{}'.format(attrs['id'], i))
                    final_attrs['class'] = self.allow_multiple_selected and 'custom-checkbox' or 'custom-radio'
                    obj.widget = widget_cls(final_attrs, check_test=lambda v: int(v) in values).render(name, str(option_value))
                    i += 1
                    objects.append(obj)
                grouped_objects.append((grouper, objects))

        return mark_safe(render_to_string(self.template_name, dict(grouped_objects=grouped_objects, widget=widget, name=name.replace('-', '_'))))


# File Widgets #


class FileInput(widgets.ClearableFileInput):
    template_name = 'clearable_file_input.html'
    pass


class ImageInput(widgets.ClearableFileInput):
    template_name = 'clearable_file_input.html'
    pass


class PhotoWidget(widgets.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs.update(style='display:none;')
        html = super(PhotoWidget, self).render(name, value, attrs)
        return render_to_string('widgets/photo_widget.html', dict(name=name, html=html))


# Regional Widgets #

class CpfWidget(MaskWidget):
    def __init__(self):
        super(CpfWidget, self).__init__('000.000.000-00')


class CnpjWidget(MaskWidget):
    def __init__(self):
        super(CnpjWidget, self).__init__('00.000.000/0000-00')


class CpfCnpjWidget(TextInput):

    class Media:
        js = ('/static/js/jquery.mask.min-1.7.7.js',)

    def render(self, name, value=None, attrs=None, renderer=None):
        html = super(CpfCnpjWidget, self).render(name, value, attrs)
        html = '''
                <div class="input-group">
                    {}
                </div>
                <script>
                    var CpfCnpjMaskBehavior = function (val) {{
                        return val.replace(/\D/g, '').length <= 11 ? '000.000.000-009' : '00.000.000/0000-00';
                    }},
                    spOptions = {{
                      clearIfNotMatch: true,
                      onKeyPress: function(val, e, field, options) {{
                          field.mask(CpfCnpjMaskBehavior.apply({}, arguments), options);
                        }}
                    }};

                    $('#id_{}').mask(CpfCnpjMaskBehavior, spOptions);
                </script>
                '''.format(html, value, name)
        return mark_safe(html)


class CepWidget(MaskWidget):
    def __init__(self):
        super(CepWidget, self).__init__('00.000-000')


class CarPlateWidget(MaskWidget):
    def __init__(self):
        super(CarPlateWidget, self).__init__('AAA-0000')


class PhoneWidget(TextInput):

    class Media:
        js = ('/static/js/jquery.mask.min-1.7.7.js',)

    def render(self, name, value, attrs=None, renderer=None):
        html = super(PhoneWidget, self).render(name, value, attrs)
        html = '''
        <div class="input-group">
            {}
            <span class="input-group-addon"><i class="fa fa-phone"></i></span>
        </div>
        <script>
            var SPMaskBehavior = function (val) {{
              return val.replace(/\D/g, '').length === 11 ? '(00) 00000-0000' : '(00) 0000-00009';
            }},
            spOptions = {{
              clearIfNotMatch: true,
              onKeyPress: function(val, e, field, options) {{
                  field.mask(SPMaskBehavior.apply({{}}, arguments), options);
                }}
            }};

            $('#id_{}').mask(SPMaskBehavior, spOptions);
        </script>
        '''.format(html, name)
        return mark_safe(html)

# Utilitary Fields #


class PasswordInput(widgets.PasswordInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        return super(PasswordInput, self).render(name, value, attrs)


class DecimalInput3(DecimalInput):

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        html = super(DecimalInput, self).render(name, value, attrs)
        html = html.replace('type="number"', 'type="text"')
        js = "<script>$('#id_{}').mask('#.##0,000', {{reverse: true, clearIfNotMatch: true}});</script>".format(name)
        return mark_safe('{}\n{}'.format(html, js))


class OneDigitValidationInput(TextInput):

    class Media:
        js = ('/static/js/jquery.mask.min-1.7.7.js',)

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        html = super(OneDigitValidationInput, self).render(name, value, attrs)
        html = html.replace('type="number"', 'type="text"')
        js = "<script>$('#id_{}').mask('#.##0-0', {{reverse: true, clearIfNotMatch: true}});</script>".format(name)
        return mark_safe('{}\n{}'.format(html, js))


class CreditCardWidget(MaskWidget):
    def __init__(self):
        super(CreditCardWidget, self).__init__('9999 9999 9999 9999')
