# -*- coding: utf-8 -*-

from django.forms import widgets
from django.utils.safestring import mark_safe


class FormattedTextarea(widgets.Textarea):

    class Media:
        js = ('/static/js/tinymce.min.js',)

    def render(self, name, value, attrs=None, renderer=None):
        tools = [
            'insert', 'undo redo', 'formatselect', 'bold italic backcolor forecolor',
            'alignleft aligncenter alignright alignjustify',
            'bullist numlist outdent indent', 'removeformat', 'table'
        ]
        attrs['class'] = 'form-control'
        html = super(FormattedTextarea, self).render(name, value, attrs)
        js = '''
            <script>
            tinymce.remove();
            tinymce.init({{
              selector: '#id_{}',
              height: 300,
              menubar: false,
                plugins: [
                    'advlist autolink lists link image table textcolor',
                  ],
              toolbar: '{}',
                  content_css: []
            }});
            </script>
        '''.format(name, ' | '.join(tools))
        return mark_safe('{}{}'.format(html, js))
