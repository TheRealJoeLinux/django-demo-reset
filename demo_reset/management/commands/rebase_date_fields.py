from dateutil import parser

from django.core.management.base import BaseCommand, CommandError
from django.db.models import DateTimeField, DateField, F
from django.db.models.loading import get_apps, get_models
from django.utils import timezone
from django.conf import settings


class Command(BaseCommand):
    args = "<rebase_date>"
    help = """
    Rebases all date and datetime fields such that their offset from
    today will be the same as their offset from the specified <rebase_date>.
    """

    def handle(self, *args, **options):
        rebase_date = self.parse_rebase_date(args[0])
        today = timezone.now().date()
        delta = today - rebase_date

        self.ignores = getattr(settings, 'DEMO_DATE_RESET_IGNORES', {})

        for app in get_apps():
            app_models = get_models(app)
            if not app_models:
                continue

            app_name = app.__name__.split('.')[-2]
            if app_name in self.ignores:
                continue

            for klass in app_models:
                fields = self.get_date_fields_for_klass(klass)
                if fields:
                    update_kwargs = dict([(field_name, F(field_name) + delta) for field_name in fields])
                    klass.objects.update(**update_kwargs)

    def parse_rebase_date(self, rebase_date_str):
        """
        Parse the supplied rebase_date using "smart" dateutil.parser
        """
        try:
            parsed_date = parser.parse(rebase_date_str)
        except ValueError:
            raise CommandError('Cannot parse date from {0}'.format(rebase_date_str))
        return parsed_date.date()

    def get_date_fields_for_klass(self, klass):
        """
        Lookup the date/datetime fields in the specified model class
        Returns a list of the field names to be updated
        """
        klass_name = '.'.join((klass.__module__, klass.__name__))
        klass_ignores = self.ignores.get(klass_name, [])
        return [field.name
                for field in klass._meta.fields
                if (isinstance(field, (DateTimeField, DateField))
                    and field.name not in klass_ignores)]
