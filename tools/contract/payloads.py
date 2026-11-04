#!/usr/bin/env python3
"""Resolve the request bodies the front end *actually* sends.

Why this file exists
--------------------
The contract checker used to compare the backend's required body fields
against the body fields the front end sends — but only for calls whose
body is a **literal object** at the call site::

    postSingle('/expenses', { amount: 500 })      // checkable
    postSingle('/expenses', body)                 // NOT checkable

Almost none of the mutations are written that way. They go through a
TanStack-Query hook, and the payload is built in the screen::

    // lib/queries.ts
    export function useCreateExpense() {
      return useMutation({ mutationFn: (body) => postSingle('/expenses', body) });
    }

    // app/(app)/expenses.tsx
    const create = useCreateExpense();
    await create.mutateAsync({ amount: amt, vehicle_id: vehicleId, ... });

So 51 of the 60 mutating calls could not be checked at all. A field
renamed on either side of the boundary — ``amount`` becoming ``amt`` in
the screen, or the backend renaming ``amount`` to ``total_amount`` —
was invisible to every check in the repository:

* ``tsc`` compares the front end's types against themselves;
* the backend test suite never sends the front end's body;
* the static checker had no body keys to compare;
* the runtime contract test sent a body it built from the OpenAPI
  schema, so it agreed with the backend by construction.

And because the Pydantic models do not forbid unknown fields, a renamed
field is not even an error — it is **silently dropped**. The record is
saved without the value and nobody finds out until the invoice is wrong.

This module closes that hole by resolving the payload the way the
application actually assembles it::

    hook  ->  mutation variable  ->  mutate()/mutateAsync() argument
          ->  the keys of that object

It is deliberately a source scanner rather than a TypeScript compiler
program: the backend test suite imports it, and that suite must keep
running without node_modules installed.
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import Iterable

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from sources import iter_source_files  # noqa: E402
from check import (  # noqa: E402
    FRONTEND,
    HELPER_METHOD,
    _enclosing_symbol,
    _norm,
    _object_keys,
    _read_args,
    _read_template,
    _split_args,
    _strip_comments,
)

# Helpers whose second argument is the request body.
_HELPER_BODY_ARG = {
    "postSingle": 1,
    "postJson": 1,
    "postNoContent": 1,
    "patchSingle": 1,
    "patchJson": 1,
    "patchNoContent": 1,
    "putSingle": 1,
    "deleteJson": 1,
}

# `api.<verb>(path, body, params)` — body is the second argument.
_API_BODY_ARG = {"post": 1, "patch": 1, "put": 1}


class Payload:
    """One resolved request body."""

    def __init__(
        self,
        method: str,
        path: str,
        keys: list[str],
        src: str,
        symbol: str,
        resolved: bool,
        reason: str = "",
        no_body: bool = False,
    ):
        self.method = method
        self.path = path
        self.keys = keys
        self.src = src
        self.symbol = symbol
        self.resolved = resolved
        self.reason = reason
        # True for calls that take no request body at all (e.g.
        # `postAction('/cash-ups/{id}/submit')`). They are still part of
        # the app's API surface, so they take part in the reachability
        # check, but there is nothing to compare against the schema.
        self.no_body = no_body

    @property
    def key(self) -> tuple[str, str]:
        return (self.method, self.path)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Payload {self.method} {self.path} keys={self.keys} {self.src}>"


# ─── low-level source helpers ───────────────────────────────────────────────

def _match_paren(src: str, open_at: int) -> int:
    """Index just past the ``)`` that closes the ``(`` at ``open_at``."""
    depth = 0
    i = open_at
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in "'\"`":
            _, i = _read_template(src, i)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _object_member(text: str, key: str) -> str | None:
    """The value text of a top-level member of an object literal."""
    text = text.strip()
    if not text.startswith("{"):
        return None
    body = text[1:-1] if text.endswith("}") else text[1:]
    depth, cur, i, n = 0, "", 0, len(body)
    members: list[str] = []
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

    for m in members:
        m = m.strip()
        if not m or ":" not in m:
            continue
        name, _, value = m.partition(":")
        if name.strip().strip("'\"`") == key:
            return value.strip()
    return None


# ─── the scan ───────────────────────────────────────────────────────────────

def _source_files() -> Iterable[pathlib.Path]:
    for sub in ("app", "lib", "components", "stores"):
        base = FRONTEND / sub
        if not base.exists():
            continue
        for p in iter_source_files(base):
            # lib/api.ts is the helper module itself; its "calls" are
            # the axios plumbing, not application requests.
            if p.name == "api.ts":
                continue
            yield p


def _api_calls_in(src: str) -> list[dict]:
    """Every API helper call in ``src`` with its body expression."""
    found: list[dict] = []

    helper_re = re.compile(
        r"(?<![.\w])(" + "|".join(HELPER_METHOD) + r")\s*(?:<[^()]*?>)?\s*\(\s*"
    )
    for m in helper_re.finditer(src):
        raw, after = _read_template(src, m.end())
        if raw is None:
            continue
        args = _split_args(_read_args(src, after))
        helper = m.group(1)
        idx = _HELPER_BODY_ARG.get(helper)
        body_expr = args[idx] if idx is not None and len(args) > idx else None
        found.append(
            {
                "method": HELPER_METHOD[helper],
                "path": _norm(raw),
                "body_expr": body_expr,
                "at": m.start(),
                "symbol": _enclosing_symbol(src, m.start()),
            }
        )

    api_re = re.compile(
        r"\bapi\s*\.\s*(get|post|patch|put|delete)\s*(?:<[^()]*?>)?\s*\(\s*"
    )
    for m in api_re.finditer(src):
        raw, after = _read_template(src, m.end())
        if raw is None:
            continue
        args = _split_args(_read_args(src, after))
        verb = m.group(1).upper()
        idx = _API_BODY_ARG.get(verb.lower())
        body_expr = args[idx] if idx is not None and len(args) > idx else None
        found.append(
            {
                "method": verb,
                "path": _norm(raw),
                "body_expr": body_expr,
                "at": m.start(),
                "symbol": _enclosing_symbol(src, m.start()),
            }
        )

    return found


def _bindings(src: str) -> list[dict]:
    """Every `const VAR = useMutation(...)` / `= useSomeHook(...)`.

    Each binding records the span of the call, so an API call can be
    attributed to the mutation that owns it.
    """
    out: list[dict] = []
    assign = re.compile(
        r"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*(useMutation|use[A-Z][\w$]*)\s*\("
    )
    for m in assign.finditer(src):
        open_paren = src.index("(", m.end() - 1)
        end = _match_paren(src, open_paren)
        name = m.group(2)
        out.append(
            {
                "var": m.group(1),
                "hook": None if name == "useMutation" else name,
                "start": m.start(),
                "end": end,
            }
        )
    return out


def _mutate_arguments(src: str, var: str) -> list[str]:
    """The arguments passed to ``var.mutate(...)`` / ``var.mutateAsync(...)``."""
    call_re = re.compile(
        r"\b" + re.escape(var) + r"\s*\.\s*(?:mutateAsync|mutate)\s*\("
    )
    out: list[str] = []
    for m in call_re.finditer(src):
        args = _split_args(_read_args(src, m.end()))
        if args:
            out.append(args[0].strip())
    return out


_MUTATION_FN_RE = re.compile(
    r"mutationFn\s*:\s*(?:async\s*)?\(\s*([^)]*)\)\s*=>", re.DOTALL
)


def _mutation_param(src: str, at: int) -> tuple[str, list[str]]:
    """The parameter of the ``mutationFn`` that owns the call at ``at``.

    Returns (whole-parameter name, destructured property names). A hook
    written as ``mutationFn: (body) => ...`` takes the whole payload;
    one written as ``mutationFn: ({ id, data }) => ...`` takes named
    properties of it.
    """
    best = None
    for m in _MUTATION_FN_RE.finditer(src):
        if m.start() > at:
            break
        best = m
    if best is None:
        return "", []

    params = best.group(1).strip()
    if params.startswith("{"):
        # `({ id, data }: { id: string; data: X })` — only the
        # destructuring pattern matters, not the type annotation.
        depth, end = 0, 0
        for i, ch in enumerate(params):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        pattern = params[: end + 1] if end else params
        names = []
        for part in pattern.strip("{}").split(","):
            part = part.strip()
            if not part:
                continue
            name = part.split(":", 1)[0].split("=", 1)[0].strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
                names.append(name)
        return "", names
    return params, []


def scan_frontend_payloads() -> list[Payload]:
    """Every request body the front end sends, with its keys."""
    # --- load every source file ------------------------------------------
    sources: dict[str, str] = {}
    for path in _source_files():
        rel = str(path.relative_to(FRONTEND))
        try:
            sources[rel] = _strip_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue

    # --- index mutation variables -----------------------------------------
    # hook name -> [(file, var)]      (a hook used in several screens)
    # inline useMutation -> [(file, var, start, end)]
    hook_vars: dict[str, list[tuple[str, str]]] = {}
    inline: list[tuple[str, str, int, int]] = []
    per_file_bindings: dict[str, list[dict]] = {}

    for rel, src in sources.items():
        binds = _bindings(src)
        per_file_bindings[rel] = binds
        for b in binds:
            if b["hook"]:
                hook_vars.setdefault(b["hook"], []).append((rel, b["var"]))
            else:
                inline.append((rel, b["var"], b["start"], b["end"]))

    # --- resolve each API call's body ------------------------------------
    payloads: list[Payload] = []

    for rel, src in sources.items():
        for call in _api_calls_in(src):
            body_expr = call["body_expr"]
            if body_expr is None:
                # A call with no request body. Track it for reachability.
                payloads.append(
                    Payload(
                        call["method"], call["path"], [], rel, call["symbol"],
                        True, "", no_body=True,
                    )
                )
                continue

            expr = body_expr.strip()

            # 1. A literal object right at the call site.
            if expr.startswith("{"):
                payloads.append(
                    Payload(
                        call["method"], call["path"], _object_keys(expr),
                        rel, call["symbol"], True,
                    )
                )
                continue

            # 2. `body` / `body.data` — trace it to the mutation call.
            parts = expr.split(".")
            root = parts[0].strip()
            subpath = parts[1:]
            if not re.fullmatch(r"[A-Za-z_$][\w$]*", root):
                payloads.append(
                    Payload(
                        call["method"], call["path"], [], rel, call["symbol"],
                        False, f"body expression '{expr}' is not traceable",
                    )
                )
                continue

            # The mutation parameter decides whether `root` is the whole
            # payload or one property of a destructured payload.
            param_name, destructured = _mutation_param(src, call["at"])
            if destructured:
                # `mutationFn: ({ id, data }) => putSingle(path, data)` —
                # the body is the `data` property of the caller's object.
                if root not in destructured:
                    payloads.append(
                        Payload(
                            call["method"], call["path"], [], rel, call["symbol"],
                            False,
                            f"'{root}' is not a property of the mutation parameter",
                        )
                    )
                    continue
                lookup = [root] + subpath
            else:
                lookup = subpath

            # The mutation variable that owns this call.
            owners: list[tuple[str, str]] = []
            for f_rel, var, start, end in inline:
                if f_rel == rel and start <= call["at"] < end:
                    owners.append((f_rel, var))
            if not owners:
                # The call lives inside a hook; the hook's variable is
                # bound in the screen(s) that use it.
                owners = hook_vars.get(call["symbol"], [])

            if not owners:
                payloads.append(
                    Payload(
                        call["method"], call["path"], [], rel, call["symbol"],
                        False, "no mutation variable could be attributed to this call",
                    )
                )
                continue

            keys: list[str] = []
            resolved = False
            reason = "no mutate()/mutateAsync() call with an object literal was found"
            for owner_file, owner_var in owners:
                for arg in _mutate_arguments(sources.get(owner_file, ""), owner_var):
                    if not arg.startswith("{"):
                        # `owner.mutateAsync(id)` — a path parameter.
                        continue
                    target = arg
                    for hop in lookup:
                        target = _object_member(target, hop) or ""
                    if not target.strip().startswith("{"):
                        reason = f"{owner_var}.mutate() argument is not an object literal"
                        continue
                    found_keys = _object_keys(target)
                    if found_keys:
                        keys = found_keys
                        resolved = True
                        reason = ""
                    break
                if resolved:
                    break

            payloads.append(
                Payload(
                    call["method"], call["path"], keys, rel, call["symbol"],
                    resolved, reason,
                )
            )

    return payloads


def payload_keys_by_call(
    payloads: list[Payload] | None = None,
) -> dict[tuple[str, str], list[Payload]]:
    """Group the resolved payloads by (method, path)."""
    if payloads is None:
        payloads = scan_frontend_payloads()
    out: dict[tuple[str, str], list[Payload]] = {}
    for p in payloads:
        out.setdefault(p.key, []).append(p)
    return out


# ─── reachability ───────────────────────────────────────────────────────────

_IMPORT_RE = re.compile(
    r"""(?:from|import)\s+['"]([^'"]+)['"]""",
)

_SCREEN_ROOTS = ("app", "components", "stores")


def _resolve_import(spec: str, from_rel: str) -> str | None:
    """The file an import specifier points at, as a path relative to FRONTEND."""
    if spec.startswith("@/"):
        base = FRONTEND / spec[2:]
    elif spec.startswith("."):
        base = (FRONTEND / from_rel).parent / spec
    else:
        return None  # a package
    for candidate in (
        base.with_suffix(".ts"),
        base.with_suffix(".tsx"),
        base / "index.ts",
        base / "index.tsx",
    ):
        if candidate.exists():
            try:
                return str(candidate.relative_to(FRONTEND))
            except ValueError:
                return None
    return None


def reachable_files() -> set[str]:
    """Every source file a user can reach, following imports.

    A screen is a root. Everything it imports is reachable, and so is
    everything *that* imports — which is how ``lib/push.ts`` (reached
    through ``lib/auth-context.tsx``) counts as reachable.
    """
    files: dict[str, str] = {}
    for path in _source_files():
        rel = str(path.relative_to(FRONTEND))
        try:
            files[rel] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

    edges: dict[str, set[str]] = {}
    for rel, src in files.items():
        targets: set[str] = set()
        for m in _IMPORT_RE.finditer(src):
            resolved = _resolve_import(m.group(1), rel)
            if resolved:
                targets.add(resolved)
        edges[rel] = targets

    roots = {rel for rel in files if rel.startswith(_SCREEN_ROOTS)}
    seen = set(roots)
    stack = list(roots)
    while stack:
        current = stack.pop()
        for target in edges.get(current, ()):  # noqa: B007
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return seen


def reachable_symbols() -> set[str]:
    """Every identifier mentioned in a reachable file."""
    reachable = reachable_files()
    out: set[str] = set()
    for path in _source_files():
        rel = str(path.relative_to(FRONTEND))
        if rel not in reachable:
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out.update(re.findall(r"\b[A-Za-z_$][\w$]*\b", src))
    return out


if __name__ == "__main__":
    all_payloads = scan_frontend_payloads()
    resolved = [p for p in all_payloads if p.resolved]
    unresolved = [p for p in all_payloads if not p.resolved]
    print(f"payloads resolved   : {len(resolved)}")
    print(f"payloads unresolved : {len(unresolved)}")
    print()
    for p in resolved:
        print(f"  OK  {p.method:6} {p.path:42} {sorted(p.keys)}")
    print()
    for p in unresolved:
        print(f"  ??  {p.method:6} {p.path:42} {p.src} ({p.reason})")
