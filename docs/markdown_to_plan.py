"""Convert the generated testing manual into a document plan for the DOCX renderer.

The plan is an intermediate, renderer-agnostic structure: headings,
paragraphs, bullets, callouts and tables. The .NET renderer turns it into
WordprocessingML. Keeping the conversion here means the Markdown stays
the single source of truth and the DOCX cannot drift from it.

    python docs/markdown_to_plan.py docs/TESTING_MANUAL.md docs/testing_manual_plan.json
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys


def strip_inline(text: str) -> str:
    """Flatten Markdown inline syntax to plain text.

    The renderer applies its own emphasis, so the plan carries the plain
    string plus a list of (start, end, style) spans for the renderer to
    re-apply.
    """
    return text


def split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells, cur, esc = [], "", False
    for ch in line:
        if esc:
            cur += ch
            esc = False
            continue
        if ch == "\\":
            esc = True
            cur += ch
            continue
        if ch == "|":
            cells.append(cur.strip())
            cur = ""
            continue
        cur += ch
    cells.append(cur.strip())
    return cells


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells)


def clean(cell: str) -> str:
    """Remove Markdown emphasis markers, keep the words."""
    cell = cell.strip()
    cell = re.sub(r"\*\*(.+?)\*\*", r"\1", cell)
    cell = re.sub(r"`(.+?)`", r"\1", cell)
    cell = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", cell)
    cell = cell.replace("<br>", " · ")
    cell = re.sub(r"<br\s*/?>", " · ", cell)
    return cell.strip()


def convert(md_path: pathlib.Path, out_path: pathlib.Path) -> dict:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    blocks: list[dict] = []
    i = 0
    title = ""
    subtitle = ""
    meta_lines: list[str] = []
    note = ""
    after_title = True

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Horizontal rule -> nothing (visual separator handled by spacing)
        if stripped == "---":
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = clean(m.group(2))
            if level == 1 and not title:
                title = text
                blocks.append({"type": "title", "text": text})
            elif level == 2 and not subtitle and text.startswith("Part "):
                subtitle = ""
                blocks.append({"type": "heading", "level": level, "text": text})
            else:
                blocks.append({"type": "heading", "level": level, "text": text})
            i += 1
            continue

        # Blockquote -> callout
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append({"type": "callout", "text": clean(" ".join(quote_lines))})
            continue

        # Table
        if stripped.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            headers = split_row(lines[i])
            if i + 1 < len(lines) and is_separator(split_row(lines[i + 1])):
                i += 2
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = split_row(lines[i])
                    if not is_separator(cells):
                        rows.append([clean(c) for c in cells])
                    i += 1
                # Pad short rows so every row matches the header width.
                width = len(headers)
                headers = [clean(h) for h in headers]
                rows = [(r + [""] * width)[:width] for r in rows]
                blocks.append({"type": "table", "headers": headers, "rows": rows})
                continue
            i += 1
            continue

        # Bullet list
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(clean(re.sub(r"^\s*[-*]\s+", "", lines[i])))
                i += 1
            blocks.append({"type": "bullets", "items": items})
            continue

        # Numbered list
        if re.match(r"^\d+(\.\d+)*\.?\s+", stripped) and not stripped.startswith("|"):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+(\.\d+)*\.?\s+", lines[i]):
                items.append(clean(re.sub(r"^\s*\d+(\.\d+)*\.?\s+", "", lines[i])))
                i += 1
            blocks.append({"type": "bullets", "items": items, "numbered": True})
            continue

        # Image: ![alt](path)
        m = re.match(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\s*$", stripped)
        if m:
            rel = m.group("path").strip()
            # Paths in the Markdown are relative to the Markdown file.
            absolute = os.path.normpath(os.path.join(os.path.dirname(
                os.path.abspath(md_path)), rel))
            blocks.append({
                "type": "image",
                "path": absolute,
                "rel": rel,
                "caption": m.group("alt").strip(),
            })
            i += 1
            continue

        # Fenced code block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            body_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body_lines.append(lines[i])
                i += 1
            i += 1  # closing fence
            blocks.append({
                "type": "code",
                "lang": lang,
                "text": "\n".join(body_lines),
            })
            continue

        # Blank
        if not stripped:
            i += 1
            continue

        # The release-candidate line becomes the cover subtitle.
        if stripped.startswith("**Release candidate:**") and not subtitle:
            subtitle = clean(stripped).rstrip("· ").strip()
            i += 1
            continue

        # A whole-line bold statement directly under the title is the
        # cover subtitle; the plain line under it is the cover meta.
        if after_title and not subtitle and re.fullmatch(r"\*\*[^*]+\*\*", stripped):
            subtitle = clean(stripped).rstrip("· ").strip()
            after_title = False
            i += 1
            continue

        # The paragraphs directly under the cover subtitle are the meta
        # line and then the note.
        if subtitle and not note and not meta_lines and stripped and not stripped.startswith("#"):
            meta_lines.append(clean(stripped))
            i += 1
            continue
        if subtitle and meta_lines and not note and stripped and not stripped.startswith("#"):
            note = clean(stripped)
            i += 1
            continue

        # Paragraph — join consecutive non-blank lines
        if after_title and not subtitle:
            after_title = False
            meta_lines.append(clean(stripped))
        para = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,4}\s|\||>|[-*]\s|\d+(\.\d+)*\.?\s|---$)", lines[i].strip()
        ):
            para.append(lines[i].strip())
            i += 1
        blocks.append({"type": "paragraph", "text": clean(" ".join(para))})

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(md_path)))
    logo = os.path.join(repo_root, "frontend", "assets", "transitos-logo.png")
    cover = {
        "logo": logo if os.path.isfile(logo) else "",
        "subtitle": subtitle,
        "meta": meta_lines,
        "note": note,
    }

    plan = {
        "title": title,
        "cover": cover,
        "subtitle": subtitle,
        "blocks": blocks,
    }
    out_path.write_text(json.dumps(plan, indent=1), encoding="utf-8")

    counts: dict[str, int] = {}
    for b in blocks:
        counts[b["type"]] = counts.get(b["type"], 0) + 1
    print(f"wrote {out_path}")
    print(f"  blocks: {counts}")
    print(f"  tables: {sum(len(b.get('rows', [])) for b in blocks if b['type'] == 'table')} rows")
    return plan


if __name__ == "__main__":
    md = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "docs/TESTING_MANUAL.md")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "docs/testing_manual_plan.json")
    convert(md, out)
