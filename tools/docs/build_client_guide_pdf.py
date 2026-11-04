#!/usr/bin/env python3
"""
Build the client-facing TransitOS onboarding guide as a print-ready PDF.

Source of truth
---------------
    docs/CLIENT_ONBOARDING_GUIDE.md          (the guide, in Markdown)
    frontend/lib/theme.ts                    (the colours — navy + yellow)
    frontend/assets/transitos-logo.png       (the bus logo)

Pipeline
--------
    markdown ──markdown-it──> body HTML ──> guide.pdf  (contents + body)
                                          cover.pdf (full bleed)
                                                │
                                                └─> append ─> stamp ─> final
                                                     (pypdf)   (reportlab)

Four things are deliberate here:

  * **Cover, contents and body are one document.** Chromium resolves `#anchor`
    links only against elements in the same document, so a contents page
    rendered on its own would produce a PDF whose links all point at nothing.
    Rendering everything together is what makes the contents clickable.

  * **The cover is a separate render.** Chromium clips content to the content
    box, so a full-bleed cover needs a zero page margin while the body needs
    real ones. The two are rendered separately and concatenated; the links
    survive because pypdf's `append` remaps Chromium's named destinations
    onto the merged page tree.

  * **The contents is rendered twice.** The first pass uses placeholder page
    numbers; once the body has been paginated the real numbers are known and
    the contents is rendered again. A one-pixel marker at the top of the body
    says exactly where the body starts, so heading -> page is a lookup rather
    than a guess.

  * **The running head and footer are stamped, not rendered.** Chromium's
    built-in footer prints the source file's URL and its own page counter,
    which is wrong here. reportlab stamps the real absolute page number.

Usage
-----
    python3 tools/docs/build_client_guide_pdf.py \
        --out-dir /workspace/output/guide-build \
        --pdf    /workspace/output/TransitOS-Client-Onboarding-Guide.pdf
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MARKDOWN = ROOT / "docs" / "CLIENT_ONBOARDING_GUIDE.md"
LOGO = ROOT / "frontend" / "assets" / "transitos-logo.png"
RENDERER = Path(__file__).resolve().parent / "render_pdf.cjs"

DOC_TITLE = "Branch Onboarding & Operations Guide"
DOC_VERSION = "v1.2.0"
DOC_DATE = "3 November 2026"
DOC_SUBTITLE = "Setting up a branch, and running trips, people, fleet and cash on TransitOS."

COVER_MARGIN = "0"                 # Chromium clips to the content box: the cover needs 0
BODY_MARGIN = "18mm 14mm 15mm 14mm"  # body pages get real page margins
PAGE_W, PAGE_H = 595.276, 841.89  # A4 in points
MM = 72 / 25.4
MARGIN_L = 14 * MM
MARGIN_R = 14 * MM
HEADER_BASELINE = PAGE_H - 12.0 * MM
HEADER_RULE = PAGE_H - 15.4 * MM
FOOTER_BASELINE = 8.4 * MM
FOOTER_RULE = 11.4 * MM

# Marker that says "the body starts here". White and 1pt, so it is invisible
# on the page but still present in the extracted text layer.
BODY_MARK = "TRANSITOSBODYSTART"

# ── Palette — taken verbatim from frontend/lib/theme.ts ──────────────────────
NAVY = "#0B3D91"
NAVY_DEEP = "#072A66"
YELLOW = "#FFCC00"
YELLOW_SOFT = "#FFF6CC"
SLATE = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
FIELD = "#F1F5F9"
DANGER = "#B91C1C"
DANGER_BG = "#FEF2F2"


# ──────────────────────────────────────────────────────────────────────────────
# Markdown → HTML
# ──────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_markdown(text: str):
    """Render the guide to an HTML fragment and collect a heading tree."""
    # The green tick emoji has no glyph in any font installed on the build
    # machine and falls back to Noto Color Emoji, which looks wrong in print.
    # The monochrome tick is used throughout the guide already.
    text = text.replace("✅", "✔")

    md = MarkdownIt("commonmark").enable("table").enable("strikethrough")
    tokens = md.parse(text)

    entries: list[dict] = []
    seen: dict[str, int] = {}

    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            inline = tokens[i + 1]
            raw = inline.content.strip()
            base = slugify(raw)
            seen[base] = seen.get(base, 0) + 1
            sid = base if seen[base] == 1 else f"{base}-{seen[base]}"
            tok.attrSet("id", sid)
            entries.append({"id": sid, "level": int(tok.tag[1]), "text": raw})

        elif tok.type == "paragraph_open":
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if nxt is not None and nxt.type == "inline" and nxt.content.startswith("**You need"):
                tok.attrSet("class", "need")

        elif tok.type == "blockquote_open":
            content = ""
            for j in range(i + 1, min(i + 10, len(tokens))):
                if tokens[j].type == "inline":
                    content = tokens[j].content
                    break
            cls = "callout callout-danger" if "cannot currently advance" in content else "callout"
            tok.attrSet("class", cls)

    # The document H1 becomes the cover title; drop it from the body.
    if entries and entries[0]["level"] == 1:
        entries = entries[1:]
        for i, tok in enumerate(tokens):
            if tok.type == "heading_open" and tok.tag == "h1":
                del tokens[i : i + 3]
                break

    html = md.renderer.render(tokens, md.options, {})

    # The closing section ("A last word") is the last thing in the guide and
    # lands alone on the final page. Wrap it so the PDF can render it as a
    # designed back page instead of a nearly-empty sheet.
    h2s = list(re.finditer(r'<h2 id="[^"]+">', html))
    if h2s:
        cut = h2s[-1].start()
        html = html[:cut] + '<div class="closing">' + html[cut:] + '</div>'

    return html, entries


# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────

BASE_CSS = f"""
@page {{ size: A4 portrait; margin: {BODY_MARGIN}; }}
* {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html {{ background: #fff; }}
body {{
  margin: 0;
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  font-size: 10pt;
  line-height: 1.5;
  color: {SLATE};
  background: #fff;
}}
@media screen {{
  html {{ background: #d5d7dc; }}
  body {{ margin: 0; padding: 20px 0; }}
  body > section {{
    width: 210mm; min-height: 297mm; margin: 0 auto 20px; background: #fff;
    box-shadow: 0 4px 24px rgba(0,0,0,0.18); box-sizing: border-box; overflow: hidden;
  }}
}}
"""

COVER_CSS = f"""
.cover-page {{
  position: relative;
  width: 210mm;
  height: 297mm;
  overflow: hidden;
  background: {NAVY_DEEP};
}}
.cover-band {{ position: absolute; inset: 0; background: {NAVY_DEEP}; }}
.cover-band::after {{
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 54mm;
  background: {NAVY};
}}
.cover-band::before {{
  content: ""; position: absolute; left: 0; right: 0; top: 0; height: 8mm; background: {YELLOW};
}}
.cover-inner {{ position: absolute; top: 27mm; left: 20mm; right: 20mm; }}
.cover-brand {{ display: flex; align-items: center; gap: 4.5mm; }}
.cover-logo {{ width: 16mm; height: 16mm; border-radius: 2.5mm; display: block; }}
.cover-wordmark {{
  font-size: 14pt; font-weight: bold; color: #fff; letter-spacing: 3.4pt; line-height: 1;
}}
.cover-wordmark span {{ color: {YELLOW}; }}

.cover-mid {{ position: absolute; top: 94mm; left: 20mm; right: 20mm; }}
.cover-eyebrow {{
  font-size: 8.4pt; font-weight: bold; letter-spacing: 2.8pt;
  color: {YELLOW}; margin-bottom: 8mm;
}}
.cover-title {{
  font-size: 34pt; line-height: 1.06; color: #fff; margin: 0 0 7mm;
  letter-spacing: -0.7pt; font-weight: bold;
}}
.cover-rule {{ width: 36mm; height: 2.8pt; background: {YELLOW}; margin-bottom: 8mm; }}
.cover-sub {{ font-size: 11.4pt; line-height: 1.5; color: #C9D6EE; margin: 0; max-width: 140mm; }}

.cover-foot {{ position: absolute; left: 20mm; right: 20mm; bottom: 20mm; }}
.cover-meta {{ display: flex; gap: 8mm; }}
.cover-meta div {{ flex: 1; }}
.cover-meta .k {{
  font-size: 7.2pt; font-weight: bold; letter-spacing: 1.5pt;
  color: {YELLOW}; margin-bottom: 2.4mm;
}}
.cover-meta .v {{ font-size: 9.2pt; color: #fff; line-height: 1.38; }}
.cover-note {{
  margin-top: 9mm; padding-top: 5mm; border-top: 0.5pt solid rgba(255,255,255,0.24);
  font-size: 8pt; color: #A9BCDC; line-height: 1.45;
}}
"""

TOC_CSS = f"""
.toc-head {{
  border-bottom: 2.5pt solid {YELLOW};
  padding-bottom: 7pt;
  margin-bottom: 8pt;
}}
.toc-head h1 {{
  font-size: 18pt;
  color: {NAVY};
  margin: 0 0 3pt;
  letter-spacing: -0.2pt;
  line-height: 1.15;
}}
.toc-head p {{ margin: 0; font-size: 9pt; color: {MUTED}; }}

.toc-row {{
  display: flex;
  align-items: baseline;
  break-inside: avoid;
  text-decoration: none;
  color: inherit;
  margin: 0 0 4.6pt;
  font-size: 9.2pt;
}}
.toc-row .lbl {{ flex: 0 1 auto; }}
.toc-row .lead {{
  flex: 1 1 auto; border-bottom: 0.6pt dotted #B9C2D0;
  margin: 0 5pt; position: relative; top: -3.4pt;
}}
.toc-row .pg {{
  flex: 0 0 auto; color: {NAVY}; font-weight: bold;
  font-variant-numeric: tabular-nums;
}}

.toc-part {{
  display: flex; align-items: baseline; break-inside: avoid;
  text-decoration: none; color: inherit;
  margin: 7.5pt 0 3.5pt; font-size: 10pt; font-weight: bold; color: {NAVY};
}}
.toc-part .lbl {{ flex: 0 1 auto; }}
.toc-part .lead {{
  flex: 1 1 auto; border-bottom: 0.6pt solid {NAVY};
  margin: 0 5pt; position: relative; top: -3.4pt; opacity: 0.4;
}}
.toc-part .pg {{
  flex: 0 0 auto; color: {NAVY}; font-weight: bold;
  font-variant-numeric: tabular-nums;
}}

.toc-sub .toc-row {{ margin-left: 7mm; font-size: 8.9pt; color: #334155; }}
.toc-sub .toc-row .pg {{ font-weight: normal; color: {MUTED}; }}
"""

BODY_CSS = f"""
.doc-body {{ break-before: page; }}
.toc-head {{ break-after: avoid; }}
.bmark {{ font-size: 1pt; line-height: 1pt; color: #fff; margin: 0; padding: 0; }}

.doc-body h1 {{
  break-before: auto;
  break-after: avoid;
  font-size: 16pt;
  line-height: 1.16;
  color: #fff;
  background: {NAVY};
  border-left: 4pt solid {YELLOW};
  padding: 7pt 12pt 8pt;
  margin: 17pt 0 10pt;
  border-radius: 1.5pt;
  letter-spacing: -0.1pt;
}}

.doc-body h2 {{
  break-after: avoid;
  font-size: 12.5pt;
  color: {NAVY};
  margin: 13pt 0 5pt;
  padding-left: 8pt;
  border-left: 3pt solid {YELLOW};
}}

.doc-body h3 {{
  break-after: avoid;
  font-size: 10.4pt;
  color: {SLATE};
  margin: 10pt 0 3pt;
}}

.doc-body p {{ margin: 0 0 6pt; }}
.doc-body ul, .doc-body ol {{ margin: 4pt 0 8pt; padding-left: 15pt; }}
.doc-body li {{ margin: 2.5pt 0; }}
.doc-body li > ul, .doc-body li > ol {{ margin: 2pt 0 3pt; }}
.doc-body strong {{ color: {NAVY_DEEP}; }}
.doc-body em {{ font-family: "Bitstream Charter", "Liberation Serif", Georgia, serif; }}

.doc-body table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 8.6pt;
  line-height: 1.38;
  margin: 5pt 0 10pt;
  break-inside: auto;
}}
.doc-body tr {{ break-inside: avoid; }}
.doc-body thead th {{ break-after: avoid; }}
.doc-body thead {{ display: table-header-group; }}
.doc-body thead th {{
  background: {NAVY};
  color: #fff;
  text-align: left;
  font-weight: bold;
  font-size: 8.2pt;
  letter-spacing: 0.15pt;
  padding: 5pt 6.5pt;
}}
.doc-body tbody td {{
  padding: 4.5pt 6.5pt;
  border-bottom: 0.5pt solid {BORDER};
  vertical-align: top;
}}
.doc-body tbody tr:nth-child(even) {{ background: #F7F9FC; }}
.doc-body tbody td:first-child {{ font-weight: bold; color: {NAVY_DEEP}; }}

.doc-body blockquote {{
  margin: 8pt 0;
  padding: 7pt 10pt 7pt 11pt;
  background: {YELLOW_SOFT};
  border-left: 2.5pt solid {YELLOW};
  font-size: 9.2pt;
  line-height: 1.48;
  color: #3B3A30;
  break-inside: avoid;
}}
.doc-body blockquote p {{ margin: 0 0 4pt; }}
.doc-body blockquote p:last-child {{ margin-bottom: 0; }}
.doc-body blockquote strong {{ color: #6B5500; }}
.doc-body .callout-danger {{ background: {DANGER_BG}; border-left-color: {DANGER}; color: #5A2020; }}
.doc-body .callout-danger strong {{ color: {DANGER}; }}

.doc-body p.need {{
  margin: 4pt 0 9pt;
  padding: 5pt 9pt;
  background: {FIELD};
  border-left: 2.5pt solid {NAVY};
  font-size: 9.2pt;
  break-inside: avoid;
}}
.doc-body p.need strong {{
  color: {NAVY};
  text-transform: uppercase;
  letter-spacing: 0.4pt;
  font-size: 8pt;
  margin-right: 6pt;
}}
.doc-body p.need code {{ background: #fff; }}

.doc-body code {{
  font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
  font-size: 0.9em;
  color: {NAVY_DEEP};
}}
.doc-body p code, .doc-body li code, .doc-body td code, .doc-body th code {{
  background: {FIELD};
  padding: 0.5pt 2.5pt;
  border-radius: 2pt;
}}

.doc-body pre {{
  background: {FIELD};
  border-left: 2.5pt solid {NAVY};
  padding: 8pt 10pt;
  margin: 6pt 0 9pt;
  font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
  font-size: 7.9pt;
  line-height: 1.42;
  white-space: pre;
  break-inside: avoid;
  color: #1E293B;
}}
.doc-body pre code {{ background: none; padding: 0; font-size: inherit; color: inherit; }}
.doc-body hr {{ display: none; }}

/* The closing section, rendered as a back page. */
.doc-body .closing {{
  background: {NAVY_DEEP};
  color: #C9D6EE;
  padding: 12mm 11mm;
  margin: 14pt 0 0;
  border-radius: 2pt;
  min-height: 238mm;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: center;
  break-inside: avoid;
}}
.doc-body .closing h2 {{
  color: {YELLOW};
  border-left: 0;
  padding-left: 0;
  margin: 0 0 9pt;
  font-size: 14pt;
}}
.doc-body .closing p {{ color: #C9D6EE; }}
.doc-body .closing strong {{ color: #fff; }}
.doc-body .closing em {{ color: #E6EDF8; }}
"""


# ──────────────────────────────────────────────────────────────────────────────
# HTML assembly
# ──────────────────────────────────────────────────────────────────────────────

def logo_data_uri(path: Path, size: int = 480) -> str:
    """Downscale the app logo and inline it as a PNG data URI."""
    img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def cover_markup(logo_uri: str) -> str:
    return f"""<section class="cover-page">
  <div class="cover-band"></div>
  <div class="cover-inner">
    <div class="cover-brand">
      <img class="cover-logo" src="{logo_uri}" alt="TransitOS">
      <div class="cover-wordmark">TRANSIT<span>OS</span></div>
    </div>
  </div>
  <div class="cover-mid">
    <div class="cover-eyebrow">CLIENT HANDOVER</div>
    <h1 class="cover-title">{DOC_TITLE}</h1>
    <div class="cover-rule"></div>
    <p class="cover-sub">{DOC_SUBTITLE}</p>
  </div>
  <div class="cover-foot">
    <div class="cover-meta">
      <div><div class="k">APPLIES TO</div><div class="v">TransitOS {DOC_VERSION}<br>Expo app + TransitOS API</div></div>
      <div><div class="k">AUDIENCE</div><div class="v">Head office, branch managers,<br>fleet and finance staff</div></div>
      <div><div class="k">ISSUED</div><div class="v">{DOC_DATE}<br>Version 1.0</div></div>
    </div>
    <div class="cover-note">
      This guide tells you what to do, in what order, and by whom. It is a companion
      to the User Manual, which explains what every screen looks like. Every screen
      path and button name in here has been checked against the shipping app.
    </div>
  </div>
</section>"""


def build_toc_rows(entries: list[dict], page_map: dict[str, int]) -> str:
    rows: list[str] = []
    for e in entries:
        page = page_map.get(e["id"], "")
        # A heading may carry Markdown inline code. The backticks are
        # Markdown syntax — they never reach the page, so the contents
        # must not show them either.
        label = e["text"].replace("`", "")
        if e["level"] == 1:
            rows.append(
                f'<a class="toc-part" href="#{e["id"]}">'
                f'<span class="lbl">{esc(label)}</span>'
                f'<span class="lead"></span>'
                f'<span class="pg">{page}</span></a>'
            )
        else:
            rows.append(
                f'<div class="toc-sub">'
                f'<a class="toc-row" href="#{e["id"]}">'
                f'<span class="lbl">{esc(label)}</span>'
                f'<span class="lead"></span>'
                f'<span class="pg">{page}</span></a></div>'
            )
    return "\n".join(rows)


def build_cover_html(logo_uri: str) -> str:
    """The cover, on its own — it needs zero page margins to bleed."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{DOC_TITLE}</title>
<style>{COVER_CSS}</style>
</head>
<body>
{cover_markup(logo_uri)}
</body>
</html>"""


def build_guide_html(body_html: str, entries: list[dict], page_map: dict[str, int]) -> str:
    """Contents + body in a single document, so the contents links resolve."""
    css = BASE_CSS + TOC_CSS + BODY_CSS
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{DOC_TITLE}</title>
<style>{css}</style>
</head>
<body>
<section>
  <div class="toc-head">
    <h1>Contents</h1>
    <p>Every entry below is a link — click it to jump straight to that section.</p>
  </div>
  <div class="toc">
{build_toc_rows(entries, page_map)}
  </div>
  <div class="doc-body">
    <p class="bmark">{BODY_MARK}</p>
{body_html}
  </div>
</section>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────────────────────────────────────

def render(html_path: Path, pdf_path: Path, margin: str) -> None:
    cmd = [
        "node", str(RENDERER),
        "--in", str(html_path),
        "--out", str(pdf_path),
        "--format", "A4",
        "--margin", margin,
        "--wait", "1200",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"render failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    print(f"  rendered {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")


def pdf_page_texts(pdf_path: Path) -> list[str]:
    import pdfplumber

    out = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            out.append(re.sub(r"\s+", " ", txt).strip().lower())
    return out


def find_body_start(pages: list[str]) -> int:
    """1-based index of the first page of the body inside the guide PDF."""
    for idx, txt in enumerate(pages, start=1):
        if BODY_MARK.lower() in txt:
            return idx
    raise RuntimeError("body-start marker not found in the rendered guide")


def locate_headings(pages: list[str], entries: list[dict], body_start: int):
    """Map each heading id to its 1-based page inside the guide PDF."""
    page_map: dict[str, int] = {}
    unresolved: list[str] = []

    for e in entries:
        # A heading may carry Markdown inline code: "a trip from `planned`
        # to `cashed up`". The backticks are Markdown syntax and never
        # reach the page, so the plain form is tried as well.
        needles = []
        for text in (e["text"], e["text"].replace("`", "")):
            needle = re.sub(r"\s+", " ", text).strip().lower()
            if needle and needle not in needles:
                needles.append(needle)
        found = None
        for idx in range(body_start - 1, len(pages)):
            if any(needle in pages[idx] for needle in needles):
                found = idx + 1
                break
        if found is None:
            unresolved.append(e["text"])
        else:
            page_map[e["id"]] = found

    # An unresolved heading inherits the page of the closest resolved
    # predecessor, so the contents never shows a blank.
    last = body_start
    for e in entries:
        if e["id"] in page_map:
            last = page_map[e["id"]]
        else:
            page_map[e["id"]] = last

    return page_map, unresolved


# ──────────────────────────────────────────────────────────────────────────────
# Running head / footer
# ──────────────────────────────────────────────────────────────────────────────

def merge_cover_and_stamp(cover_pdf: Path, guide_pdf: Path, out_pdf: Path,
                          footer_left: str) -> int:
    """Concatenate cover + guide and stamp the running head and footer.

    `append` is used rather than `add_page` because only `append` carries
    Chromium's named-destination tree across the merge — and that tree is what
    makes the table of contents clickable. `add_page` silently drops it.
    """
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas

    writer = PdfWriter()
    writer.append(PdfReader(str(cover_pdf)))
    writer.append(PdfReader(str(guide_pdf)))
    total = len(writer.pages)
    cover_pages = len(PdfReader(str(cover_pdf)).pages)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    for i in range(total):
        if i >= cover_pages:
            c.setFont("Helvetica", 7.2)
            c.setFillColor(HexColor(MUTED))
            c.drawString(MARGIN_L, HEADER_BASELINE, "TRANSITOS  \u00b7  BRANCH ONBOARDING & OPERATIONS GUIDE")
            c.setFont("Helvetica-Bold", 7.2)
            c.setFillColor(HexColor(NAVY))
            c.drawRightString(PAGE_W - MARGIN_R, HEADER_BASELINE, f"{DOC_VERSION}  \u00b7  {DOC_DATE}")
            c.setStrokeColor(HexColor(BORDER))
            c.setLineWidth(0.5)
            c.line(MARGIN_L, HEADER_RULE, PAGE_W - MARGIN_R, HEADER_RULE)

            c.setFont("Helvetica", 7.2)
            c.setFillColor(HexColor(MUTED))
            c.drawString(MARGIN_L, FOOTER_BASELINE, footer_left)
            c.setFont("Helvetica-Bold", 7.2)
            c.setFillColor(HexColor(NAVY))
            c.drawRightString(PAGE_W - MARGIN_R, FOOTER_BASELINE, f"Page {i + 1} of {total}")
            c.setStrokeColor(HexColor(BORDER))
            c.setLineWidth(0.5)
            c.line(MARGIN_L, FOOTER_RULE, PAGE_W - MARGIN_R, FOOTER_RULE)
        c.showPage()
    c.save()
    buf.seek(0)

    overlay = PdfReader(buf)
    for i, page in enumerate(writer.pages):
        page.merge_page(overlay.pages[i])

    with open(out_pdf, "wb") as fh:
        writer.write(fh)
    return total


def add_bookmarks(pdf_path: Path, items: list[tuple[str, int]]) -> None:
    """Add a PDF outline so the reader's side panel mirrors the contents."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for title, page_no in items:
        try:
            writer.add_outline_item(title, page_no - 1)
        except Exception:  # noqa: BLE001 - a bad bookmark must not kill the build
            pass
    with open(pdf_path, "wb") as fh:
        writer.write(fh)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Build the TransitOS client guide PDF.")
    ap.add_argument("--out-dir", default="/workspace/output/guide-build")
    ap.add_argument("--pdf", default="/workspace/output/TransitOS-Client-Onboarding-Guide.pdf")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    final_pdf = Path(args.pdf)
    final_pdf.parent.mkdir(parents=True, exist_ok=True)

    print("· reading source")
    src = MARKDOWN.read_text(encoding="utf-8")
    body_html, entries = parse_markdown(src)
    print(f"  {len(entries)} headings, {len(body_html) // 1024} KB of HTML")
    logo_uri = logo_data_uri(LOGO)

    guide_html = out_dir / "guide.html"
    guide_pdf = out_dir / "guide.pdf"

    # Pass 1 — contents with placeholder page numbers, to learn where the
    # body actually starts.
    print("· rendering (pass 1)")
    guide_html.write_text(build_guide_html(body_html, entries, {}), encoding="utf-8")
    render(guide_html, guide_pdf, BODY_MARGIN)

    pages = pdf_page_texts(guide_pdf)
    body_start = find_body_start(pages)
    page_map, unresolved = locate_headings(pages, entries, body_start)
    if unresolved:
        print(f"  ! could not locate {len(unresolved)} heading(s): {unresolved}")

    # The cover sits in front of the guide, so the page a reader sees is the
    # guide's page plus one. Fold that offset in now.
    absolute = {e["id"]: page_map[e["id"]] + 1 for e in entries}

    # Pass 2 — contents with the real page numbers.
    print("· rendering (pass 2)")
    guide_html.write_text(build_guide_html(body_html, entries, absolute), encoding="utf-8")
    render(guide_html, guide_pdf, BODY_MARGIN)

    pages2 = pdf_page_texts(guide_pdf)
    body_start2 = find_body_start(pages2)
    if body_start2 != body_start:
        print(f"  ! body start moved {body_start} -> {body_start2}; re-resolving")
        body_start = body_start2
        page_map, unresolved = locate_headings(pages2, entries, body_start)
        absolute = {e["id"]: page_map[e["id"]] + 1 for e in entries}
        guide_html.write_text(build_guide_html(body_html, entries, absolute), encoding="utf-8")
        render(guide_html, guide_pdf, BODY_MARGIN)

    # Cover
    print("· rendering cover")
    cover_html = out_dir / "cover.html"
    cover_pdf = out_dir / "cover.pdf"
    cover_html.write_text(build_cover_html(logo_uri), encoding="utf-8")
    render(cover_html, cover_pdf, COVER_MARGIN)

    # Merge + running head/footer, then bookmarks.
    print("· merging")
    total = merge_cover_and_stamp(
        cover_pdf, guide_pdf, final_pdf,
        "TransitOS  \u00b7  Branch Onboarding & Operations Guide",
    )
    marks = [(e["text"], absolute[e["id"]]) for e in entries if e["level"] == 1]
    add_bookmarks(final_pdf, marks)

    print(f"\n✓ {final_pdf}")
    print(f"  {total} pages · {final_pdf.stat().st_size // 1024} KB")
    meta = {
        "pdf": str(final_pdf),
        "pages": total,
        "body_start": body_start,
        "headings": len(entries),
        "unresolved": unresolved,
    }
    (out_dir / "build-report.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
