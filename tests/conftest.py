"""Shared fixtures.

Plain pytest fixtures rather than factory_boy: the object graph here is small
and explicit fixtures make the arrangement of each test obvious at a glance.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.contracts.services import create_contract
from apps.members.models import Member
from apps.properties.models import Property, Unit

User = get_user_model()

PASSWORD = "TestPass123!"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com",
        full_name="Staff Member",
        password=PASSWORD,
    )


@pytest.fixture
def auth_client(api_client, staff_user):
    """An APIClient carrying a valid JWT for staff_user."""
    response = api_client.post(
        "/api/auth/login",
        {"email": staff_user.email, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200, response.data
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client


@pytest.fixture
def property_obj(db, staff_user):
    return Property.objects.create(
        name="Cantonment House",
        address="12 Cantonment Road, Singapore",
        created_by=staff_user,
    )


@pytest.fixture
def unit(db, property_obj):
    return Unit.objects.create(
        property=property_obj,
        unit_number="01-01",
        monthly_rent=Decimal("2500.00"),
    )


@pytest.fixture
def other_unit(db, property_obj):
    return Unit.objects.create(
        property=property_obj,
        unit_number="01-02",
        monthly_rent=Decimal("3000.00"),
    )


@pytest.fixture
def member(db):
    return Member.objects.create(full_name="Priya Raman", email="priya@example.com")


@pytest.fixture
def other_member(db):
    return Member.objects.create(full_name="Wei Lim", email="wei@example.com")


@pytest.fixture
def today():
    return date.today()


@pytest.fixture
def active_contract(db, member, unit, today):
    """A contract whose range covers today, so the unit reads as occupied."""
    return create_contract(
        member=member,
        unit=unit,
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=300),
    )
