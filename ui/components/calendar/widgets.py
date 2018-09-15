# -*- coding: utf-8 -*-

from django.forms import widgets
from django.utils.safestring import mark_safe
from djangoplus.utils.formatter import format_value


class DateWidget(widgets.DateInput):

    class Media:
        css = {'all': ('/static/css/daterangepicker-2.1.24.css',)}
        js = ('/static/js/moment.min.js', '/static/js/daterangepicker-2.1.24.js', '/static/js/jquery.mask.min-1.7.7.js')

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        html = super(DateWidget, self).render(name, value, attrs)
        script = '''
            $("#id_{}").daterangepicker({{
                singleDatePicker: true,
                showDropdowns: false,
                autoUpdateInput: false,
                locale: {{
                    format: 'DD/MM/YYYY'
                }}
                }});
            $("#id_{}").on('apply.daterangepicker', function(ev, picker) {{
                  $(this).val(picker.startDate.format('DD/MM/YYYY'));
              }});
            $("#id_{}").mask("00/00/0000", {{clearIfNotMatch: true}});
        '''.format(name, name, name)
        html = '<div class="input-group">{}<span class="input-group-addon"><i class="fa fa-calendar"></i></span></div><script>{}</script>'.format(html, script)
        return mark_safe(html)

    def _format_value(self, value):
        if value:
            if type(value) in [str, str]:
                return value
            else:
                return format_value(value)
        return ''


class HiddenDateWidget(widgets.DateInput):

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'hidden'
        return super(HiddenDateWidget, self).render(name, value, attrs)


class DateTimeWidget(widgets.DateTimeInput):

    class Media:
        css = {'all': ('/static/css/daterangepicker-2.1.24.css', )}
        js = ('/static/js/moment.min.js', '/static/js/daterangepicker-2.1.24.js', '/static/js/jquery.mask.min-1.7.7.js')

    def render(self, name, value, attrs=None, renderer=None):
        attrs['class'] = 'form-control'
        html = super(DateTimeWidget, self).render(name, value, attrs)
        if type(value) not in [str, str]:
            js_value = value and 'new Date{}'.format((value.year, value.month-1, value.day, value.hour, value.minute),) or 'new Date()'
        else:
            js_value = "'{}'".format(value)
        script = '''
                    $("#id_{}").daterangepicker({{
                        singleDatePicker: true,
                        showDropdowns: false,
                        autoUpdateInput: false,
                        startDate: {},
                        timePicker: true,
                        timePickerIncrement: 5,
                        timePicker24Hour: true,
                        locale: {{
                            format: 'DD/MM/YYYY H:mm',
                            cancelLabel: 'Cancelar',
                            applyLabel: 'Aplicar',
                        }}
                        }});
                        $("#id_{}").on('apply.daterangepicker', function(ev, picker) {{
                          $(this).val(picker.startDate.format('DD/MM/YYYY H:mm'));
                        }});
                        $("#id_{}").mask("00/00/0000 00:00", {{clearIfNotMatch: true}});
                '''.format(name, js_value, name, name)
        html = '<div class="input-group">{}<span class="input-group-addon"><i class="fa fa-calendar"></i></span></div><script>{}</script>'.format(
        html, script)
        return mark_safe(html)

    def _format_value(self, value):
        if type(value) in [str, str]:
            return value
        else:
            return format_value(value)


class DateRangeWidget(widgets.MultiWidget):
    def __init__(self, widgets=[DateWidget, DateWidget], attrs={}):
        super(DateRangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return ['', '']
        return value

    def render(self, name, value, attrs=None, renderer=None):
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        output.append('<div class="s12" style="margin-left:-10px"><div class="col s6">A partir de')
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='{}_{}'.format(id_, i))
            output.append(widget.render(name + '_{}'.format(i), widget_value, final_attrs))
            if i == 0:
                output.append('</div><div class="col s6">Até')
        output.append('</div></div>')
        return mark_safe(self.format_output(output))


class DateFilterWidget(DateRangeWidget):

    class Media:
        css = {'all': ('/static/css/daterangepicker-2.1.24.css',)}
        js = ('/static/js/moment.min.js', '/static/js/daterangepicker-2.1.24.js', '/static/js/jquery.mask.min-1.7.7.js')

    def __init__(self, widgets=(HiddenDateWidget, HiddenDateWidget), attrs={}):
        super(DateRangeWidget, self).__init__(widgets, attrs)
        self.label = ''

    def decompress(self, value):
        if not value:
            return ['', '']
        return value

    def render(self, name, value, attrs=None, renderer=None):
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        start = value and len(value) > 0 and value[0] or None
        end = value and len(value) > 1 and value[1] or None

        start_js = start and 'var start = moment("{}", "DD/MM/YYYY");'.format(start) or 'var start = null;'
        end_js = end and 'var end = moment("{}", "DD/MM/YYYY");'.format(end) or 'var end = null;'

        final_attrs.update(id='{}_0'.format(id_))
        final_attrs.update(**{'data-type':'hidden_daterange'})
        output.append(self.widgets[0].render('{}_0'.format(name), start, final_attrs))
        final_attrs.update(id='{}_1'.format(id_))
        output.append(self.widgets[1].render('{}_1'.format(name), end, final_attrs))
        function_name = name.replace('-', '_')
        script = '''
            <script>

                {}
                {}

                function cb{}(start, end, onload) {{
                    var s = "{}";
                    var startInput = $("#{}_0");
                    var endInput = $("#{}_1");
                    var format = "D [de] MMMM [de] YYYY";

                    if(start !=null && end !=null){{
                        s = start.format(format) + ' - ' + end.format(format);
                        startInput.val(start.format("DD/MM/YYYY"));;
                        endInput.val(end.format("DD/MM/YYYY"));
                    }}
                    else if (start!= null){{
                        s = ' A partir de  ' + start.format(format);
                        startInput.val(start.format("DD/MM/YYYY"));
                    }}
                    else if(end!=null){{
                        s = ' Até ' + end.format(format);
                        endInput.val(end.format("DD/MM/YYYY"));
                    }} else {{
                        $('#reportrange{} span').html(s);
                        startInput.val('');
                        endInput.val('');
                    }}

                    if(start !=null || end !=null) $('#clear{}').show();
                    else $('#clear{}').hide();

                    $('#reportrange{} span').html(s);

                    if(onload!=true){{
                        startInput.trigger('change');
                    }}
                }}

                $('#reportrange{}').daterangepicker({{
                    showCustomRangeLabel: false,
                    locale: {{format: "DD/MM/YYYY", applyLabel: "Selecionar", cancelLabel: "Cancelar"}},
                    linkedCalendars: false,
                    alwaysShowCalendars: true,
                    opens: "center",
                    ranges: {{
                       'Hoje': [moment(), moment().add(1, 'days')],
                       'Ontem': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
                       'Últimos 7 dias': [moment().subtract(6, 'days'), moment()],
                       'Últimos 30 dias': [moment().subtract(29, 'days'), moment()],
                       'Este mês': [moment().startOf('month'), moment().endOf('month')],
                       'Mês passado': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
                    }}
                }}, cb{});

                cb{}(start, end, true);

            </script>
        '''.format(start_js, end_js, function_name, self.label, id_, id_, name, name, name, name, name, function_name, function_name)
        output.append('''
            <div class="form-control" style="cursor:pointer; width:auto;">
                <span id="reportrange{}">
                <i class="fa fa-calendar"></i>&nbsp;&nbsp;
                    <span style="white-space: nowrap"></span>&nbsp;
                    </span><i id="clear{}" onclick="cb{}(null, null)" class="fa fa-close">
                </i>&nbsp;
                <b class="caret"></b>&nbsp;&nbsp;&nbsp;</div>'''.format(name, name, function_name))
        output.append(script)

        s = mark_safe(''.join(output))
        return s

