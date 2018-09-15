# -*- coding: utf-8 -*-

import os
from django.forms import widgets
from djangoplus.test import cache
from django.utils.safestring import mark_safe
from djangoplus.utils.metadata import get_metadata
from django.template.loader import render_to_string
from djangoplus.utils.serialization import dumps_qs_query


INIT_SCRIPT = '''{html}
<script>
    $("#id_{name}").select2({{
        allowClear: true,
        language: 'pt-BR',
        {templates}
        escapeMarkup: function (markup) {{ var links = markup=='Nenhum resultado encontrado'? '<div>{links}</dev>' : ''; return markup + links; }}}}).on('select2:unselecting',
        function() {{
            $(this).data('unselecting', true);}}).on(
            'select2:opening',
            function(e) {{
                if ($(this).data('unselecting')) {{
                    $(this).removeData('unselecting');
                    e.preventDefault();
                }}
            }}
        );
    function load{function_name}(value){{
        $('#id_{name}').val(value);
        $('#id_{name}').trigger("change");
    }}
</script>'''

AJAX_INIT_SCRIPT = '''{html}
<script>
    window['qs_{name}'] = {{ 'qs' : '{qs_dump}' }}
    $('#id_{name}').select2({{
        allowClear: true,
        language: 'pt-BR',
        escapeMarkup: function (markup) {{ var links = markup=='Nenhum resultado encontrado'? '<div>{links}</dev>' : ''; return markup + links; }},
        ajax: {{
            delay: 500,
            dataType: 'json',
            type: 'POST',
            url:'/autocomplete/{app_label}/{model_name}/',
            data: function (params) {{return {{qs: window['qs_{name}'], q:params.term}}}},
            cache: true,
            transport: function (params, success, failure) {{
                if({minimum_input_length}==0 && $('#id_{name}').prop('cache')){{
                    success($('#id_{name}').prop('cache'));
                }} else {{
                    var request = $.ajax(params);
                    request.then(success);
                    request.fail(failure);
                    return request;
                }}
            }},
            success: function(data){{
                if({minimum_input_length}==0) $('#id_{name}').prop('cache', data);
                var values = $('#id_{name}').val();
                $('#id_{name}').append($('<option></option>').attr("value", "").text(""));
                for(var i=0; i<data.results.length; i++){{
                    var option = $('<option></option>').attr("value", data.results[i].id).text(data.results[i].text)
                    $('#id_{name}').append(option);
                }}
            }}
        }},
        minimumInputLength: {minimum_input_length},
        templateResult: function (item) {{if (item.loading) return item.text; return item.html;}}
        }}
    );
    $('#id_{name}').on("select2:unselecting", function (e) {{
        $('#id_{name}').val('').trigger("change");
        e.preventDefault();
    }});
    function load{function_name}(value, text){{
        var option = $('<option></option>').attr("value", value).text(text).attr("selected", true);
        $('#id_{name}').append(option);
    }}
</script>
'''

RELOAD_SCRIPT = '''
<script>
    function reload_{function_name}(){{
        var pk = $('#id_{popup}{field_name}').val()
        if(!pk) pk = 0;
        $.ajax({{url:"/reload_options/{app_label}/{model_name}/{value}/{lookup}/"+pk+"/{lazy}/", dataType:'json', success:function( data ) {{
            if({lazy}){{
                window['qs_{name}']['qs'] = data.qs;
            }} else {{
                $('#id_{name}').select2('destroy').empty().select2({{allowClear: true, data: data.results}});
                $('#id_{name}').val('{value}'.split('_'));
            }}
            $('#id_{name}').trigger("change");
        }}}});
    }}
    $('#id_{popup}{field_name}').on('change', function(e) {{
        reload_{function_name}();
    }});
    reload_{function_name}();
</script>
'''

ADD_LINK = '<a class="pull-right popup" style="padding:5px" href="javascript:" onclick="$(\\\'#id_{}\\\').select2(\\\'close\\\');popup(\\\'/add/{}/{}/?select=id_{}\\\');"><i class="fa fa-plus">\</i>Adicionar {}</a>'


class SelectWidget(widgets.Select):

    class Media:
        css = {'all': ('/static/css/select2.min.css',)}
        js = ('/static/js/select2.min.js', '/static/js/i18n/pt-BR.js')

    def __init__(self, *args, **kwargs):
        super(SelectWidget, self).__init__(*args, **kwargs)
        self.lazy = False
        self.form_filters = []
        self.minimum_input_length = 3

    def render(self, name, value, attrs=None, renderer=None):

        if cache.HEADLESS:
            self.lazy = False

        attrs['class'] = 'form-control'
        if 'data-placeholder' not in self.attrs:
            attrs['data-placeholder'] = ' '
        queryset = None
        if self.lazy and hasattr(self.choices, 'queryset'):
            queryset = self.choices.queryset
            self.choices.queryset = self.choices.queryset.model.objects.filter(pk=value or 0)

        model = None
        links = []
        templates = []
        if hasattr(self.choices, 'queryset'):
            model = self.choices.queryset.model
            models = model.__subclasses__() or [model]

            if not self.lazy:
                select_template = get_metadata(model, 'select_template')
                select_display = get_metadata(model, 'select_display')
                if select_template or select_display:
                    templates_var_name = name.replace('-', '_')
                    templates.append('templateResult: function (item) {{{}_templates = Array();'.format(templates_var_name))
                    if hasattr(self.choices.queryset.model, 'get_tree_index_field'):
                        tree_index_field = self.choices.queryset.model.get_tree_index_field()
                        if tree_index_field:
                            self.choices.queryset = self.choices.queryset.order_by(tree_index_field.name)
                    for obj in self.choices.queryset:
                        obj_html = render_to_string(select_template or 'select_template.html', dict(obj=obj, select_display=select_display)) or str(obj)
                        templates.append('{}_templates[{}] = \'{}\';'.format(templates_var_name, obj.pk, obj_html.replace('\n', '')))
                    templates.append('return {}_templates[item.id];}},'.format(templates_var_name))

            if hasattr(self, 'user'):
                for tmp in models:
                    class_name = tmp.__name__.lower()
                    app_label = get_metadata(tmp, 'app_label')
                    perm = '{}.add_{}'.format(app_label, class_name)
                    if self.user.has_perm(perm):
                        links.append(ADD_LINK.format(name, app_label, class_name, name, get_metadata(tmp, 'verbose_name')))

        html = super(SelectWidget, self).render(name, value, attrs)
        html = html.replace('---------', '')
        function_name = name.replace('-', '__')
        if model and self.lazy:
            app_label = get_metadata(model, 'app_label')
            model_name = model.__name__.lower()
            qs_dump = dumps_qs_query(queryset)
            html = AJAX_INIT_SCRIPT.format(html=html, name=name, function_name=function_name, qs_dump=qs_dump, app_label=app_label, model_name=model_name, links=''.join(links), minimum_input_length=self.minimum_input_length)
        else:
            html = INIT_SCRIPT.format(html=html, name=name, function_name=function_name, links=''.join(links), templates=''.join(templates))

        if model:
            value = value or 0
            lazy = self.lazy and 1 or 0
            for field_name, lookup in self.form_filters:
                if '-' in name:
                    field_name = '{}-{}'.format(name.split('-')[0], field_name)
                app_label = get_metadata(model, 'app_label')
                model_name = model.__name__.lower()
                function_name = name.replace('-', '__')
                popup = 'popup' in function_name and 'popup-' or ''
                reload_script = RELOAD_SCRIPT.format(
                    function_name=function_name, field_name=field_name, app_label=app_label, model_name=model_name,
                    value=value, lookup=lookup, lazy=lazy, name=name, popup=popup
                )
                html = '{} {}'.format(html, reload_script)
        return mark_safe(html)


class SelectMultipleWidget(widgets.SelectMultiple):

    class Media:
        css = {'all': ('/static/css/select2.min.css',)}
        js = ('/static/js/select2.min.js', '/static/js/i18n/pt-BR.js')

    def __init__(self, *args, **kwargs):
        super(SelectMultipleWidget, self).__init__(*args, **kwargs)
        self.lazy = False
        self.form_filters = []
        self.minimum_input_length = 3

    def render(self, name, value, attrs=None, renderer=None):

        if cache.HEADLESS:
            self.lazy = False

        attrs['class'] = 'form-control'
        attrs['data-placeholder'] = ' '
        queryset = None
        templates = []
        if hasattr(self.choices, 'queryset'):
            queryset = self.choices.queryset.all()
            if self.lazy:
                self.choices.queryset = self.choices.queryset.model.objects.filter(pk__in=value or [])
            else:
                select_template = get_metadata(queryset.model, 'select_template')
                select_display = get_metadata(queryset.model, 'select_display')
                if select_template or select_display:
                    templates_var_name = name.replace('-', '_')
                    templates.append('templateResult: function (item) {{{}_templates = Array();'.format(templates_var_name))
                    if hasattr(self.choices.queryset.model, 'get_tree_index_field'):
                        tree_index_field = self.choices.queryset.model.get_tree_index_field()
                        if tree_index_field:
                            self.choices.queryset = self.choices.queryset.order_by(tree_index_field.name)
                    for obj in self.choices.queryset.all():
                        obj_html = render_to_string(select_template or 'select_template.html', dict(obj=obj, select_display=select_display)) or str(obj)
                        templates.append('{}_templates[{}] = \'{}\';'.format(templates_var_name, obj.pk, obj_html.replace('\n', '')))
                    templates.append('return {}_templates[item.id];}},'.format(templates_var_name))
        html = super(SelectMultipleWidget, self).render(name, value, attrs)
        links = []
        if queryset:
            models = queryset.model.__subclasses__() or [queryset.model]
            if hasattr(self, 'user'):
                for tmp in models:
                    class_name = tmp.__name__.lower()
                    app_label = get_metadata(tmp, 'app_label')
                    perm = '{}.add_{}'.format(app_label, class_name)
                    if self.user.has_perm(perm):
                        links.append(ADD_LINK.format(name, app_label, class_name, name, get_metadata(tmp, 'verbose_name')))

        function_name = name.replace('-', '__')
        if queryset.model and self.lazy:
            app_label = get_metadata(queryset.model, 'app_label')
            model_name = queryset.model.__name__.lower()
            qs_dump = dumps_qs_query(queryset)
            html = AJAX_INIT_SCRIPT.format(html=html, name=name, function_name=function_name, qs_dump=qs_dump, app_label=app_label, model_name=model_name, links=''.join(links), minimum_input_length=self.minimum_input_length)
        else:
            html = INIT_SCRIPT.format(html=html, name=name, function_name=function_name, links=''.join(links), templates=''.join(templates))

        if queryset.model:
            l = []
            if value:
                for pk in value:
                    l.append(str(pk))
            else:
                l.append('0')
            lazy = self.lazy and 1 or 0
            for field_name, lookup in self.form_filters:
                app_label = get_metadata(queryset.model, 'app_label')
                model_name = queryset.model.__name__.lower()
                value = '_'.join(l)
                function_name = name.replace('-', '__')
                popup = 'popup' in function_name and 'popup-' or ''
                reload_script = RELOAD_SCRIPT.format(function_name=function_name, field_name=field_name, popup=popup,
                    app_label=app_label, model_name=model_name, value=value, lookup=lookup, lazy=lazy, name=name)
                html = '{} {}'.format(html, reload_script)

        return mark_safe(html)
    

class NullBooleanSelect(widgets.NullBooleanSelect):

    class Media:
        css = {'all': ('/static/css/select2.min.css',)}
        js = ('/static/js/select2.min.js', '/static/js/i18n/pt-BR.js')

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        if 'data-placeholder' not in self.attrs:
            attrs['data-placeholder'] = ' '
        function_name = name.replace('-', '__')
        html = super(NullBooleanSelect, self).render(name, value, attrs)
        html = INIT_SCRIPT.format(html=html, name=name, function_name=function_name, templates='', links='')
        return mark_safe(html)