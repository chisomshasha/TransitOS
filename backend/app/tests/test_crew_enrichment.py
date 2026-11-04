"""Tests for the driver/conductor user-enrichment fix.

Driver and Conductor documents only store `user_id`; their response
schemas declare `full_name`/`email`/`phone` as denormalized display
fields that must be populated from the linked user record. Previously
these routers never performed that join, so the fields always came
back null — which the mobile app's driver/conductor pickers rendered
as a raw user_id string instead of a name.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_driver_response_includes_user_fields(client, auth_headers, branch, driver_user):
    r = await client.post(
        "/drivers",
        headers=auth_headers,
        json={
            "user_id": str(driver_user["_id"]),
            "license_no": "ENR-LIC-001",
            "license_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "years_experience": 3,
            "status": "active",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["full_name"] == driver_user["full_name"]
    assert data["email"] == driver_user["email"]


async def test_list_drivers_includes_user_fields(client, auth_headers, branch, driver_user):
    await client.post(
        "/drivers",
        headers=auth_headers,
        json={
            "user_id": str(driver_user["_id"]),
            "license_no": "ENR-LIC-002",
            "license_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "years_experience": 3,
            "status": "active",
        },
    )
    r = await client.get("/drivers", headers=auth_headers, params={"page": 1, "page_size": 50})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    match = next(i for i in items if i["license_no"] == "ENR-LIC-002")
    assert match["full_name"] == driver_user["full_name"]
    assert match["email"] == driver_user["email"]


async def test_get_driver_includes_user_fields(client, auth_headers, branch, driver_user):
    create = await client.post(
        "/drivers",
        headers=auth_headers,
        json={
            "user_id": str(driver_user["_id"]),
            "license_no": "ENR-LIC-003",
            "license_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "years_experience": 3,
            "status": "active",
        },
    )
    driver_id = create.json()["data"]["id"]
    r = await client.get(f"/drivers/{driver_id}", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["full_name"] == driver_user["full_name"]


async def test_update_driver_response_includes_user_fields(client, auth_headers, branch, driver_user):
    create = await client.post(
        "/drivers",
        headers=auth_headers,
        json={
            "user_id": str(driver_user["_id"]),
            "license_no": "ENR-LIC-004",
            "license_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "years_experience": 3,
            "status": "active",
        },
    )
    driver_id = create.json()["data"]["id"]
    r = await client.patch(
        f"/drivers/{driver_id}", headers=auth_headers, json={"years_experience": 4}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["full_name"] == driver_user["full_name"]


async def test_create_conductor_response_includes_user_fields(client, auth_headers, branch):
    user_resp = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "cnd-enrich@transitos.app",
            "full_name": "Cindy Enrichment",
            "role": "conductor",
            "branch_id": str(branch["_id"]),
            "password": "Pass#12345",
        },
    )
    assert user_resp.status_code == 201, user_resp.text
    user_id = user_resp.json()["data"]["id"]

    r = await client.post(
        "/conductors",
        headers=auth_headers,
        json={"user_id": user_id, "badge_no": "ENR-BADGE-001", "status": "active"},
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["full_name"] == "Cindy Enrichment"
    assert data["email"] == "cnd-enrich@transitos.app"


async def test_list_conductors_includes_user_fields(client, auth_headers, branch):
    user_resp = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "cnd-enrich2@transitos.app",
            "full_name": "Connor Enrichment",
            "role": "conductor",
            "branch_id": str(branch["_id"]),
            "password": "Pass#12345",
        },
    )
    user_id = user_resp.json()["data"]["id"]
    await client.post(
        "/conductors",
        headers=auth_headers,
        json={"user_id": user_id, "badge_no": "ENR-BADGE-002", "status": "active"},
    )
    r = await client.get("/conductors", headers=auth_headers, params={"page": 1, "page_size": 50})
    assert r.status_code == 200, r.text
    match = next(i for i in r.json()["items"] if i["badge_no"] == "ENR-BADGE-002")
    assert match["full_name"] == "Connor Enrichment"
