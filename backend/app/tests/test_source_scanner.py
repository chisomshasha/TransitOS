"""The front-end source scanner must never walk into ``node_modules``.

Why this file exists
--------------------
The static contract checks and the runtime contract test all scan the
front end's TypeScript. They used to do it with ``Path.rglob()``, which
descends into ``node_modules`` and *then* throws the results away with an
``if "node_modules" in p.parts`` filter.

That filter is applied after the walk, so the walk still happens. Two
consequences, both observed:

**It was slow.** A single scan of ``frontend/`` took **20.5 seconds**
because it walked several hundred megabytes of installed packages. The
contract checker scans more than once, so every check paid that price.

**It could crash.** ``rglob()`` raises ``FileNotFoundError`` if a
directory disappears while it is walking. Running the backend suite
while ``npm ci`` was installing produced::

    FileNotFoundError: .../frontend/node_modules/fsevents

and the test died. The same crash happens on a developer machine when
the backend suite runs next to a ``npm install``.

The fix is ``tools/contract/sources.py``: one walker that prunes the
skipped directories *before* descending, built on ``os.walk`` (which
ignores a directory vanishing mid-walk). These tests pin that behaviour
so the ``rglob`` pattern cannot come back.
"""

from __future__ import annotations

import pathlib
import shutil
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "contract"))

from sources import SKIP_DIRS, iter_source_files  # noqa: E402

FRONTEND = REPO / "frontend"


def _tree(tmp_path: pathlib.Path) -> pathlib.Path:
    """A miniature front end with dependency and build directories."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "screen.tsx").write_text("export const S = 1;")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "api.ts").write_text("export const api = 1;")
    for junk in ("node_modules", ".expo", "dist", "__pycache__"):
        d = tmp_path / junk / "pkg"
        d.mkdir(parents=True)
        (d / "index.ts").write_text("export const x = 1;")
        (d / "index.tsx").write_text("export const y = 1;")
    return tmp_path


def test_skipped_directories_are_never_scanned(tmp_path):
    """Files under node_modules (and friends) must not be returned."""
    root = _tree(tmp_path)
    found = iter_source_files(root)

    names = {str(p.relative_to(root)) for p in found}
    assert names == {"app/screen.tsx", "lib/api.ts"}


def test_the_real_frontend_scan_excludes_node_modules():
    """The actual scan must not include a single installed package."""
    assert FRONTEND.exists(), "front end not found"

    found = iter_source_files(FRONTEND)
    assert found, "no front-end source found — the scanner is broken"

    offenders = [p for p in found if "node_modules" in p.parts]
    assert not offenders, f"node_modules was scanned: {offenders[:5]}"

    # The real app has screens; a scanner that returns nothing has
    # silently stopped working.
    assert any(p.suffix == ".tsx" for p in found)


def test_scan_survives_a_directory_disappearing_mid_walk(tmp_path):
    """The scanner must not crash when a directory vanishes under it.

    This is the ``npm ci`` race: packages are created and removed while
    the walk is in progress. ``Path.rglob()`` raises ``FileNotFoundError``
    here; the scanner must simply skip it.
    """
    root = tmp_path / "app"
    root.mkdir()
    (root / "screen.tsx").write_text("export const S = 1;")

    churn = root / "churn"
    churn.mkdir()
    (churn / "pkg.ts").write_text("export const x = 1;")

    stop = threading.Event()

    def churn_loop():
        i = 0
        while not stop.is_set():
            d = root / f"churn-{i % 25}"
            try:
                d.mkdir(exist_ok=True)
                (d / "pkg.ts").write_text("export const x = 1;")
                shutil.rmtree(d, ignore_errors=True)
            except OSError:
                pass
            i += 1

    t = threading.Thread(target=churn_loop, daemon=True)
    t.start()
    try:
        time.sleep(0.05)
        for _ in range(25):
            # Must not raise, however unlucky the timing.
            iter_source_files(root)
    finally:
        stop.set()
        t.join(timeout=3)


def test_skip_list_covers_the_usual_suspects():
    """The directories that must never be walked."""
    for name in ("node_modules", ".expo", "dist", "__pycache__"):
        assert name in SKIP_DIRS, f"{name} is not pruned"


def test_missing_root_is_not_an_error(tmp_path):
    """A path that does not exist yields nothing, not an exception."""
    assert iter_source_files(tmp_path / "nope") == []
