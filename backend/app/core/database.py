"""Async MongoDB client + DB factory + index creation.

The Motor client is a singleton; the ``get_db()`` dependency returns
the application database. Tests override ``get_db`` to swap in
``transitos_test`` and clean state between runs.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.config import settings

logger = logging.getLogger(__name__)


# Singleton client. ``tz_aware=True`` makes BSON datetimes Python
# ``datetime`` objects that carry UTC tzinfo — what the spec wants.
client: AsyncIOMotorClient = AsyncIOMotorClient(
    settings.mongodb_url,
    tz_aware=True,
    uuidRepresentation="standard",
)

# Default DB handle. Tests override via dependency injection.
db: AsyncIOMotorDatabase = client[settings.mongodb_db_name]


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency: returns the active database handle.

    Tests can override this with ``app.dependency_overrides[get_db]``.
    """
    return db


async def create_indexes() -> None:
    """Create every index listed in ``data-model.md`` §1–§7 + §8.

    Idempotent: ``create_index`` is a no-op when the index already exists
    with the same spec.
    """
    # --- branches ---
    await db.branches.create_indexes(
        [
            IndexModel([("code", ASCENDING)], unique=True, name="uniq_code"),
            IndexModel(
                [("is_active", ASCENDING), ("name", ASCENDING)],
                name="is_active_name",
            ),
            IndexModel(
                [("city", ASCENDING), ("state", ASCENDING)], name="city_state"
            ),
            IndexModel([("manager_id", ASCENDING)], name="manager_id"),
        ]
    )

    # --- users ---
    await db.users.create_indexes(
        [
            IndexModel([("email", ASCENDING)], unique=True, name="uniq_email"),
            IndexModel(
                [("is_active", ASCENDING), ("role", ASCENDING)],
                name="is_active_role",
            ),
            IndexModel(
                [("branch_id", ASCENDING), ("role", ASCENDING)],
                name="branch_id_role",
            ),
            IndexModel([("status", ASCENDING)], name="status"),
        ]
    )

    # --- vehicles ---
    await db.vehicles.create_indexes(
        [
            IndexModel(
                [("reg_number", ASCENDING)], unique=True, name="uniq_reg_number"
            ),
            IndexModel(
                [("branch_id", ASCENDING), ("status", ASCENDING)],
                name="branch_id_status",
            ),
            IndexModel(
                [("is_active", ASCENDING), ("type", ASCENDING)],
                name="is_active_type",
            ),
            IndexModel(
                [("documents.expires_at", ASCENDING)], name="docs_expires_at"
            ),
        ]
    )

    # --- drivers ---
    await db.drivers.create_indexes(
        [
            IndexModel([("user_id", ASCENDING)], unique=True, name="uniq_user_id"),
            IndexModel([("license_no", ASCENDING)], name="license_no"),
            IndexModel(
                [("is_active", ASCENDING), ("status", ASCENDING)],
                name="is_active_status",
            ),
            IndexModel([("license_expiry", ASCENDING)], name="license_expiry"),
            IndexModel([("branch_id", ASCENDING)], name="branch_id"),
        ]
    )

    # --- conductors ---
    await db.conductors.create_indexes(
        [
            IndexModel([("user_id", ASCENDING)], unique=True, name="uniq_user_id"),
            IndexModel(
                [("badge_no", ASCENDING)], unique=True, name="uniq_badge_no"
            ),
            IndexModel(
                [("is_active", ASCENDING), ("status", ASCENDING)],
                name="is_active_status",
            ),
            IndexModel([("branch_id", ASCENDING)], name="branch_id"),
        ]
    )

    # --- routes ---
    await db.routes.create_indexes(
        [
            IndexModel(
                [
                    ("branch_id", ASCENDING),
                    ("is_active", ASCENDING),
                    ("name", ASCENDING),
                ],
                name="branch_active_name",
            ),
            IndexModel(
                [
                    ("origin_branch_id", ASCENDING),
                    ("destination_branch_id", ASCENDING),
                ],
                name="origin_dest",
            ),
            IndexModel(
                [("type", ASCENDING), ("is_active", ASCENDING)],
                name="type_active",
            ),
        ]
    )

    # --- audit_log ---
    await db.audit_log.create_indexes(
        [
            IndexModel([("ts", DESCENDING)], name="ts_desc"),
            IndexModel(
                [("actor_id", ASCENDING), ("ts", DESCENDING)],
                name="actor_ts",
            ),
            IndexModel(
                [
                    ("entity_type", ASCENDING),
                    ("entity_id", ASCENDING),
                    ("ts", DESCENDING),
                ],
                name="entity_ts",
            ),
            IndexModel(
                [("action", ASCENDING), ("ts", DESCENDING)],
                name="action_ts",
            ),
        ]
    )

    # --- refresh_tokens ---
    await db.refresh_tokens.create_indexes(
        [
            IndexModel([("jti", ASCENDING)], unique=True, name="uniq_jti"),
            IndexModel(
                [("user_id", ASCENDING), ("revoked", ASCENDING)],
                name="user_revoked",
            ),
            # Supports purge_revoked_refresh_tokens(created_at < cutoff, revoked=True).
            IndexModel(
                [("revoked", ASCENDING), ("created_at", ASCENDING)],
                name="revoked_created",
            ),
            # TTL: MongoDB deletes the document once expires_at is reached.
            IndexModel(
                [("expires_at", ASCENDING)],
                name="ttl_expires_at",
                expireAfterSeconds=0,
            ),
        ]
    )

    # --- password_reset_tokens (separate collection so TTL is safe) ---
    await db.password_reset_tokens.create_indexes(
        [
            IndexModel(
                [("token_hash", ASCENDING)], unique=True, name="uniq_token_hash"
            ),
            IndexModel([("user_id", ASCENDING)], name="user_id"),
            # TTL: expired reset tokens are purged automatically.
            IndexModel(
                [("expires_at", ASCENDING)],
                name="ttl_expires_at",
                expireAfterSeconds=0,
            ),
        ]
    )

    # --- trips ---
    await db.trips.create_indexes(
        [
            IndexModel(
                [("branch_id", ASCENDING), ("scheduled_departure", DESCENDING)],
                name="branch_dep",
            ),
            IndexModel([("vehicle_id", ASCENDING)], name="vehicle"),
            IndexModel([("driver_id", ASCENDING)], name="driver"),
            IndexModel([("conductor_id", ASCENDING)], name="conductor"),
            IndexModel([("status", ASCENDING)], name="status"),
            IndexModel([("route_id", ASCENDING)], name="route"),
        ]
    )

    # --- manifest ---
    await db.manifest.create_indexes(
        [
            IndexModel([("trip_id", ASCENDING)], name="trip"),
            IndexModel(
                [("trip_id", ASCENDING), ("type", ASCENDING)],
                name="trip_type",
            ),
            IndexModel([("payment_status", ASCENDING)], name="payment_status"),
        ]
    )

    # --- cash_ups ---
    await db.cash_ups.create_indexes(
        [
            IndexModel(
                [("trip_id", ASCENDING)], unique=True, sparse=True, name="uniq_trip"
            ),
            IndexModel(
                [("branch_id", ASCENDING), ("created_at", DESCENDING)],
                name="branch_created",
            ),
            IndexModel([("status", ASCENDING)], name="status"),
            IndexModel([("conductor_id", ASCENDING)], name="conductor"),
        ]
    )

    # --- expenses ---
    await db.expenses.create_indexes(
        [
            IndexModel(
                [("branch_id", ASCENDING), ("occurred_at", DESCENDING)],
                name="branch_occurred",
            ),
            IndexModel([("trip_id", ASCENDING)], name="trip"),
            IndexModel([("vehicle_id", ASCENDING)], name="vehicle"),
            IndexModel([("category", ASCENDING)], name="category"),
        ]
    )

    # --- fuel_logs ---
    await db.fuel_logs.create_indexes(
        [
            IndexModel(
                [("vehicle_id", ASCENDING), ("occurred_at", DESCENDING)],
                name="vehicle_occurred",
            ),
            IndexModel(
                [("branch_id", ASCENDING), ("occurred_at", DESCENDING)],
                name="branch_occurred",
            ),
        ]
    )

    # --- maintenance ---
    await db.maintenance.create_indexes(
        [
            IndexModel(
                [("vehicle_id", ASCENDING), ("scheduled_for", ASCENDING)],
                name="vehicle_scheduled",
            ),
            IndexModel(
                [("branch_id", ASCENDING), ("status", ASCENDING)],
                name="branch_status",
            ),
        ]
    )

    # --- push_tokens ---
    await db.push_tokens.create_indexes(
        [
            IndexModel(
                [("user_id", ASCENDING), ("token", ASCENDING)],
                unique=True,
                name="uniq_user_token",
            ),
            IndexModel(
                [("user_id", ASCENDING), ("is_active", ASCENDING)],
                name="user_active",
            ),
        ]
    )

    logger.info("Mongo indexes created (or already existed).")


async def drop_all_collections() -> None:
    """Drop every collection — used by tests for clean teardown."""
    for coll_name in await db.list_collection_names():
        await db.drop_collection(coll_name)


async def close_client() -> None:
    """Close the motor client. Called on FastAPI shutdown."""
    client.close()
