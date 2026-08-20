from django.db import models

from apps.common.models import TimeStampedModel


class Member(TimeStampedModel):
    """A tenant.

    Deliberately not a User. Members have no credentials and cannot
    authenticate -- the brief specifies a staff-only system, and keeping the two
    as separate tables means a tenant record can never accidentally become a way
    into the API. If tenant logins are ever needed, the right move is to add a
    nullable OneToOne to User rather than to merge the models.
    """

    full_name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(
        unique=True,
        help_text="Unique across members; used to identify a returning tenant.",
    )
    phone = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "members"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"
