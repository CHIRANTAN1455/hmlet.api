"""Recompute every unit's availability from its contracts.

Unit status depends on the calendar, not only on writes: a contract that ended
yesterday frees its unit today without any request touching the database. In
production this would run on a schedule (cron / Celery beat) shortly after
midnight. See README > Unit status is derived.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.contracts.services import sync_all_unit_statuses


class Command(BaseCommand):
    help = "Recalculate unit availability from contract date ranges."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Evaluate as at this date (YYYY-MM-DD) instead of today. Useful for testing.",
        )

    def handle(self, *args, **options):
        on_date = options.get("date")
        if on_date:
            on_date = timezone.datetime.strptime(on_date, "%Y-%m-%d").date()
        else:
            on_date = timezone.localdate()

        changed = sync_all_unit_statuses(on_date=on_date)
        self.stdout.write(
            self.style.SUCCESS(f"Unit statuses synced as at {on_date}: {changed} changed.")
        )
