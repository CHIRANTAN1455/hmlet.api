"""Endpoint behaviour: CRUD, filtering, validation and query efficiency."""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.contracts.models import Contract
from apps.contracts.services import create_contract
from apps.properties.models import Unit

pytestmark = pytest.mark.django_db


# --- Properties ------------------------------------------------------------


def test_create_property(auth_client):
    response = auth_client.post(
        "/api/properties",
        {"name": "Tanjong Pagar Residences", "address": "88 Tanjong Pagar Road"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["unit_count"] == 0


def test_created_by_comes_from_the_token_not_the_body(auth_client, staff_user):
    """Attribution must not be forgeable."""
    response = auth_client.post(
        "/api/properties",
        {"name": "Somewhere", "address": "Anywhere", "created_by": 99999},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["created_by"] == staff_user.email


@pytest.mark.parametrize("payload", [{"name": "", "address": "x"}, {"name": "  ", "address": "x"}, {"name": "x"}])
def test_invalid_property_payloads_are_rejected(auth_client, payload):
    assert auth_client.post("/api/properties", payload, format="json").status_code == 400


def test_property_detail_includes_units(auth_client, property_obj, unit, other_unit):
    response = auth_client.get(f"/api/properties/{property_obj.id}")
    assert response.status_code == 200
    assert response.data["unit_count"] == 2
    assert {u["unit_number"] for u in response.data["units"]} == {"01-01", "01-02"}


def test_property_list_omits_units(auth_client, property_obj, unit):
    """The list payload must not grow with the portfolio."""
    response = auth_client.get("/api/properties")
    assert "units" not in response.data["results"][0]
    assert response.data["results"][0]["unit_count"] == 1


def test_missing_property_is_404(auth_client):
    assert auth_client.get("/api/properties/999999").status_code == 404


# --- Units -----------------------------------------------------------------


def test_create_unit_under_property(auth_client, property_obj):
    response = auth_client.post(
        f"/api/properties/{property_obj.id}/units",
        {"unit_number": "03-04", "monthly_rent": "2750.00"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["property_id"] == property_obj.id
    assert response.data["status"] == "available"


def test_duplicate_unit_number_in_same_property_is_rejected(auth_client, property_obj, unit):
    response = auth_client.post(
        f"/api/properties/{property_obj.id}/units",
        {"unit_number": unit.unit_number, "monthly_rent": "1000.00"},
        format="json",
    )
    assert response.status_code == 400


def test_same_unit_number_in_a_different_property_is_allowed(auth_client, property_obj, unit, staff_user):
    from apps.properties.models import Property

    other = Property.objects.create(name="Other Block", address="Elsewhere", created_by=staff_user)
    response = auth_client.post(
        f"/api/properties/{other.id}/units",
        {"unit_number": unit.unit_number, "monthly_rent": "1000.00"},
        format="json",
    )
    assert response.status_code == 201


@pytest.mark.parametrize("rent", ["0", "-100.00"])
def test_non_positive_rent_is_rejected(auth_client, property_obj, rent):
    response = auth_client.post(
        f"/api/properties/{property_obj.id}/units",
        {"unit_number": "X-1", "monthly_rent": rent},
        format="json",
    )
    assert response.status_code == 400


def test_unit_under_missing_property_is_404(auth_client):
    response = auth_client.post(
        "/api/properties/999999/units", {"unit_number": "X", "monthly_rent": "100"}, format="json"
    )
    assert response.status_code == 404


def test_filter_units_by_status(auth_client, unit, other_unit, member, today):
    create_contract(
        member=member,
        unit=unit,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=100),
    )
    available = auth_client.get("/api/units?status=available")
    occupied = auth_client.get("/api/units?status=occupied")

    assert [u["id"] for u in available.data["results"]] == [other_unit.id]
    assert [u["id"] for u in occupied.data["results"]] == [unit.id]


def test_filter_units_by_rent_range(auth_client, unit, other_unit):
    response = auth_client.get("/api/units?min_rent=2800")
    assert [u["id"] for u in response.data["results"]] == [other_unit.id]


def test_invalid_status_filter_is_rejected(auth_client, unit):
    assert auth_client.get("/api/units?status=bogus").status_code == 400


# --- Members ---------------------------------------------------------------


def test_create_member(auth_client):
    response = auth_client.post(
        "/api/members", {"full_name": "Amara Nwosu", "email": "amara@example.com"}, format="json"
    )
    assert response.status_code == 201


def test_duplicate_member_email_is_rejected_case_insensitively(auth_client, member):
    response = auth_client.post(
        "/api/members", {"full_name": "Someone", "email": member.email.upper()}, format="json"
    )
    assert response.status_code == 400


def test_search_members(auth_client, member, other_member):
    response = auth_client.get("/api/members?search=priya")
    assert [m["id"] for m in response.data["results"]] == [member.id]


# --- Contracts -------------------------------------------------------------


def test_create_contract_defaults_rent_to_the_unit(auth_client, member, unit):
    response = auth_client.post(
        "/api/contracts",
        {
            "member_id": member.id,
            "unit_id": unit.id,
            "start_date": "2030-01-01",
            "end_date": "2030-12-31",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Decimal(response.data["monthly_rent"]) == unit.monthly_rent
    assert Decimal(response.data["total_value"]) == unit.monthly_rent * 12


def test_create_contract_honours_a_rent_override(auth_client, member, unit):
    response = auth_client.post(
        "/api/contracts",
        {
            "member_id": member.id,
            "unit_id": unit.id,
            "start_date": "2030-01-01",
            "end_date": "2030-06-30",
            "monthly_rent": "1234.00",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Decimal(response.data["total_value"]) == Decimal("7404.00")


def test_total_value_cannot_be_supplied_by_the_client(auth_client, member, unit):
    """A client must not be able to declare what it owes."""
    response = auth_client.post(
        "/api/contracts",
        {
            "member_id": member.id,
            "unit_id": unit.id,
            "start_date": "2030-01-01",
            "end_date": "2030-12-31",
            "total_value": "1.00",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Decimal(response.data["total_value"]) == unit.monthly_rent * 12


def test_end_before_start_is_rejected(auth_client, member, unit):
    response = auth_client.post(
        "/api/contracts",
        {
            "member_id": member.id,
            "unit_id": unit.id,
            "start_date": "2030-06-01",
            "end_date": "2030-01-01",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "end_date" in response.data["error"]["details"]


def test_overlapping_contract_via_api_is_rejected(auth_client, member, other_member, unit):
    payload = {
        "member_id": member.id,
        "unit_id": unit.id,
        "start_date": "2030-01-01",
        "end_date": "2030-12-31",
    }
    assert auth_client.post("/api/contracts", payload, format="json").status_code == 201

    clash = dict(payload, member_id=other_member.id, start_date="2030-06-01", end_date="2030-07-01")
    response = auth_client.post("/api/contracts", clash, format="json")
    assert response.status_code in (400, 409)
    assert Contract.objects.filter(unit=unit).count() == 1


def test_unknown_member_or_unit_is_rejected(auth_client, member, unit):
    response = auth_client.post(
        "/api/contracts",
        {"member_id": 999999, "unit_id": unit.id, "start_date": "2030-01-01", "end_date": "2030-02-01"},
        format="json",
    )
    assert response.status_code == 400


def test_active_filter_returns_only_current_contracts(
    auth_client, member, other_member, unit, other_unit, today
):
    create_contract(
        member=member,
        unit=unit,
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=10),
    )
    create_contract(
        member=other_member,
        unit=other_unit,
        start_date=today + timedelta(days=100),
        end_date=today + timedelta(days=200),
    )

    active = auth_client.get("/api/contracts?active=true")
    assert active.data["count"] == 1
    assert active.data["results"][0]["status"] == "active"

    inactive = auth_client.get("/api/contracts?active=false")
    assert inactive.data["count"] == 1
    assert inactive.data["results"][0]["status"] == "upcoming"

    assert auth_client.get("/api/contracts").data["count"] == 2


def test_contract_response_embeds_member_and_unit(auth_client, active_contract):
    response = auth_client.get("/api/contracts")
    row = response.data["results"][0]
    assert row["member"]["full_name"] == active_contract.member.full_name
    assert row["unit"]["unit_number"] == active_contract.unit.unit_number
    assert row["property_name"] == active_contract.unit.property.name


def test_filter_contracts_by_member(auth_client, active_contract, member):
    response = auth_client.get(f"/api/contracts?member={member.id}")
    assert response.data["count"] == 1


# --- Cross-cutting ---------------------------------------------------------


def test_list_responses_are_paginated(auth_client, property_obj):
    response = auth_client.get("/api/properties")
    assert {"count", "total_pages", "page", "page_size", "results"} <= set(response.data)


def _count_queries(client, url):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
        assert response.status_code == 200
    return len(ctx), response


def test_unit_list_avoids_n_plus_one(auth_client, property_obj):
    """Query count must be constant, not proportional to the number of rows.

    Asserted as "same count at 3 rows as at 30" rather than a magic number, so
    the test states the actual property and does not need editing when an
    unrelated query (auth, pagination) is added or removed.
    """
    Unit.objects.bulk_create(
        [
            Unit(property=property_obj, unit_number=f"S-{i:03d}", monthly_rent=Decimal("1000"))
            for i in range(3)
        ]
    )
    few, response = _count_queries(auth_client, "/api/units?page_size=50")
    assert len(response.data["results"]) == 3

    Unit.objects.bulk_create(
        [
            Unit(property=property_obj, unit_number=f"L-{i:03d}", monthly_rent=Decimal("1000"))
            for i in range(27)
        ]
    )
    many, response = _count_queries(auth_client, "/api/units?page_size=50")
    assert len(response.data["results"]) == 30

    assert few == many, f"query count grew from {few} to {many} with 10x the rows"


def test_contract_list_avoids_n_plus_one(auth_client, property_obj, member, today):
    def add_contracts(prefix, n):
        for i in range(n):
            u = Unit.objects.create(
                property=property_obj, unit_number=f"{prefix}-{i:03d}", monthly_rent=Decimal("1000")
            )
            create_contract(
                member=member,
                unit=u,
                start_date=today - timedelta(days=5),
                end_date=today + timedelta(days=5),
            )

    add_contracts("C", 2)
    few, response = _count_queries(auth_client, "/api/contracts?page_size=50")
    assert len(response.data["results"]) == 2

    add_contracts("D", 18)
    many, response = _count_queries(auth_client, "/api/contracts?page_size=50")
    assert len(response.data["results"]) == 20

    assert few == many, f"query count grew from {few} to {many} with 10x the rows"
