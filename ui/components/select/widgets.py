# -*- coding: utf-8 -*-
from django.forms import widgets
from django.utils.safestring import mark_safe
from djangoplus.utils.metadata import get_metadata
from django.template.loader import render_to_string
from djangoplus.utils.serialization import dumps_qs_query


INIT_SCRIPT = u'''%(html)s
<script>
    $("#id_%(name)s").select2({
        allowClear: true,
        language: 'pt-BR',
        %(templates)s
        escapeMarkup: function (markup) { var links = markup=='Nenhum resultado encontrado'? '<div>%(links)s</dev>' : ''; return markup + links; }}).on('select2:unselecting',
        function() {
            $(this).data('unselecting', true);}).on(
            'select2:opening',
            function(e) {
                if ($(this).data('unselecting')) {
                    $(this).removeData('unselecting');
                    e.preventDefault();
                }
            }
        );
    function load%(function_name)s(value){
        $('#id_%(name)s').val(value);
        $('#id_%(name)s').trigger("change");
    }
</script>'''

AJAX_INIT_SCRIPT = u'''%(html)s
<script>
    window['qs_%(name)s'] = { 'qs' : '%(qs_dump)s' }
    $('#id_%(name)s').select2({
        allowClear: true,
        language: 'pt-BR',
        escapeMarkup: function (markup) { var links = markup=='Nenhum resultado encontrado'? '<div>%(links)s</dev>' : ''; return markup + links; },
        ajax: {
            delay: 500,
            dataType: 'json',
            type: 'POST',
            url:'/autocomplete/%(app_label)s/%(model_name)s/',
            data: function (params) {return {qs: window['qs_%(name)s'], q:params.term}},
            cache: true,
            success: function(data){
                var values = $('#id_%(name)s').val();
                //$('#id_%(name)s').empty();
                $('#id_%(name)s').append($('<option></option>').attr("value", "").text(""));
                for(var i=0; i<data.results.length; i++){
                    var option = $('<option></option>').attr("value", data.results[i].id).text(data.results[i].text)
                    //if(values.indexOf(String(data.results[i].id))>-1) option.attr("selected", true)
                    $('#id_%(name)s').append(option);
                }
            }
        },
        minimumInputLength: 1,
        templateResult: function (item) {if (item.loading) return item.text; return item.html;}
        }
    );
    function load%(function_name)s(value, text){
        var option = $('<option></option>').attr("value", value).text(text).attr("selected", true);
        $('#id_%(name)s').append(option);
    }
</script>
'''

RELOAD_SCRIPT = u'''
<script>
    function reload_%(function_name)s(){
        var pk = $('#id_%(field_name)s').val()
        if(!pk) pk = 0;
        $.ajax({url:"/reload_options/%(app_label)s/%(model_name)s/%(value)s/%(lookup)s/"+pk+"/%(lazy)s/", dataType:'json', success:function( data ) {
            if(%(lazy)s){
                window['qs_%(name)s']['qs'] = data.qs;
            } else {
                $('#id_%(name)s').select2('destroy').empty().select2({data: data.results});
                $('#id_%(name)s').val('%(value)s'.split('_'));
            }
            $('#id_%(name)s').trigger("change");
        }});
    }
    $('#id_%(field_name)s').on('change', function(e) {
        reload_%(function_name)s();
    });
    reload_%(function_name)s();
</script>
'''

ADD_LINK = u'<a class="pull-right popup" style="padding:5px" href="javascript:" onclick="$(\\\'#id_%s\\\').select2(\\\'close\\\');popup(\\\'/add/%s/%s/?select=id_%s\\\');"><i class="fa fa-plus">\</i>Adicionar %s</a>'


class SelectWidget(widgets.Select):

    class Media:
        css = {'all': ('/static/css/select2.min.css',)}
        js = ('/static/js/select2.min.js', '/static/js/i18n/pt-BR.js')

    def __init__(self, *args, **kwargs):
        super(SelectWidget, self).__init__(*args, **kwargs)
        self.lazy = False
        self.form_filters = []

    def render(self, name, value, attrs=None):

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
                    templates.append('templateResult: function (item) {%s_templates = Array();' % templates_var_name)
                    if hasattr(self.choices.queryset.model, 'get_tree_index_field'):
                        tree_index_field = self.choices.queryset.model.get_tree_index_field()
                        if tree_index_field:
                            self.choices.queryset = self.choices.queryset.order_by(tree_index_field.name)
                    for obj in self.choices.queryset:
                        obj_html = render_to_string(select_template or 'select_template.html', dict(obj=obj, select_display=select_display)) or unicode(obj)
                        templates.append('%s_templates[%s] = \'%s\';' % (templates_var_name, obj.pk, obj_html.replace('\n', '')))
                    templates.append('return %s_templates[item.id];},' % templates_var_name)

            if hasattr(self, 'user'):
                for tmp in models:
                    class_name = tmp.__name__.lower()
                    app_label = get_metadata(tmp, 'app_label')
                    perm = '%s.add_%s' % (app_label, class_name)
                    if self.user.has_perm(perm):
                        links.append(ADD_LINK % (name, app_label, class_name, name, get_metadata(tmp, 'verbose_name')))

        html = super(SelectWidget, self).render(name, value, attrs)
        html = html.replace('---------', '')
        function_name = name.replace('-', '__')
        if model and self.lazy:
            app_label = get_metadata(model, 'app_label')
            model_name = model.__name__.lower()
            qs_dump = dumps_qs_query(queryset)
            html = AJAX_INIT_SCRIPT % dict(html=html, name=name, function_name=function_name, qs_dump=qs_dump, app_label=app_label, model_name=model_name, links=''.join(links))
        else:
            html = INIT_SCRIPT % dict(html=html, name=name, function_name=function_name, links=''.join(links), templates=''.join(templates))

        if model:
            value = value or 0
            lazy = self.lazy and 1 or 0
            for field_name, lookup in self.form_filters:
                if '-' in name:
                    field_name = '%s-%s' % (name.split('-')[0], field_name)
                app_label = get_metadata(model, 'app_label')
                model_name = model.__name__.lower()
                function_name = name.replace('-', '__')
                reload_script = RELOAD_SCRIPT % dict(
                    function_name=function_name, field_name=field_name, app_label=app_label, model_name=model_name,
                    value=value, lookup=lookup, lazy=lazy, name=name
                )
                html = '%s %s' % (html, reload_script)
        return mark_safe(html)


class SelectMultipleWidget(widgets.SelectMultiple):

    class Media:
        css = {'all': ('/static/css/select2.min.css',)}
        js = ('/static/js/select2.min.js', '/static/js/i18n/pt-BR.js')

    def __init__(self, *args, **kwargs):
        super(SelectMultipleWidget, self).__init__(*args, **kwargs)
        self.lazy = False
        self.form_filters = []

    def render(self, name, value, attrs=None):
        attrs['class'] = 'form-control'
        attrs['data-placeholder'] = u' '
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
                    templates.append('templateResult: function (item) {%s_templates = Array();' % templates_var_name)
                    if hasattr(self.choices.queryset.model, 'get_tree_index_field'):
                        tree_index_field = self.choices.queryset.model.get_tree_index_field()
                        if tree_index_field:
                            self.choices.queryset = self.choices.queryset.order_by(tree_index_field.name)
                    for obj in self.choices.queryset.all():
                        obj_html = render_to_string(select_template or 'select_template.html', dict(obj=obj, select_display=select_display)) or unicode(obj)
                        templates.append('%s_templates[%s] = \'%s\';' % (templates_var_name, obj.pk, obj_html.replace('\n', '')))
                    templates.append('return %s_templates[item.id];},' % templates_var_name)
        html = super(SelectMultipleWidget, self).render(name, value, attrs)
        links = []
        if queryset:
            models = queryset.model.__subclasses__() or [queryset.model]
            if hasattr(self, 'user'):
                for tmp in models:
                    class_name = tmp.__name__.lower()
                    app_label = get_metadata(tmp, 'app_label')
                    perm = u'%s.add_%s' % (app_label, class_name)
                    if self.user.has_perm(perm):
                        links.append(ADD_LINK % (name, app_label, class_name, name, get_metadata(tmp, 'verbose_name')))

        function_name = name.replace('-', '__')
        if queryset.model and self.lazy:
            app_label = get_metadata(queryset.model, 'app_label')
            model_name = queryset.model.__name__.lower()
            qs_dump = dumps_qs_query(queryset)
            html = AJAX_INIT_SCRIPT % dict(html=html, name=name, function_name=function_name, qs_dump=qs_dump, app_label=app_label, model_name=model_name, links=''.join(links))
        else:
            html = INIT_SCRIPT % dict(html=html, name=name, function_name=function_name, links=''.join(links), templates=''.join(templates))

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
                reload_script = RELOAD_SCRIPT % dict(function_name=function_name, field_name=field_name,
                    app_label=app_label, model_name=model_name, value=value, lookup=lookup, lazy=lazy, name=name)
                html = '%s %s' % (html, reload_script)

        return mark_safe(html)
    

class NullBooleanSelect(widgets.NullBooleanSelect):

    class Media:
        css = {'all': ('/static/css/select2.min.css',)}
        js = ('/static/js/select2.min.js', '/static/js/i18n/pt-BR.js')

    def render(self, name, value, attrs=None):
        attrs['class'] = 'form-control'
        if 'data-placeholder' not in self.attrs:
            attrs['data-placeholder'] = ' '
        function_name = name.replace('-', '__')
        html = super(NullBooleanSelect, self).render(name, value, attrs)
        html = INIT_SCRIPT % dict(html=html, name=name, function_name=function_name, templates='', links='')
        return mark_safe(html)