from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base giving every domain model creation/modification audit stamps.

    Every table in this service inherits from this, so "when did this row appear"
    is answerable without adding the columns case by case.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
