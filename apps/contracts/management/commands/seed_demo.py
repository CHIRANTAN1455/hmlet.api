"""Populate the database with a realistic demo dataset.

Dates are computed relative to today rather than hard-coded, so the seeded data
still demonstrates active / upcoming / expired contracts whenever a reviewer
runs it -- a fixture with literal 2026 dates would be entirely "expired" a year
from now and the ?active=true filter would look broken.
"""

from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.contracts.models import Contract
from apps.contracts.services import create_contract, sync_all_unit_statuses
from apps.members.models import Member
from apps.properties.models import Property, Unit

User = get_user_model()

DEMO_PASSWORD = "DemoPass123!"

PROPERTIES = [
    {
        "name": "Cantonment House",
        "address": "12 Cantonment Road, Singapore 089736",
        "units": [
            ("01-01", "2500.00"),
            ("01-02", "2800.00"),
            ("02-01", "3200.00"),
            ("02-02", "3400.00"),
        ],
    },
    {
        "name": "Tanjong Pagar Residences",
        "address": "88 Tanjong Pagar Road, Singapore 088512",
        "units": [
            ("05-11", "4100.00"),
            ("05-12", "4350.00"),
            ("12-01", "6800.00"),
        ],
    },
    {
        "name": "Joo Chiat Lofts",
        "address": "45 Joo Chiat Place, Singapore 427756",
        "units": [
            ("A-01", "1950.00"),
            ("A-02", "2050.00"),
        ],
    },
]

MEMBERS = [
    ("Priya Raman", "priya.raman@example.com", "+65 8123 4567"),
    ("Wei Lim", "wei.lim@example.com", "+65 8234 5678"),
    ("Daniel Okafor", "daniel.okafor@example.com", "+65 8345 6789"),
    ("Sofia Alvarez", "sofia.alvarez@example.com", ""),
    ("Hiroshi Tanaka", "hiroshi.tanaka@example.com", "+65 8456 7890"),
]


class Command(BaseCommand):
    help = "Seed demo staff user, properties, units, members and contracts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo data first. Destructive.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Resetting existing data..."))
            Contract.objects.all().delete()
            Unit.objects.all().delete()
            Property.objects.all().delete()
            Member.objects.all().delete()
            User.objects.filter(email="demo@hmlet.com").delete()

        staff, created = User.objects.get_or_create(
            email="demo@hmlet.com",
            defaults={"full_name": "Demo Staff"},
        )
        if created:
            staff.set_password(DEMO_PASSWORD)
            staff.save(update_fields=["password"])

        properties = []
        for spec in PROPERTIES:
            prop, _ = Property.objects.get_or_create(
                name=spec["name"],
                defaults={"address": spec["address"], "created_by": staff},
            )
            for number, rent in spec["units"]:
                Unit.objects.get_or_create(
                    property=prop,
                    unit_number=number,
                    defaults={"monthly_rent": Decimal(rent)},
                )
            properties.append(prop)

        members = []
        for full_name, email, phone in MEMBERS:
            member, _ = Member.objects.get_or_create(
                email=email,
                defaults={"full_name": full_name, "phone": phone},
            )
            members.append(member)

        units = list(Unit.objects.order_by("property_id", "unit_number"))

        # A deliberate spread so every query in the brief returns something:
        #   - two currently active  -> ?active=true is non-empty
        #   - one expired           -> proves status is date-derived, not a flag
        #   - one upcoming          -> proves a future contract does NOT occupy
        #   - one back-to-back      -> proves adjacent ranges are not overlaps
        #   - one part-month        -> exercises the pro-rata calculation
        plan = [
            # (member, unit, start, end, rent override)
            (members[0], units[0], today - relativedelta(months=4), today + relativedelta(months=8), None),
            (members[1], units[1], today - relativedelta(months=1), today + relativedelta(months=11), None),
            (members[2], units[2], today - relativedelta(months=18), today - relativedelta(months=6), None),
            (members[3], units[3], today + relativedelta(months=2), today + relativedelta(months=14), None),
            (members[4], units[4], today - relativedelta(months=2), today + relativedelta(months=4), Decimal("3950.00")),
            # Starts the day after the expired one on units[2] ended -> adjacent, legal.
            (members[0], units[2], today - relativedelta(months=6) + timedelta(days=1), today + relativedelta(months=6), None),
            # Part-month tail: 45 days, exercises the pro-rata branch.
            (members[1], units[5], today + relativedelta(months=1), today + relativedelta(months=1) + timedelta(days=44), None),
        ]

        created_contracts = 0
        for member, unit, start, end, rent in plan:
            if Contract.objects.overlapping(unit, start, end).exists():
                continue
            create_contract(
                member=member,
                unit=unit,
                start_date=start,
                end_date=end,
                monthly_rent=rent,
            )
            created_contracts += 1

        sync_all_unit_statuses()

        active = Contract.objects.active().count()
        occupied = Unit.objects.filter(status="occupied").count()

        self.stdout.write(self.style.SUCCESS("\nDemo data ready.\n"))
        self.stdout.write(f"  Staff login   : demo@hmlet.com / {DEMO_PASSWORD}")
        self.stdout.write(f"  Properties    : {Property.objects.count()}")
        self.stdout.write(f"  Units         : {Unit.objects.count()} ({occupied} occupied)")
        self.stdout.write(f"  Members       : {Member.objects.count()}")
        self.stdout.write(
            f"  Contracts     : {Contract.objects.count()} "
            f"({created_contracts} new, {active} currently active)"
        )
        self.stdout.write("\n  Try: GET /api/contracts?active=true  and  GET /api/units?status=available\n")
