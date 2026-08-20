"""Make double-booking impossible at the database level.

Application-level validation cannot prevent this on its own: two concurrent
requests can both pass an overlap check before either commits. Only a database
constraint closes that window.

    EXCLUDE USING gist (unit_id WITH =, daterange(start_date, end_date, '[]') WITH &&)

Reads as: no two rows may share a unit AND have intersecting date ranges. The
'[]' bounds make both endpoints inclusive, matching the domain rule that a
contract covers its end date.

This is PostgreSQL-only -- SQLite has no exclusion constraints. The operations
are therefore guarded on the connection vendor so the SQLite fallback still
migrates cleanly, dropping to application-level enforcement only (documented in
README > Double-booking prevention).
"""

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField
from django.contrib.postgres.fields.ranges import RangeBoundary, RangeOperators
from django.db import migrations, models

CONSTRAINT_NAME = "no_overlapping_contracts_per_unit"


class DateRange(models.Func):
    """SQL daterange(start, end, bounds) as a Django expression."""

    function = "daterange"
    output_field = DateRangeField()


def _constraint():
    return ExclusionConstraint(
        name=CONSTRAINT_NAME,
        expressions=[
            ("unit", RangeOperators.EQUAL),
            (
                DateRange(
                    "start_date",
                    "end_date",
                    RangeBoundary(inclusive_lower=True, inclusive_upper=True),
                ),
                RangeOperators.OVERLAPS,
            ),
        ],
    )


def add_exclusion_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    # btree_gist lets a GiST index mix the scalar '=' on unit_id with the range
    # '&&' operator. Without it the constraint cannot be created.
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    schema_editor.add_constraint(apps.get_model("contracts", "Contract"), _constraint())


def drop_exclusion_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.remove_constraint(apps.get_model("contracts", "Contract"), _constraint())


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            add_exclusion_constraint,
            reverse_code=drop_exclusion_constraint,
        ),
    ]
