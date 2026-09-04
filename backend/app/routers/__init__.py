"""Routers — one module per resource (Sprint A + Sprint B + Sprint C + admin).

All router modules are imported at package init. If any single module fails
to import (e.g. missing optional dep), the package still loads — the failing
module is logged and excluded from ``__all__``, and the app boots without
those routes. The core routers (auth, branches, etc.) are never optional.
"""

import logging
from typing import Any

# Core routers — these must always be present.
from app.routers import (  # noqa: F401
    auth,
    branches,
    cash_ups,
    conductors,
    drivers,
    expenses,
    fuel,
    maintenance,
    reports,
    routes,
    trips,
    users,
    vehicles,
)


def _try_load_admin() -> Any:
    """Load the admin router module, tolerating import failures.

    We use ``importlib.import_module`` instead of ``from app.routers import admin``
    because the latter fails with ``partially initialized module`` when the
    package is still being initialised (which is exactly the case here, since
    this code runs as part of ``app.routers``'s own ``__init__.py``).
    """
    import importlib
    try:
        return importlib.import_module("app.routers.admin")
    except ImportError as exc:
        logging.getLogger("transitos").warning(
            "admin router not available (POST /admin/seed disabled): %s", exc
        )
        return None


admin = _try_load_admin()
_ADMIN_AVAILABLE = admin is not None


__all__ = [
    "auth",
    "branches",
    "users",
    "vehicles",
    "drivers",
    "conductors",
    "routes",
    "trips",
    "cash_ups",
    "expenses",
    "fuel",
    "maintenance",
    "reports",
]
if _ADMIN_AVAILABLE:
    __all__.append("admin")
