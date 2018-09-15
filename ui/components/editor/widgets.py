# -*- coding: utf-8 -*-

from djangoplus.ui.components.select.widgets import *


class FormattedTextarea(widgets.Textarea):

    class Media:
        js = ('/static/js/tinymce.min.js',)

    def render(self, name, value, attrs=None, renderer=None):
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
              toolbar: 'insert | undo redo |  formatselect | bold italic backcolor forecolor  | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | table',
                  content_css: []
            }});
            </script>
        '''.format(name)
        return mark_safe('{}{}'.format(html, js))

