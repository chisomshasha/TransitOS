#!/usr/bin/env python3
"""One safe way to walk the front end's source tree.

Every static check and the runtime contract test need to look at the
front end's TypeScript. They used to do it with ``Path.rglob()``, which
has two problems:

**It is slow.** ``rglob("*.ts")`` descends into ``node_modules`` —
thousands of files — and then throws the results away with an
``if "node_modules" in p.parts`` filter. The filter runs *after* the
walk.

**It can crash.** ``rglob()`` raises ``FileNotFoundError`` if a
directory disappears while it is walking. That is not hypothetical: run
the backend suite while ``npm ci`` is installing, and the test dies on::

    FileNotFoundError: .../frontend/node_modules/fsevents

``os.walk`` ignores that error by default, and pruning the directory
list before descending means ``node_modules`` is never entered at all.
"""

from __future__ import annotations

import fnmatch
import os
import pathlib

#: Directories that are never application source: dependencies, build
#: output and caches.
SKIP_DIRS = frozenset(
    {
        "node_modules",
        ".expo",
        "dist",
        "build",
        ".git",
        "__pycache__",
        ".next",
        ".turbo",
        "coverage",
        ".pytest_cache",
        ".venv",
    }
)


def iter_source_files(
    root: pathlib.Path | str, globs: tuple[str, ...] = ("*.ts", "*.tsx")
) -> list[pathlib.Path]:
    """Every file under *root* matching one of *globs*, sorted.

    Skipped directories are pruned during the walk, so nothing under
    ``node_modules`` is ever opened. Errors raised while reading a
    directory (a package being installed or removed underneath us) are
    ignored rather than aborting the scan.
    """
    root = pathlib.Path(root)
    if not root.exists():
        return []

    found: list[pathlib.Path] = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda _e: None):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        base = pathlib.Path(dirpath)
        for name in sorted(filenames):
            if any(fnmatch.fnmatch(name, g) for g in globs):
                found.append(base / name)
    return found


def iter_frontend_sources(
    frontend: pathlib.Path | str, globs: tuple[str, ...] = ("*.ts", "*.tsx")
) -> list[pathlib.Path]:
    """Every front-end source file, excluding ``node_modules``."""
    return iter_source_files(frontend, globs)
