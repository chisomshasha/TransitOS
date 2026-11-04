"""Cross-cutting services."""

from app.services.audit import write_audit
from app.services.auth import (
    assert_refresh_device_match,
    authenticate_user,
    complete_password_reset,
    hash_password,
    issue_token_pair,
    purge_revoked_refresh_tokens,
    revoke_all_user_tokens,
    revoke_refresh_token,
    start_password_reset,
)
from app.services.cash_up import (
    approve_cash_up,
    compute_expected_total,
    reject_cash_up,
    submit_cash_up,
)
from app.services.trips import (
    assert_transition,
    get_branch_id_for,
    get_trip_or_404,
    recompute_trip_totals,
    update_trip_totals,
)

__all__ = [
    "write_audit",
    "authenticate_user",
    "complete_password_reset",
    "hash_password",
    "issue_token_pair",
    "revoke_all_user_tokens",
    "revoke_refresh_token",
    "assert_refresh_device_match",
    "start_password_reset",
    "purge_revoked_refresh_tokens",
    "approve_cash_up",
    "compute_expected_total",
    "reject_cash_up",
    "submit_cash_up",
    "assert_transition",
    "get_branch_id_for",
    "get_trip_or_404",
    "recompute_trip_totals",
    "update_trip_totals",
]
