#!/usr/bin/env python3
"""Contract checks — is the frontend still talking to the backend?

Run from the repo root:

    python tools/contract/check.py              # every check
    python tools/contract/check.py routes       # one check
    python tools/contract/check.py --help

The checks, and what each one catches:

``routes``    Every API call the frontend makes resolves to a live route
              with the right HTTP method. Catches the 404 and the 405.

``params``    Every required query parameter and request-body field the
              backend declares is actually supplied by the frontend.
              Catches the 422.

``rbac``      Every role the frontend lets into a screen can actually use
              that screen's endpoints. Catches the 403 wall.

``screens``   Every screen file has a navigation target that reaches it.
              Catches the dead screen.

Why a separate tool when the pytest suite already exists: the pytest
guards protect the *repository*. This tool is for *you*, while you are
still building — it runs in a second and tells you what you just broke.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("MONGODB_DB_NAME", "contract_check")
os.environ.setdefault("JWT_SECRET_KEY", "contract-check-secret")

from sources import iter_source_files  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
# frontend call scanner
# ══════════════════════════════════════════════════════════════════════════

HELPER_METHOD = {
    "getPage": "GET", "getSingle": "GET",
    "postSingle": "POST", "postAction": "POST", "postNoContent": "POST",
    "postJson": "POST",
    "patchSingle": "PATCH", "patchNoContent": "PATCH", "patchJson": "PATCH",
    "putSingle": "PUT",
    "deleteNoContent": "DELETE", "deleteJson": "DELETE",
}


def _read_template(src: str, start: int):
    """Read a string/template literal, tolerating nested interpolation."""
    quote = src[start]
    i, depth = start + 1, 0
    while i < len(src):
        ch = src[i]
        if ch == "\\":
            i += 2
            continue
        if quote == "`" and ch == "$" and i + 1 < len(src) and src[i + 1] == "{":
            depth += 1
            i += 2
            continue
        if depth and ch == "}":
            depth -= 1
            i += 1
            continue
        if depth == 0 and ch == quote:
            return src[start + 1: i], i + 1
        i += 1
    return None, i


def _strip_comments(src: str) -> str:
    """Blank out comments so doc examples are not read as real calls."""
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if src[i] in "'\"`":
            q = src[i]
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == q:
                    j += 1
                    break
                j += 1
            out.append(src[i:j])
            i = j
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _read_args(src: str, start: int) -> str:
    """The argument text of a call whose arguments begin at ``start``."""
    depth, i, n = 1, start, len(src)
    while i < n:
        ch = src[i]
        if ch in "'\"`":
            _, i = _read_template(src, i)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return src[start:i]
        i += 1
    return src[start:]


def _split_args(text: str) -> list[str]:
    parts, depth, cur, i, n = [], 0, "", 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "'\"`":
            lit, i = _read_template(text, i)
            cur += lit
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
            i += 1
            continue
        cur += ch
        i += 1
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _object_keys(text: str) -> list[str]:
    """Keys of a top-level object literal argument."""
    text = text.strip()
    if not text.startswith("{"):
        return []
    body = text[1:-1] if text.endswith("}") else text[1:]
    members, depth, cur, i, n = [], 0, "", 0, len(body)
    while i < n:
        ch = body[i]
        if ch in "'\"`":
            lit, i = _read_template(body, i)
            cur += lit
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            members.append(cur)
            cur = ""
            i += 1
            continue
        cur += ch
        i += 1
    if cur.strip():
        members.append(cur)

    keys = []
    for m in members:
        m = m.strip()
        if not m or m.startswith("..."):
            continue
        if ":" not in m:
            if re.fullmatch(r"[A-Za-z_$][\w$]*", m):
                keys.append(m)
            continue
        key = m.split(":", 1)[0].strip().strip("'\"`")
        if re.fullmatch(r"[A-Za-z_$][\w$]*", key):
            keys.append(key)
    return keys


def frontend_calls() -> list[dict]:
    """Every distinct API call the frontend makes."""
    helper_re = re.compile(
        r"(?<![.\w])(" + "|".join(HELPER_METHOD) + r")\s*(?:<[^()]*?>)?\s*\(\s*")
    api_re = re.compile(
        r"\bapi\s*\.\s*(get|post|patch|put|delete)\s*(?:<[^()]*?>)?\s*\(\s*")

    found: dict[tuple[str, str], dict] = {}
    for p in iter_source_files(FRONTEND):
        if p.name == "api.ts":
            continue
        src = _strip_comments(p.read_text(encoding="utf-8"))
        rel = str(p.relative_to(REPO))

        for m in helper_re.finditer(src):
            raw, after = _read_template(src, m.end())
            if raw is None:
                continue
            args = _split_args(_read_args(src, after))
            helper = m.group(1)
            if helper in ("getPage", "getSingle"):
                # (path, params)
                params = _object_keys(args[1]) if len(args) > 1 else []
                body = []
            else:
                # (path, body, params)
                body = _object_keys(args[1]) if len(args) > 1 else []
                params = _object_keys(args[2]) if len(args) > 2 else []
            key = (HELPER_METHOD[helper], _norm(raw))
            entry = found.setdefault(key, {
                "method": HELPER_METHOD[helper], "path": _norm(raw),
                "raw": raw, "params": params, "body": body, "src": rel,
                "symbol": _enclosing_symbol(src, m.start()), "sites": [],
            })
            entry["sites"].append({
                "src": rel,
                "symbol": _enclosing_symbol(src, m.start()),
            })

        for m in api_re.finditer(src):
            raw, after = _read_template(src, m.end())
            if raw is None:
                continue
            args = _split_args(_read_args(src, after))
            method = m.group(1).upper()
            params = _object_keys(args[1]) if len(args) > 1 else []
            body = [] if method == "GET" else (
                _object_keys(args[1]) if len(args) > 1 else [])
            key = (method, _norm(raw))
            entry = found.setdefault(key, {
                "method": method, "path": _norm(raw), "raw": raw,
                "params": params, "body": body, "src": rel,
                "symbol": _enclosing_symbol(src, m.start()), "sites": [],
            })
            entry["sites"].append({
                "src": rel,
                "symbol": _enclosing_symbol(src, m.start()),
            })

    return sorted(found.values(), key=lambda c: (c["method"], c["path"]))



def _enclosing_symbol(src: str, index: int) -> str:
    """The exported function or const that contains ``index``.

    API calls usually live in a shared hook (``lib/queries.ts``) rather
    than in the screen that uses it, so the screen cannot be found from
    the call's own file. The symbol name is the bridge: a screen that
    calls ``useFuelLogs(...)`` is a screen that calls ``GET /fuel-logs``.
    """
    head = src[:index]
    # Nearest preceding "export function NAME" / "export const NAME".
    matches = list(re.finditer(
        r"export\s+(?:default\s+)?(?:async\s+)?(?:function|const)\s+([A-Za-z_$][\w$]*)",
        head,
    ))
    if not matches:
        matches = list(re.finditer(
            r"(?:function|const)\s+([A-Za-z_$][\w$]*)\s*[=(:]",
            head,
        ))
    return matches[-1].group(1) if matches else ""


def _symbol_to_screens() -> dict[str, set[str]]:
    """hook/function name -> the screen files that can reach it.

    The lookup follows the **import closure** and distinguishes a
    *definition* from a *use*. A hook that lives in ``lib/queries.ts``
    and is used by ``components/TripStatusPanel.tsx`` belongs to every
    screen that renders that component — the trip detail screen in this
    case. Without the closure, a mutation owned by a component would
    look unreachable, and the RBAC check would skip it entirely.

    Without the definition/use distinction the map would be useless in
    the other direction: ``lib/queries.ts`` mentions every hook it
    defines, so it would look as if every screen used every hook.
    """
    out: dict[str, set[str]] = {}
    defines: dict[str, set[str]] = {}
    sources: dict[str, str] = {}
    for path in iter_source_files(FRONTEND):
        rel = str(path.relative_to(FRONTEND))
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        sources[rel] = src
        defines.setdefault(rel, set()).update(_defined_symbols(src))

    for screen, files in _screen_closures().items():
        # Paths are kept repo-relative so that every screen path starts
        # with ``frontend/app/`` — the RBAC check looks for that prefix.
        screen_rel = str((FRONTEND / screen).relative_to(REPO))
        for rel in files:
            src = sources.get(rel)
            if src is None:
                continue
            here = defines.get(rel, set())
            for name in set(re.findall(r"\b(use[A-Z][\w$]*)\b", src)):
                if name in here:
                    continue  # this file defines it — that is not a use
                out.setdefault(name, set()).add(screen_rel)
    return out


def _defined_symbols(src: str) -> set[str]:
    """The names a file declares."""
    stripped = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    stripped = re.sub(r"//[^\n]*", "", stripped)
    return set(re.findall(
        r"(?:export\s+(?:default\s+)?)?(?:async\s+)?"
        r"(?:function|const|let|var|class)\s+([A-Za-z_$][\w$]*)",
        stripped,
    ))


def _import_graph() -> dict[str, set[str]]:
    """file -> the files it imports (relative to the frontend root)."""
    from payloads import _resolve_import  # noqa: PLC0415

    edges: dict[str, set[str]] = {}
    for path in iter_source_files(FRONTEND):
        rel = str(path.relative_to(FRONTEND))
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        targets: set[str] = set()
        for spec in re.findall(r"""(?:from|import)\s+['"]([^'"]+)['"]""", src):
            resolved = _resolve_import(spec, rel)
            if resolved:
                targets.add(resolved)
        edges[rel] = targets
    return edges


def _screen_closures() -> dict[str, set[str]]:
    """screen file -> every file it can reach, following imports."""
    edges = _import_graph()
    roots = sorted(rel for rel in edges if rel.startswith("app/"))
    out: dict[str, set[str]] = {}
    for root in roots:
        seen: set[str] = set()
        stack = [root]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(edges.get(current, ()))
        out[root] = seen
    return out


def _resolve_frontend_path(rel: str) -> pathlib.Path | None:
    """Resolve a source path given relative to the repo *or* the frontend."""
    for base in (REPO, FRONTEND):
        candidate = base / rel
        if candidate.exists():
            return candidate
    return None


def _role_constants() -> dict[str, list[str]]:
    """Every ``NAME: Role[] = [...]`` constant in the frontend."""
    out: dict[str, list[str]] = {}
    for path in iter_source_files(FRONTEND / "lib"):
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for name, body in re.findall(
            r"export\s+const\s+([A-Z][A-Z0-9_]*)\s*:\s*(?:readonly\s+)?Role\[\]\s*=\s*\[([^\]]*)\]",
            src,
        ):
            roles = re.findall(r"'([a-z_]+)'", body)
            if roles:
                out[name] = roles
    return out


def _endpoint_guards() -> dict[tuple[str, str], list[str]]:
    """(method, path) -> the role list the UI guards it with.

    Read from ``ENDPOINT_GUARDS`` in ``frontend/lib/rbac.ts``. The table
    is the one place that says "this action is offered to these roles",
    so the checker does not have to guess which of a screen's role lists
    belongs to which endpoint.
    """
    path = FRONTEND / "lib" / "rbac.ts"
    if not path.exists():
        return {}
    src = path.read_text(encoding="utf-8")
    block = re.search(r"ENDPOINT_GUARDS[^=]*=\s*\[(.*?)\n\];", src, re.S)
    if not block:
        return {}
    constants = _role_constants()
    out: dict[tuple[str, str], list[str]] = {}
    for method, ep_path, roles_name in re.findall(
        r"\{\s*method:\s*'([A-Z]+)'\s*,\s*path:\s*'([^']+)'\s*,\s*roles:\s*([A-Z][A-Z0-9_]*)\s*\}",
        block.group(1),
    ):
        roles = constants.get(roles_name)
        if roles:
            out[(method, _norm(ep_path))] = roles
    return out



def _screen_role_guards(screen_file: str) -> list[list[str]]:
    """Role allow-lists a screen declares for its own actions.

    A screen often hides an action from roles that may not use it, e.g.::

        const CASHUP_APPROVE_ROLES: Role[] = ['super_admin', 'owner', ...];
        const canApprove = canAccess(user?.role, CASHUP_APPROVE_ROLES);

    When that is present, the backend's role list is not the only
    constraint — the UI already withholds the action. Without knowing
    this, the checker reports every guarded action as a mismatch.

    The list may be declared locally *or* imported from a shared module
    (``@/lib/rbac``), so an imported constant is resolved back to its
    declaration. Every guard the screen declares is returned; the caller
    decides which one belongs to which endpoint (see
    ``_endpoint_guards``).
    """
    path = _resolve_frontend_path(screen_file)
    if path is None:
        return []
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return []
    constants = _role_constants()
    out: list[list[str]] = []
    for name, body in re.findall(
        r"const\s+([A-Z][A-Z0-9_]*_ROLES)\s*:\s*(?:readonly\s+)?Role\[\]\s*=\s*\[([^\]]*)\]",
        src,
    ):
        roles = re.findall(r"'([a-z_]+)'", body)
        if roles:
            out.append(roles)
            continue
        # Imported from a shared module — resolve the constant there.
        imported = constants.get(name)
        if imported and re.search(rf"canAccess\([^)]*,\s*{re.escape(name)}\s*\)", src):
            out.append(imported)
    return out

def _screens_for_call(call: dict, symbol_map: dict[str, set[str]]) -> set[str]:
    """Which screens can reach this API call.

    A call made directly inside a screen file belongs to that screen. A
    call made inside a shared hook belongs to every screen that uses the
    hook. A path may be called from several places, so every call site
    is considered and the results are unioned.
    """
    screens: set[str] = set()
    sites = call.get("sites") or [
        {"src": call.get("src", ""), "symbol": call.get("symbol", "")}
    ]
    for site in sites:
        src = site.get("src", "")
        if "/app/" in src:
            screens.add(src)
        symbol = site.get("symbol") or ""
        if symbol:
            for user in symbol_map.get(symbol, set()):
                if "/app/" in user:
                    screens.add(user)
    return screens

def _norm(path: str) -> str:
    path = re.sub(r"\$\{[^}]*\}", "{}", path)
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return path.split("?")[0].rstrip("/") or "/"


# ══════════════════════════════════════════════════════════════════════════
# backend inventory
# ══════════════════════════════════════════════════════════════════════════

def openapi_ops() -> list[dict]:
    from app.main import app

    spec = app.openapi()
    ops = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method.lower() not in ("get", "post", "patch", "put", "delete"):
                continue
            params = [p["name"] for p in (op.get("parameters") or [])
                      if p.get("required") and p.get("in") == "query"]
            body = []
            body_props = []
            rb = op.get("requestBody") or {}
            if rb.get("content", {}).get("application/json"):
                sch = rb["content"]["application/json"].get("schema", {})
                if "$ref" in sch:
                    sch = spec["components"]["schemas"][sch["$ref"].split("/")[-1]]
                body = sch.get("required", []) or []
                body_props = list((sch.get("properties") or {}).keys())
            ops.append({
                "method": method.upper(), "path": path,
                "tag": (op.get("tags") or ["-"])[0],
                "query": params, "body": body, "body_props": body_props,
            })
    return ops


def _balanced(src: str, open_at: int) -> str:
    depth, i, n = 0, open_at, len(src)
    while i < n:
        ch = src[i]
        if ch in "\"'":
            q = ch
            i += 1
            while i < n and src[i] != q:
                i += 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return src[open_at + 1: i]
        i += 1
    return src[open_at + 1:]


def endpoint_roles() -> dict:
    """(METHOD, path) -> {'roles': [...], 'access': 'public|session|restricted'}."""
    from app.core.roles import (
        ANY_AUTHENTICATED, CREW_READ, FLEET_OPS, READ_ALL, SAFETY_OPS,
        USERS_READ, Role,
    )

    aliases = {
        "SA": "super_admin", "OWNER": "owner", "GM": "general_manager",
        "BM": "branch_manager", "OM": "operations_manager",
        "FM": "fleet_manager", "CA": "chief_accountant",
        "BA": "branch_accountant", "DRIVER": "driver", "CONDUCTOR": "conductor",
    }
    groups = {
        "ANY_AUTHENTICATED": [r.value for r in ANY_AUTHENTICATED],
        "READ_ALL": [r.value for r in READ_ALL],
        "FLEET_OPS": [r.value for r in FLEET_OPS],
        "CREW_READ": [r.value for r in CREW_READ],
        "SAFETY_OPS": [r.value for r in SAFETY_OPS],
        "USERS_READ": [r.value for r in USERS_READ],
        "REPORTS_READ": ["super_admin", "owner", "general_manager",
                         "chief_accountant", "branch_accountant",
                         "branch_manager", "operations_manager", "fleet_manager"],
    }

    out = {}
    for path in sorted((BACKEND / "app" / "routers").glob("*.py")):
        src = path.read_text(encoding="utf-8")

        local = {}
        for m in re.finditer(r"^([A-Z][A-Z_0-9]*)\s*=\s*([^\n]+)$", src, re.M):
            name, body = m.group(1), m.group(2).strip()
            if body.startswith("["):
                roles = []
                for part in body.strip("[]").split(","):
                    part = part.strip().lstrip("*").strip()
                    if part in aliases:
                        roles.append(aliases[part])
                    elif part.startswith("Role."):
                        roles.append(part.split(".", 1)[1].lower())
                    elif part in groups:
                        roles.extend(groups[part])
                if roles:
                    local[name] = sorted(set(roles))
            elif body in groups:
                local[name] = list(groups[body])
            elif body in aliases:
                local[name] = [aliases[body]]

        prefixes = {}
        for var, pre in re.findall(
            r"(\w+)\s*=\s*APIRouter\([^)]*?prefix\s*=\s*[\"']([^\"']+)[\"']", src, re.S
        ):
            prefixes.setdefault(var, pre)

        for m in re.finditer(
            r"@(\w+)\.(get|post|patch|put|delete)\(\s*[\"']([^\"']*)[\"'][^)]*\)\s*\n"
            r"(?:@[\w.]+(?:\([^\n]*\))?\s*\n)*"
            r"(?:async\s+)?def\s+\w+\s*\(",
            src, re.S,
        ):
            var, method, sub = m.groups()
            if var not in prefixes:
                continue
            sig = _balanced(src, m.end() - 1)
            rm = re.search(r"require_roles\(([^)]*)\)", sig)
            roles = []
            if rm:
                for part in rm.group(1).split(","):
                    part = part.strip().lstrip("*").strip()
                    if part in local:
                        roles.extend(local[part])
                    elif part in groups:
                        roles.extend(groups[part])
                    elif part in aliases:
                        roles.append(aliases[part])
                roles = sorted(set(roles))
            full = (prefixes[var] + sub).rstrip("/") or "/"
            if rm is None and "get_current_user" not in sig:
                access = "public"
            elif roles:
                access = "restricted"
            else:
                access = "session"
            out[(method.upper(), full)] = {"roles": roles, "access": access}

    return out


def screen_routes() -> dict:
    """route -> file, for every expo-router screen."""
    app_dir = FRONTEND / "app"
    routes = {}
    for p in iter_source_files(app_dir, ("*.tsx",)):
        if p.name == "_layout.tsx":
            continue
        rel = str(p.relative_to(app_dir))[:-4]
        if rel.startswith("("):
            rel = rel[rel.index(")") + 1:]
        route = "/" + rel.replace("/index", "").strip("/")
        route = re.sub(r"//+", "/", route).rstrip("/") or "/"
        routes[route] = str(p.relative_to(REPO))
    return routes


def navigation_targets() -> set[str]:
    """Every route the frontend links to."""
    targets = set()
    for p in iter_source_files(FRONTEND):
        src = p.read_text(encoding="utf-8")
        for m in re.finditer(r"router\.push\(\s*[`'\"]([^`'\"]*)[`'\"]", src):
            targets.add(m.group(1))
        for m in re.finditer(r"href:\s*[`'\"]([^`'\"]*)[`'\"]", src):
            targets.add(m.group(1))
        for m in re.finditer(r"router\.(?:replace|navigate)\(\s*[`'\"]([^`'\"]*)[`'\"]", src):
            targets.add(m.group(1))
    return targets


# ══════════════════════════════════════════════════════════════════════════
# checks
# ══════════════════════════════════════════════════════════════════════════

#: Paths whose trailing segment is a runtime variable.
DYNAMIC_SUFFIX = {
    "/settlements/{}/{}": ["submit", "approve", "reject", "pay"],
    "/incidents/{}/{}": ["resolve"],
    "/vehicle-transfers/{}/{}": ["cancel", "confirm", "return"],
}


def check_routes(ops, calls, roles):
    problems = []
    by_path: dict[str, set[str]] = {}
    for op in ops:
        by_path.setdefault(_norm(op["path"]), set()).add(op["method"])

    for c in calls:
        key = (c["method"], c["path"])
        if key in [(o["method"], _norm(o["path"])) for o in ops]:
            continue
        if c["path"] in DYNAMIC_SUFFIX:
            verbs = DYNAMIC_SUFFIX[c["path"]]
            head = c["path"][: c["path"].rfind("{}")]
            missing = [v for v in verbs if c["method"] not in by_path.get(head + v, set())]
            if missing:
                problems.append(
                    f"{c['method']} {c['path']} -> no backend route for action(s) {missing}")
            continue
        methods = by_path.get(c["path"])
        if methods is None:
            problems.append(f"{c['method']} {c['path']} -> no such route (404)")
        else:
            problems.append(
                f"{c['method']} {c['path']} -> route exists but only for {sorted(methods)} (405)")
    return problems


def check_params(ops, calls, roles=None):
    problems = []
    required: dict[tuple[str, str], dict] = {}
    for op in ops:
        required[(op["method"], _norm(op["path"]))] = op

    for c in calls:
        op = required.get((c["method"], c["path"]))
        if op is None:
            continue
        sent_params = set(c["params"])
        for p in op["query"]:
            if p not in sent_params:
                problems.append(
                    f"{c['method']} {c['path']} -> required query parameter ?{p} is never sent")
        # Body fields are only knowable when the frontend sends a literal
        # object. When it passes a variable, the check cannot see the
        # keys and must stay silent rather than guess.
        if c["body"]:
            sent_body = set(c["body"])
            for f in op["body"]:
                if f not in sent_body:
                    problems.append(
                        f"{c['method']} {c['path']} -> required body field '{f}' is not sent")
    return problems


def check_guards(ops, calls, roles):
    """The endpoint→guard table must agree with the backend.

    ``frontend/lib/rbac.ts`` declares, for every role-gated action, the
    roles the app offers it to. Two things have to hold:

    * the table must not grant an action to a role the backend refuses
      it to — that would be a UI that offers a button that always 403s;
    * every endpoint in the table must exist and actually be called, so
      the table cannot rot into a list of stale promises.
    """
    problems: list[str] = []
    guards = _endpoint_guards()
    if not guards:
        problems.append(
            "ENDPOINT_GUARDS is missing from frontend/lib/rbac.ts — the role-gated "
            "actions have no declared owner"
        )
        return problems

    known = {(o["method"], _norm(o["path"])) for o in ops}
    called = {(c["method"], c["path"]) for c in calls}
    by_norm = {
        (o["method"], _norm(o["path"])): roles.get((o["method"], o["path"]))
        for o in ops
    }

    for (method, path), guard_roles in sorted(guards.items()):
        if (method, path) not in known:
            problems.append(
                f"ENDPOINT_GUARDS declares {method} {path}, which is not a backend route"
            )
            continue
        if (method, path) not in called:
            problems.append(
                f"ENDPOINT_GUARDS declares {method} {path}, but no screen calls it"
            )
        info = by_norm.get((method, path))
        if not info:
            continue
        allowed = set(info["roles"])
        extra = sorted(set(guard_roles) - allowed)
        if extra:
            problems.append(
                f"ENDPOINT_GUARDS offers {method} {path} to {extra}, but the backend "
                f"allows only {sorted(allowed)}"
            )
    return problems


def check_rbac(ops, calls, roles):
    """A role the frontend admits to a screen must be able to use it."""
    problems = []
    screen_roles = _screen_gates()
    by_path: dict[tuple[str, str], dict] = {
        (o["method"], _norm(o["path"])): roles.get((o["method"], o["path"]))
        for o in ops
    }
    endpoint_guards = _endpoint_guards()

    symbol_map = _symbol_to_screens()

    for c in calls:
        info = by_path.get((c["method"], c["path"]))
        if not info or info["access"] != "restricted":
            continue
        allowed = set(info["roles"])
        # Which screens can reach this call? Direct calls belong to their
        # own screen; calls inside a shared hook belong to every screen
        # that uses that hook.
        screens = _screens_for_call(c, symbol_map)
        if not screens:
            continue
        for prefix, gate_roles in screen_roles:
            hit = [f for f in screens
                   if f.endswith(f"{prefix}.tsx") or f"/{prefix}/" in f]
            if not hit:
                continue
            # A mutation may be guarded in the UI by its own role list;
            # in that case the UI's list is the effective constraint.
            effective = list(gate_roles)
            if c["method"] != "GET":
                # The explicit table wins: it says which role list
                # guards *this* endpoint, which is the only way to
                # resolve a screen that hosts several guarded actions.
                table = endpoint_guards.get((c["method"], c["path"]))
                if table:
                    effective = table
                else:
                    guards = [g for f in hit for g in _screen_role_guards(f)]
                    if len(guards) == 1:
                        effective = guards[0]
            for r in effective:
                if r not in allowed:
                    problems.append(
                        f"role '{r}' may open {prefix} but "
                        f"{c['method']} {c['path']} allows only {sorted(allowed)}")
            break
    return problems


def _screen_gates() -> list[tuple[str, list[str]]]:
    """[(screen name, roles allowed)] from lib/rbac.ts."""
    path = FRONTEND / "lib" / "rbac.ts"
    if not path.exists():
        return []
    src = path.read_text(encoding="utf-8")
    block = re.search(r"SCREEN_ACCESS[^=]*=\s*\[(.*?)\n\];", src, re.S)
    if not block:
        return []
    out = []
    for m in re.finditer(r"prefix:\s*'([^']+)',\s*roles:\s*\[(.*?)\]", block.group(1), re.S):
        roles = re.findall(r"'([a-z_]+)'", m.group(2))
        if not roles and "ALL_ROLES" in m.group(2):
            roles = [r.value for r in __import__(
                "app.core.roles", fromlist=["Role"]).Role]
        out.append((m.group(1), roles))
    return out


#: Screens that are entered from outside the app rather than by tapping
#: through the navigation graph:
#:
#: * ``/login``            — the app's entry point (app/index.tsx redirects here)
#: * ``/forgot-password``  — linked from the login screen
#: * ``/forgot-username``  — linked from the login screen
#: * ``/reset-password``   — linked from the password-reset **email**
#:                           (backend/app/services/auth.py builds the URL)
EXTERNAL_ENTRY_ROUTES = (
    "/login",
    "/forgot-password",
    "/forgot-username",
    "/reset-password",
)


def check_screens():
    problems = []
    routes = screen_routes()
    targets = navigation_targets()
    normalised = set()
    for t in targets:
        base = t.split("?")[0]
        base = re.sub(r"\$\{[^}]*\}", "*", base)
        normalised.add(base.rstrip("/") or "/")

    for route, src in sorted(routes.items()):
        base = route[:-6] if route.endswith("/index") else route
        ok = False
        for t in normalised:
            if t == base or t.rstrip("/") == base.rstrip("/"):
                ok = True
                break
            if "*" in t:
                pat = re.escape(t).replace(r"\*", "[^/]+")
                if re.fullmatch(pat, base):
                    ok = True
                    break
        if not ok and base not in EXTERNAL_ENTRY_ROUTES:
            problems.append(f"no navigation target reaches {route}  ({src})")
    return problems


# ══════════════════════════════════════════════════════════════════════════

def check_fields(ops, calls, roles=None):
    """The body fields the front end sends must match the backend's schema.

    Two ways to be wrong, and both matter:

    * a **required** field the front end never sends -> the request is
      refused with 422 and the screen shows an error;
    * a field the front end sends that the backend does not declare ->
      the Pydantic models do not forbid unknown fields, so the value is
      **silently dropped**. The record is saved without it.

    The body the front end sends is resolved the way the application
    assembles it (hook -> mutation variable -> mutate() argument) by
    ``tools/contract/payloads.py``. Without that, 51 of the 60 mutating
    calls could not be checked at all.
    """
    from payloads import scan_frontend_payloads

    problems: list[str] = []
    by_key = {(o["method"], _norm(o["path"])): o for o in ops}

    payloads = scan_frontend_payloads()
    # One (method, path) can appear in several places; a resolved
    # payload wins over an unresolved one.
    best: dict[tuple[str, str], dict] = {}
    for p in payloads:
        key = p.key
        current = best.get(key)
        if current is None or (p.resolved and not current["resolved"]):
            best[key] = {
                "resolved": p.resolved,
                "keys": set(p.keys),
                "src": p.src,
                "symbol": p.symbol,
                "reason": p.reason,
                "no_body": p.no_body,
            }

    for (method, path), info in sorted(best.items()):
        if not info["resolved"] or info.get("no_body"):
            continue
        op = by_key.get((method, path))
        if op is None:
            continue
        sent = info["keys"]
        required = set(op.get("body") or [])
        known = set(op.get("body_props") or [])

        for field in sorted(required - sent):
            problems.append(
                f"{method} {path} -> required body field '{field}' is never sent "
                f"(by {info['src']}, {info['symbol']})"
            )
        if known:
            for field in sorted(sent - known):
                problems.append(
                    f"{method} {path} -> body field '{field}' is not declared by the "
                    f"backend and will be silently dropped "
                    f"(by {info['src']}, {info['symbol']})"
                )
    return problems


def check_reachable(ops, calls, roles=None):
    """Every endpoint the front end defines must be reachable from a screen.

    A hook that no screen ever calls is a feature that is not in the
    app. Four of them — advancing a trip's status, adding a manifest
    entry, removing one and submitting a cash-up — sit in the middle of
    the money loop: without them no trip can reach ``closed``, no
    manifest can be filled, so no cash-up can be raised, so nothing can
    ever be approved. Every static check passes for a feature that no
    user can reach.

    A call counts as reachable when it is made directly by a screen or
    a component, or when it lives in a function that a screen or a
    component calls.

    ``KNOWN_UNREACHABLE`` is the baseline: the endpoints that are
    already known to be unreachable are listed there with the reason.
    They stay visible, and any *new* unreachable endpoint fails the
    build.
    """
    from payloads import reachable_files, reachable_symbols, scan_frontend_payloads

    problems: list[str] = []

    # Files a user can reach (the screens, plus everything they import,
    # transitively) and the identifiers those files mention.
    files = reachable_files()
    symbols = reachable_symbols()

    # An endpoint is unreachable only when *none* of its call sites is
    # reachable — the front end often offers the same endpoint both
    # through a hook and directly from a screen.
    unreachable: dict[tuple[str, str], set[str]] = {}
    reachable_keys: set[tuple[str, str]] = set()

    for p in scan_frontend_payloads():
        in_screen = p.src.startswith(("app/", "components/", "stores/"))
        if in_screen:
            # A call written in a screen or a component is reachable.
            reachable_keys.add(p.key)
            continue
        # A call in lib/ belongs to a function. It is reachable when some
        # *other* reachable file mentions that function — otherwise the
        # function is defined but never used, and the endpoint it
        # reaches is not in the app.
        used_elsewhere = any(
            rel != p.src and p.symbol and p.symbol in mentioned
            for rel, mentioned in _mentions_by_file(files).items()
        )
        if p.symbol and p.symbol in symbols and used_elsewhere:
            reachable_keys.add(p.key)
        else:
            unreachable.setdefault(p.key, set()).add(p.symbol)

    for (method, path), owners in sorted(unreachable.items()):
        if (method, path) in reachable_keys:
            continue
        if (method, path) in KNOWN_UNREACHABLE:
            continue
        where = ", ".join(sorted(s for s in owners if s)) or "an unknown function"
        problems.append(
            f"{method} {path} is never called from a screen — it is defined in "
            f"{where}, which no reachable file uses, so the feature is unreachable"
        )
    return problems


# Endpoints the front end defines but no screen can reach. Each one is a
# gap in the app, recorded here so the guard below fails on any *new*
# one. Remove an entry as soon as the screen that uses it lands.
KNOWN_UNREACHABLE: dict[tuple[str, str], str] = {
    # ── single-record reads the screens do not use (they list and filter locally) ──
    ("GET", "/branches/{}"): "branch detail screens use the list endpoint",
    ("GET", "/cash-ups/{}"): "cash-up detail screens use the list endpoint",
    ("GET", "/conductors/{}"): "conductor detail screens use the list endpoint",
    ("GET", "/drivers/{}"): "driver detail screens use the list endpoint",
    ("GET", "/routes/{}"): "route detail screens use the list endpoint",
    ("GET", "/users/{}"): "user detail screens use the list endpoint",
    ("GET", "/vehicles/{}"): "vehicle detail screens use the list endpoint",
    ("GET", "/role-permissions/{}"): "the matrix screen loads every role at once",
    # ── reports and analytics the screens do not surface yet ──
    ("GET", "/fuel-logs/vehicle/{}/efficiency"): "no efficiency screen",
    ("GET", "/maintenance/vehicle/{}/upcoming"): "no upcoming-maintenance screen",
    ("GET", "/qr/generate/{}/{}"): "the scan screen reads QR codes, it does not mint them",
    ("GET", "/reports/branches/performance"): "not surfaced in the reports screen",
    ("GET", "/reports/operations/daily"): "not surfaced in the reports screen",
    ("GET", "/reports/vehicles/roi"): "not surfaced in the reports screen",
    ("GET", "/vehicle-documents/expiring"): "not surfaced in the notifications screen",
    # ── admin/maintenance actions without a screen ──
    ("POST", "/alerts/scan"): "the background worker scans on a timer; the manual trigger has no screen",
    ("PATCH", "/vehicles/{}/documents/{}"): "no vehicle-document edit screen",
}


def _mentions_by_file(files: set[str]) -> dict[str, set[str]]:
    """The identifiers mentioned by each reachable file."""
    out: dict[str, set[str]] = {}
    for sub in ("app", "components", "stores", "lib"):
        base = FRONTEND / sub
        if not base.exists():
            continue
        for path in iter_source_files(base):
            rel = str(path.relative_to(FRONTEND))
            if rel not in files:
                continue
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            out[rel] = set(re.findall(r"\b[A-Za-z_$][\w$]*\b", src))
    return out


def check_webview(ops=None, calls=None, roles=None):
    """The map WebViews must escape everything they interpolate.

    The two map screens build an HTML document as a string and hand it
    to a ``react-native-webview``. That document has two injection
    points:

    * a value interpolated into the ``<script>`` block can close the tag
      (``</script>``) — ``JSON.stringify`` does not escape ``<``;
    * a value interpolated into a Leaflet popup is HTML — a driver's
      name or a branch's name is free text.

    Both are stored XSS: the WebView runs JavaScript, has network
    access and can talk back to the app through
    ``window.ReactNativeWebView.postMessage``.

    The fix is ``jsonForScript()`` for the JSON and ``esc()`` for the
    HTML (see ``frontend/lib/html.ts``). This check stops the pattern
    coming back.
    """
    problems: list[str] = []

    for sub in ("app", "components"):
        base = FRONTEND / sub
        if not base.exists():
            continue
        for path in iter_source_files(base):
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "<WebView" not in src:
                continue
            rel = str(path.relative_to(REPO))

            # 1. JSON interpolated into the HTML must be script-safe.
            #    Find the HTML template literal, then look for any
            #    JSON.stringify() *outside* it — inside the template
            #    the JSON is already a variable, so the call that
            #    built it is what matters.
            tmpl_start = tmpl_end = -1
            doctype = src.find("<!DOCTYPE html>")
            if doctype != -1:
                start = src.rfind("`", 0, doctype)
                end = src.find("`", doctype)
                if start != -1 and end != -1:
                    tmpl_start, tmpl_end = start, end

            for m in re.finditer(r"JSON\.stringify\(", src):
                if tmpl_start != -1 and tmpl_start < m.start() < tmpl_end:
                    continue  # inside the WebView's own script
                line = src[: m.start()].count("\n") + 1
                problems.append(
                    f"{rel}:{line} — JSON.stringify() feeds the WebView HTML; use "
                    f"jsonForScript() so a value cannot close the <script> tag"
                )

            # 2. Anything rendered as HTML must be escaped.
            for m in re.finditer(r"bindPopup\(", src):
                tail = src[m.end():]
                depth, i = 1, 0
                while i < len(tail) and depth:
                    if tail[i] == "(":
                        depth += 1
                    elif tail[i] == ")":
                        depth -= 1
                    i += 1
                arg = tail[:i]
                if re.search(r"\.(label|description|title|name)\b", arg) and "esc(" not in arg:
                    line = src[: m.start()].count("\n") + 1
                    problems.append(
                        f"{rel}:{line} — bindPopup() renders a value as HTML without "
                        f"escaping it; wrap it in esc()"
                    )
    return problems


def check_url(ops=None, calls=None, roles=None):
    """The backend base URL must be resolved in exactly one place.

    The app used to resolve it twice: ``lib/api.ts`` (for every axios
    call) and ``lib/auth-context.tsx`` (for the two bare ``fetch`` calls
    to ``/auth/login`` and ``/auth/refresh``). The two resolvers had the
    precedence in opposite orders — ``EXPO_PUBLIC_API_URL`` first in one,
    ``extra.apiUrl`` first in the other.

    That matters exactly when you use EAS build profiles to point at
    different backends: login would have gone to ``app.json``'s URL
    while every other request went to the profile's URL, so the app
    would authenticate against one backend and call another.

    ``lib/api.ts`` now owns the resolution and everything else imports
    it. This check stops a second copy appearing.
    """
    problems: list[str] = []
    owner = "lib/api.ts"

    for sub in ("app", "components", "lib", "stores"):
        base = FRONTEND / sub
        if not base.exists():
            continue
        for path in iter_source_files(base):
            rel_to_api = path.relative_to(FRONTEND).as_posix()
            if rel_to_api == owner:
                continue
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            # Ignore comments — the docs legitimately explain the chain.
            code = _strip_comments(src)
            hits = [
                token
                for token in ("extra.apiUrl", "EXPO_PUBLIC_API_URL")
                if token in code
            ]
            if hits:
                rel = str(path.relative_to(REPO))
                problems.append(
                    f"{rel} — resolves the backend URL itself ({', '.join(hits)}); "
                    f"import resolveBaseURL() from {owner} instead so there is one "
                    f"source of truth"
                )
    return problems


#: Where ``DEFAULT_PERMISSIONS`` promises access the API does not grant.
#:
#: The matrix is **display-only** — it seeds the ``role_permissions``
#: collection, which the admin screen edits, but no route ever consults
#: it. The API enforces access with hard-coded ``require_roles(...)``
#: lists, and the front end gates screens with ``lib/rbac.ts``. Those
#: two agree with each other; the matrix is the odd one out.
#:
#: Aligning the matrix with the API would be the conservative fix (it
#: only removes promises — it grants nobody anything), but it changes
#: what an administrator sees, so it is a product decision rather than
#: a bug fix. Until then the drift is frozen here: any **new**
#: divergence fails the build.
KNOWN_MATRIX_DRIFT: set[tuple[str, str]] = {
    ("chief_accountant", "vehicles"),
    ("branch_accountant", "vehicles"),
    ("driver", "vehicles"),
    ("conductor", "vehicles"),
    ("chief_accountant", "drivers"),
    ("branch_accountant", "drivers"),
    ("chief_accountant", "conductors"),
    ("branch_accountant", "conductors"),
    ("driver", "routes"),
    ("conductor", "routes"),
    ("operations_manager", "fuel"),
    ("driver", "fuel"),
    ("operations_manager", "maintenance"),
    ("driver", "maintenance"),
    ("operations_manager", "cash_ups"),
    ("fleet_manager", "cash_ups"),
    ("branch_manager", "audit_log"),
    ("operations_manager", "audit_log"),
    ("chief_accountant", "incidents"),
    ("branch_accountant", "incidents"),
    ("driver", "incidents"),
    ("conductor", "incidents"),
    ("chief_accountant", "inspections"),
    ("branch_accountant", "inspections"),
    ("conductor", "inspections"),
}


def check_matrix(ops=None, calls=None, roles=None):
    """The permissions matrix must not grant what the API denies.

    The ``role_permissions`` collection is what the admin screen shows
    and edits. It is **display-only** — the API enforces access with
    hard-coded ``require_roles(...)`` lists. When the two disagree, an
    admin is shown a permission that has no effect, and a role looks
    able to reach a screen it cannot.

    The drift is real: ``DEFAULT_PERMISSIONS`` granted
    ``cash_ups: ["read"]`` to ``fleet_manager`` and
    ``operations_manager``, but the cash-ups routes only allow
    ``[SA, OWNER, GM, CA, BA, BM, CONDUCTOR]`` — and the front end
    hides the screen from those two roles. The matrix was the odd one
    out.

    This check compares the matrix against the roles each endpoint
    actually allows, so the two cannot drift apart again.
    """
    from app.models.role_permission import DEFAULT_PERMISSIONS, RESOURCES

    problems: list[str] = []
    matrix_paths = {
        "fuel": "/fuel-logs",
        "transfers": "/vehicle-transfers",
    }

    allowed_by_prefix: dict[str, set[str]] = {}
    for (method, path), info in (roles or {}).items():
        if method != "GET" or info.get("access") != "restricted":
            continue
        # Only the collection endpoint, not its item paths.
        if path.count("/") != 1:
            continue
        allowed_by_prefix.setdefault(path, set()).update(info["roles"])

    for resource in RESOURCES:
        prefix = matrix_paths.get(resource, "/" + resource.replace("_", "-"))
        allowed = allowed_by_prefix.get(prefix)
        if allowed is None:
            continue  # no restricted list endpoint for this resource
        for role, perms in DEFAULT_PERMISSIONS.items():
            if "read" not in (perms.get(resource) or []):
                continue
            if role not in allowed:
                if (role, resource) in KNOWN_MATRIX_DRIFT:
                    continue
                problems.append(
                    f"permissions matrix grants '{role}' read on {resource}, but "
                    f"{prefix} only allows {sorted(allowed)}"
                )
    return problems


CHECKS = {
    "routes": check_routes,
    "params": check_params,
    "fields": check_fields,
    "reachable": check_reachable,
    "webview": check_webview,
    "url": check_url,
    "matrix": check_matrix,
    "guards": check_guards,
    "rbac": check_rbac,
    "screens": check_screens,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("check", nargs="?", choices=[*CHECKS, "all"], default="all")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    ops = openapi_ops()
    calls = frontend_calls()
    roles = endpoint_roles()

    names = list(CHECKS) if args.check == "all" else [args.check]
    results = {}
    for name in names:
        if name == "screens":
            problems = check_screens()
        else:
            problems = CHECKS[name](ops, calls, roles)
        results[name] = problems

    if args.json:
        print(json.dumps({k: v for k, v in results.items()}, indent=1))
        return 1 if any(results.values()) else 0

    print()
    for name, problems in results.items():
        status = "PASS" if not problems else f"FAIL ({len(problems)})"
        print(f"  {name:9} {status}")
        for p in problems[:25]:
            print(f"      - {p}")
        if len(problems) > 25:
            print(f"      ... and {len(problems) - 25} more")
    print()

    failed = [k for k, v in results.items() if v]
    if failed:
        print(f"  {len(failed)} check(s) failed: {', '.join(failed)}")
        return 1
    print("  all contract checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
