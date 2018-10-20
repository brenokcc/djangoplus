# -*- coding: utf-8 -*-

from django.conf import settings
from django.utils import translation
from djangoplus.tools import terminal
from djangoplus.docs import Documentation
from django.utils.translation import ugettext as _
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--usecase', action='store', nargs=1, dest='usecase', default=False,
                            help='Prints the documetation of a specific usecase')
        parser.add_argument('--json', action='store_true', dest='json', default=False, help='')

    def handle(self, *args, **options):

        doc = Documentation()
        translation.activate(settings.LANGUAGE_CODE)

        usecase_name = options.get('usecase')

        if options.pop('json', False):
            print(str(doc.as_json()))
        else:
            output = list()
            if not usecase_name:
                output.append(terminal.bold(_('Description:').upper()))
                output.append(terminal.info(doc.description))
                output.append('')
                output.append(terminal.bold(_('Actors:').upper()))
                for i, actor in enumerate(doc.actors):
                    output.append('{}. {}'.format(i + 1, actor.name))
                output.append('')
                output.append(terminal.bold(_('Workflow:').upper()))
                for i, task in enumerate(doc.workflow.tasks):
                    output.append('{} {}'.format(' ' * i, task))
                output.append('')
            output.append(terminal.bold(_('Usecases:').upper()))
            for i, usecase in enumerate(doc.usecases):
                if not usecase_name or usecase.name == usecase_name[0]:
                    output.append(terminal.bold('* Usecase #{}'.format((i + 1))))
                    output.append('')
                    output.append('{}:\t\t\t{}'.format(terminal.info(_('Name')), usecase.name))
                    output.append('{}:\t\t{}'.format(terminal.info(_('Description')), usecase.description or ''))
                    output.append('{}:\t\t\t{}'.format(terminal.info(_('Actors')), ', '.join(usecase.actors)))
                    output.append('{}:\t\t{}'.format(terminal.info(_('Buniness Rules')), ', '.join(usecase.business_rules)))
                    output.append('{}:\t\t{}'.format(terminal.info(_('Pre-conditions')), ', '.join(usecase.pre_conditions)))
                    output.append('{}:\t\t{}'.format(terminal.info(_('Post-condition')), (usecase.post_condition or '')))
                    output.append('{}:'.format(terminal.info(_('Main-scenario'))))
                    output.append(usecase.get_interactions_as_string())
                    output.append('')
            output.append('')
            if not usecase_name:
                output.append(terminal.bold(_('Class Diagrams:').upper()))
                for class_diagram in doc.class_diagrams:
                    output.append(terminal.bold('\t{} {}'.format(class_diagram.name, _('Diagram'))))
                    for i, cls in enumerate(class_diagram.classes):
                        output.append('\t\t\t{}. {}'.format(i + 1, cls['name']))
            return '\n'.join(output)