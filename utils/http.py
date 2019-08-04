# -*- coding: utf-8 -*-
from tempfile import mktemp
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
import tempfile
import json
import os
import datetime
from django.contrib import messages
from djangoplus.utils.formatter import to_ascii


def mobile(request):
    if request:
        for device in ['iphone', 'android']:
            if device in request.META.get('HTTP_USER_AGENT', '').lower():
                return True
    return False

def httprr(request, url, message='', error=False):
    if message:
        if error:
            messages.error(request, message, extra_tags='danger')
        else:
            messages.success(request, message, extra_tags='success')

    if 'popup' in request.GET:
        return HttpResponse(url)

    if url in ('.', '..'):
        back = abs(url == '..' and -1 or 0)
        stack = request.session.get('stack', [])
        if len(stack) >= back:
            while back:
                stack.pop()
                back -= 1
            request.session.save()
            if stack:
                title, url = stack[-1]
        else:
            url = request.get_full_path()
    if request.is_ajax():
        return HttpResponse(url)
    else:
        return HttpResponseRedirect(url)


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
        import pdfkit
        file_name = tempfile.mktemp('.pdf')
        if landscape:
            html = html.replace('logo_if_portrait', 'logo_if_landscape')
            html = html.replace('content="Portrait"', 'content="Landscape"')
        html = html.replace('/media', settings.MEDIA_ROOT)
        html = html.replace('/static', '{}/{}/static'.format(settings.BASE_DIR, settings.PROJECT_NAME))
        pdfkit.from_string(html, file_name)
        str_bytes = open(file_name, "rb").read()
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
        context = dict(
            objects=objects, title=title, today=datetime.date.today(), logo=logo,
            project_name=project_name, project_description=project_description,
            unit_or_organization=unit_or_organization
        )
        html = render_to_string([template], context, request=request)
        super(ReportResponse, self).__init__(html, landscape)


class ComponentResponse(HttpResponse):
    def __init__(self, component):
        super(ComponentResponse, self).__init__(
            render_to_string('default.html', context=dict(paginator=component), request=component.request)
        )


def return_response(f_return, request, title, style, template_name, raise_response=False, ignore_pdf=False):
    from datetime import datetime
    from django.shortcuts import render
    from djangoplus.admin.models import Settings
    from djangoplus.ui.components import ComponentHasResponseException
    if type(f_return) == dict:
        if 'self' in f_return:
            f_return['obj'] = f_return['self']
        if title and 'title' not in f_return:
            f_return['title'] = title
        for key in f_return:
            if hasattr(f_return[key], 'process_request'):
                f_return[key].process_request()
        if 'pdf' in style and not ignore_pdf:
            request.GET._mutable = True
            request.GET['pdf'] = 1
            request.GET._mutable = False
            app_settings = Settings.default()
            f_return['logo'] = app_settings.logo_pdf and app_settings.logo_pdf or app_settings.logo
            f_return['project_name'] = app_settings.initials
            f_return['project_description'] = app_settings.name
            f_return['today'] = datetime.now()
            f_return['default_template'] = 'report.html'
            template_list = [template_name, 'report.html']
            landscape = 'landscape' in style
            response = PdfResponse(render_to_string(template_list, f_return, request=request), landscape=landscape)
        else:
            template_list = [template_name, 'default.html']
            response = render(request, template_list, f_return)
    else:
        response = f_return
    if raise_response:
        raise ComponentHasResponseException(response)
    else:
        return response
