#!/usr/bin/env bash
# Regenerate the composite app testing manual, in both formats.
#
#   docs/TESTING_MANUAL.md                 the source of truth (Markdown)
#   docs/TransitOS-App-Testing-Manual.docx the distributable
#
# The manual is generated from the live codebase — every endpoint, screen
# and role is read out of the source — so it cannot drift from the app.
#
# Requires: python3 (backend deps for the OpenAPI schema) and the .NET 9 SDK
# for the DOCX renderer.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> 1/5  Generating the Markdown manuals"
# The backend must be importable, and any existing PYTHONPATH (a venv's
# site-packages, a container's extra libs) must be preserved.
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
python3 docs/build_testing_manual.py

echo "==> 2/5  Converting to a document plan"
python3 docs/markdown_to_plan.py \
    docs/TESTING_MANUAL.md \
    docs/testing_manual_plan.json

echo "==> 3/5  Rendering the DOCX"
cd docs/docx-renderer
dotnet build -v quiet --nologo
dotnet run --no-build -- \
    "$ROOT/docs/testing_manual_plan.json" \
    "$ROOT/docs/TransitOS-App-Testing-Manual.docx"

echo "==> 4/5  Rendering the developer guide"
python3 "$ROOT/docs/markdown_to_plan.py" \
    "$ROOT/docs/IT-DEVELOPER-GUIDE.md" \
    "$ROOT/docs/it_developer_guide_plan.json"
dotnet run --no-build -- \
    "$ROOT/docs/it_developer_guide_plan.json" \
    "$ROOT/docs/IT-DEVELOPER-GUIDE.docx"

echo "==> 5/5  Rendering the user manual"
python3 "$ROOT/docs/build_user_manual.py"
python3 "$ROOT/docs/markdown_to_plan.py" \
    "$ROOT/docs/USER_MANUAL.md" \
    "$ROOT/docs/user_manual_plan.json"
dotnet run --no-build -- \
    "$ROOT/docs/user_manual_plan.json" \
    "$ROOT/docs/TransitOS-User-Manual.docx"

echo
echo "Done:"
ls -lh "$ROOT/docs/TESTING_MANUAL.md" \
       "$ROOT/docs/TransitOS-App-Testing-Manual.docx" \
       "$ROOT/docs/IT-DEVELOPER-GUIDE.docx" \
       "$ROOT/docs/USER_MANUAL.md" \
       "$ROOT/docs/TransitOS-User-Manual.docx"
