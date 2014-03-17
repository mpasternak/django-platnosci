# -*- encoding: utf-8 -*-

import sys

from django.core.management.base import BaseCommand
from platnosci import tasks

class Command(BaseCommand):
    args = ''
    help = '''Sciaga definicje platnosci'''

    def handle(self, *args, **options):

        sys.stdout.write("Wysylam zapytanie o aktualizacje platnosci"
                         " do celery... ")

        tasks.UpdateDefinitionsTask().apply()

        sys.stdout.write("zrobiono!\n")
