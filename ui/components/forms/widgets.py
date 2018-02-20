# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.forms import widgets
from django.utils.encoding import force_unicode
from djangoplus.ui.components.calendar.widgets import *
from djangoplus.ui.components.editor.widgets import *
from djangoplus.ui.components.select.widgets import *

# Base Widgets #


class TextInput(widgets.TextInput):
    def render(self, name, value, attrs={}):
        attrs.update(**{'class':'form-control {}'.format(self.attrs.get('class', ''))})
        return super(TextInput, self).render(name, value, attrs)


class EmailInput(TextInput):
    def render(self, name, value, attrs={}):
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
    def render(self, name, value, attrs={}):
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
    def render(self, name, value, attrs={}):
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

    def render(self, name, value, attrs={}):
        attrs['class'] = 'form-control'
        html = super(MaskWidget, self).render(name, value, attrs)
        script = '<script>$("#id_{}").mask("{}", {{clearIfNotMatch: true}});</script>'.format(name, self.mask)
        return mark_safe('{}\n\n{}'.format(html, script))


class HiddenInput(widgets.HiddenInput):
    pass


class ReadOnlyInput(TextInput):
    def render(self, name, value, attrs=None):
        self.attrs['readonly'] = 'readonly'
        return super(ReadOnlyInput, self).render(name, value, attrs)


class DisplayInput(widgets.TextInput):
    def __init__(self, obj):
        super(DisplayInput, self).__init__()
        self.obj = obj

    def render(self, name, value, attrs=None):
        return '<input class="form-control" type="text" value="{}" disabled /><input type="hidden" id="id_{}" name="{}" value="{}"/>'.format(self.obj, name, name, self.obj.pk)


class Textarea(widgets.Textarea):
    def render(self, name, value, attrs={}):
        attrs['class'] = 'form-control'
        if 'rows' not in attrs: # and 'rows' not in self.attrs
            attrs['rows'] = 3
        html = super(Textarea, self).render(name, value, attrs)
        return mark_safe(html)



class NumberInput(widgets.NumberInput):
    def render(self, name, value, attrs={}):
        attrs['class'] = 'form-control'
        html = super(NumberInput, self).render(name, value, attrs)
        if self.max_value is not None and self.min_value is not None:
            html = html # TODO range widget

        return mark_safe(html)


class DecimalInput(widgets.TextInput):

    class Media:
        js = ('/static/js/jquery.mask.min-1.7.7.js',)

    def render(self, name, value, attrs={}):
        attrs['class'] = 'form-control'
        html = super(DecimalInput, self).render(name, value, attrs)
        html = html.replace('type="number"', 'type="text"')
        js = "<script>$('#id_{}').mask('###.###.##0,00', {{reverse: true}});</script>".format(name)
        return mark_safe('{}\n{}'.format(html, js))


class MoneyInput(DecimalInput):
    def render(self, name, value, attrs={}):
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


class RenderableSelectMultiple(widgets.SelectMultiple):
    def __init__(self, template_name='renderable_widget.html', *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.template_name = template_name

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        str_values = set([force_unicode(v) for v in value])
        i = 0
        objects = []

        qs = hasattr(self.choices.queryset, 'all') and self.choices.queryset.all() or self.choices.queryset
        for obj in qs:
            option_value = obj.pk
            if has_id:
                final_attrs = dict(final_attrs, id='{}_{}'.format(attrs['id'], i))
            final_attrs['class'] = 'custom-checkbox'
            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            obj.widget = rendered_cb
            i += 1
            objects.append(obj)

        return mark_safe(render_to_string(self.template_name, dict(objects=objects)))


# File Widgets #


class FileInput(widgets.ClearableFileInput):
    def render(self, *args, **kwargs):
        widget = super(FileInput, self).render(*args, **kwargs)

        tokens = widget.split('Modificar: ')
        if len(tokens) == 2:
            extra, input = tokens
            extra = extra.replace('<label ', '<span class="custom-checkbox"></span><label ')
        else:
            extra, input = '', tokens[0]

        input = input[0:-2] + 'class="file-input" ' + input[-2:]
        html = '''
            <div class="upload-file">
                 {}
                 <label for="{}" style="padding:5px"></label>
            </div>
            <div style="margin-top:20px">{}</div>
            <script>$('#{}').change(function(){{$(this).parent().find('label').html($(this).val().split('\\\\').pop());}});</script>
        '''.format(input, kwargs['attrs']['id'], extra, kwargs['attrs']['id'])
        return mark_safe(html)


class ImageInput(widgets.ClearableFileInput):
    def render(self, *args, **kwargs):
        widget = super(ImageInput, self).render(*args, **kwargs)

        tokens = widget.split('Modificar:')
        if len(tokens) == 2:
            extra, input = tokens
            extra = extra.replace('<label ', '<span class="custom-checkbox"></span><label ')
        else:
            extra, input = '', tokens[0]

        input = input[0:-2] + 'class="file-input" ' + input[-2:]
        html = '''
            <div class="upload-file">
                 {}
                 <label for="{}" style="padding:5px"></label>
            </div>
            <div style="margin-top:20px">{}</div>
            <script>$('#{}').change(function(){{$(this).parent().find('label').html($(this).val().split('\\\\').pop());}});</script>

        '''.format(input, kwargs['attrs']['id'], extra, kwargs['attrs']['id'])
        return mark_safe(html)


class PhotoWidget(widgets.TextInput):
    def render(self, name, value, attrs={}):
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

    def render(self, name, value=None, attrs={}):
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
                '''.format(html, name)
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

    def render(self, name, value, attrs={}):
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
    def render(self, name, value, attrs={}):
        attrs['class'] = 'form-control'
        return super(PasswordInput, self).render(name, value, attrs)


class DecimalInput3(DecimalInput):

    def render(self, name, value, attrs={}):
        attrs['class'] = 'form-control'
        html = super(DecimalInput, self).render(name, value, attrs)
        html = html.replace('type="number"', 'type="text"')
        js = "<script>$('#id_{}').mask('#.##0,000', {{reverse: true, clearIfNotMatch: true}});</script>".format(name)
        return mark_safe('{}\n{}'.format(html, js))


class OneDigitValidationInput(TextInput):

    class Media:
        js = ('/static/js/jquery.mask.min-1.7.7.js',)

    def render(self, name, value, attrs={}):
        attrs['class'] = 'form-control'
        html = super(OneDigitValidationInput, self).render(name, value, attrs)
        html = html.replace('type="number"', 'type="text"')
        js = "<script>$('#id_{}').mask('#.##0-0', {{reverse: true, clearIfNotMatch: true}});</script>".format(name)
        return mark_safe('{}\n{}'.format(html, js))


class CreditCardWidget(MaskWidget):
    def __init__(self):
        super(CreditCardWidget, self).__init__('9999 9999 9999 9999')
