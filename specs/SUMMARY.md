# TransitOS Sprint A — Architect's Summary

This directory contains the four spec files for Sprint A. Together
they form a single, internally consistent source of truth. The
backend and frontend engineers build to them in parallel; the
integration gate verifies they fit together.

## Files

| # | File | One-liner |
|---|------|-----------|
| 1 | [`data-model.md`](./data-model.md) | Pydantic v2 schemas for Branch, User, Vehicle, Driver, Conductor, Route; Mongo collection names, 13+ indexes, soft-delete pattern, and the immutable `audit_log` schema with write-only rules. |
| 2 | [`api-contract.md`](./api-contract.md) | 41 REST endpoints across auth, users, branches, vehicles, drivers, conductors, routes — with request/response shapes, role gates per endpoint, the standard `{items,total,page,totalPages,hasMore}` list shape, and the `{detail,type}` error shape. |
| 3 | [`design-tokens.md`](./design-tokens.md) | Transport-teal + road-amber palette, full type/spacing/radius/shadow scales, 12 component primitives (Button, Input, Card, Field, Select, Modal, Toast, Badge, EmptyState, Spinner, Skeleton, Tabs) with variants, and the `components/ui/` folder layout. |
| 4 | [`sprint-a-tasks.md`](./sprint-a-tasks.md) | Full file tree for `/workspace/transitos/` (backend + frontend), per-screen UX specs (what users see, API calls on mount, mutations, empty-state copy), and the end-to-end auth flow including token storage, redirect rules, and role-based tab visibility. |

## Open decisions made

The blueprint left five decisions ambiguous. I made concrete calls
and documented each one in the spec where it applies. The owner
should review these before the team commits code.

- **10 roles, not 9.** Blueprint §1.2 lists 9 user-facing roles;
  the data model in §4 has 10 (it includes `super_admin`). Sprint A
  ships all 10. `super_admin` is the platform bootstrap role used
  by the seed script and by the Owner-facing system tasks. It has
  every `owner` permission plus system administration. Documented
  in `data-model.md` §0.5 and `api-contract.md` §0.8.

- **Denormalized user fields in Driver/Conductor responses.**
  `DriverResponse` and `ConductorResponse` carry a `full_name`,
  `email`, and `phone` field populated from the linked `User` at
  read time. This avoids an N+1 in the list endpoint and means
  the frontend can render a row with one fetch. Documented in
  `data-model.md` §4–§5.

- **Audit log stores only the diff.** On update, the `before` and
  `after` fields in the audit log contain **only the fields that
  actually changed**, not full entity snapshots. This is
  ~10x cheaper to store and ~10x faster to read. The full record
  is still queryable via the `entity_id` + `ts` index for a
  point-in-time reconstruction. Documented in `data-model.md`
  §7 (Audit log writing rules).

- **In-app password reset, not email flow.** `POST /auth/forgot-password`
  and the public `POST /auth/reset-password` are listed as **stretch
  goals** in `api-contract.md` §1.5–§1.6 (email delivery is Sprint B).
  The Profile screen's "Reset password" button uses a separate
  authenticated endpoint `POST /auth/me/password` that requires
  the **current password** for verification — see `api-contract.md`
  §1.7 and `sprint-a-tasks.md` §4.9. This is the only Sprint A
  addition to the original API surface; the backend engineer must
  implement it.

- **In-memory rate limit; no Redis yet.** Login is rate-limited to
  5 attempts per email per 5 minutes via an in-process dict
  (`app/routers/auth.py`). A Redis-backed version is a Sprint B
  hardening task — Sprint A is single-instance. Documented in
  `data-model.md` §9 and `api-contract.md` §1.1.

## What is NOT in Sprint A (sanity check)

The verifier will fail the spec if it drifts into:
- trips, manifest_entries, fuel_logs, maintenance_records
- expenses, cash_ups (the variance feature), expense_categories
- live ops (WebSocket GPS)
- document/photo uploads
- dark mode
- multi-select pickers, date pickers, charts
- audit log read API (write-only in Sprint A)

These all live in Sprint B/C and the blueprint's §4–§7 references
to them are explicitly excluded from this spec.

## Reading order for the implementers

1. **Backend engineer**: `data-model.md` → `api-contract.md` → `sprint-a-tasks.md` §2 → `design-tokens.md` §0 (just the conventions)
2. **Frontend engineer**: `design-tokens.md` → `sprint-a-tasks.md` §3–§4 → `api-contract.md` §0 + §1 + §0.10 → `data-model.md` §0 (just the conventions)
3. **Integration gate**: this summary, then the four files in any order
