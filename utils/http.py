# -*- coding: utf-8 -*-
from tempfile import mktemp
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
import tempfile
import json
import os
import datetime
from djangoplus.utils.formatter import to_ascii


def mobile(request):
    for device in ['iphone', 'android']:
        if device in request.META.get('HTTP_USER_AGENT', '').lower():
            return True
    return False


class XlsResponse(HttpResponse):
    def __init__(self, data, name='Listagem'):
        import xlwt
        wb = xlwt.Workbook(encoding='iso8859-1')
        for title, rows in data:
            sheet = wb.add_sheet(title)
            for row_idx, row in enumerate(rows):
                for col_idx, label in enumerate(row):
                    sheet.write(row_idx, col_idx, label=label)
        file_name = mktemp()
        wb.save(file_name)
        HttpResponse.__init__(self, content=open(file_name, 'rb').read(), content_type='application/vnd.ms-excel')
        self['Content-Disposition'] = 'attachment; filename={}.xls'.format(to_ascii(name))


class CsvResponse(HttpResponse):
    def __init__(self, rows, name='Listagem'):
        import csv
        file_name = mktemp()
        with open(file_name, 'w', encoding='iso8859-1') as output:
            writer = csv.writer(output)
            for row in rows:
                writer.writerow([col for col in row]) # .encode('iso8859-1')
        HttpResponse.__init__(self, content=open(file_name, 'r').read(), content_type='application/csv')
        self['Content-Disposition'] = 'attachment; filename={}.xls'.format(to_ascii(name))


class ZipResponse(HttpResponse):
    def __init__(self, file_path):
        content = open(file_path)
        HttpResponse.__init__(self, content=content, content_type='application/zip')
        self['Content-Disposition'] = 'attachment; filename={}'.format(to_ascii(file_path.split(os.sep)[-1]))


class JsonResponse(HttpResponse):
    def __init__(self, data):
        content = json.dumps(data)
        HttpResponse.__init__(self, content=content, content_type='application/json')


class PdfResponse(HttpResponse):

    def __init__(self, html, landscape=False):
        from xhtml2pdf import pisa

        def link_callback(uri, rel):
            if not uri.startswith('/static'):
                s = '{}/{}'.format(settings.MEDIA_ROOT, uri.replace('/media', ''))
            else:
                s = '{}/{}/{}'.format(settings.BASE_DIR, settings.PROJECT_NAME, uri)
            return s

        tmp = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
        file_name = tmp.name
        if landscape:
            html = html.replace('a4 portrait', 'a4 landscape')
            html = html.replace('logo_if_portrait', 'logo_if_landscape')
        out = pisa.CreatePDF(html, tmp, link_callback=link_callback)
        out.dest.close()
        tmp = open(file_name, "rb")
        str_bytes = tmp.read()
        os.unlink(file_name)
        HttpResponse.__init__(self, str_bytes, content_type='application/pdf')


class ReportResponse(PdfResponse):
    def __init__(self, title, request, objects, landscape=False, template='report.html'):
        from djangoplus.admin.models import Settings
        app_settings = Settings.default()
        logo = app_settings.logo_pdf and app_settings.logo_pdf or app_settings.logo
        project_name = app_settings.initials
        project_description = app_settings.name
        unit_or_organization = request.session.get('scope')
        context = dict(objects=objects, title=title, today=datetime.date.today(), logo=logo,
                       project_name=project_name, project_description=project_description,
                       unit_or_organization=unit_or_organization)
        html = render_to_string([template], context, request=request)
        super(ReportResponse, self).__init__(html, landscape)


class ComponentResponse(HttpResponse):
    def __init__(self, component):
        super(ComponentResponse, self).__init__(
            render_to_string('default.html', context=dict(paginator=component), request=component.request)
        )