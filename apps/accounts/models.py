from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.common.models import TimeStampedModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """A staff user of the property management system.

    The brief specifies staff users only -- there is no tenant login. Tenants
    are represented by the Member model, which has no credentials attached.
    Keeping those two concepts as separate tables means a tenant can never
    accidentally acquire a way to authenticate.

    Email replaces username as the login identifier: there is no product reason
    to make staff invent a second name they will forget.
    """

    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)

    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate rather than delete to preserve audit history.",
    )
    is_staff = models.BooleanField(
        default=True,
        help_text="Staff-only system; every API-created account is staff.",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email
