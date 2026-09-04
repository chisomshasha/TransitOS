"""Server-side PDF generation for waybills, cash-ups, and reports.

Uses reportlab. Each generator returns bytes; the router streams them
with the correct Content-Disposition header.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def _ngn(v: Any) -> str:
    try:
        n = float(v or 0)
        return f"₦{n:,.0f}"
    except (TypeError, ValueError):
        return "₦0"


def _fmt_date(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%d %b %Y %H:%M")
    except (ValueError, AttributeError):
        return str(iso)


def _build_pdf(story: list) -> bytes:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])
    doc.build(story)
    return buffer.getvalue()


def generate_trip_waybill_pdf(
    trip: dict,
    route: Optional[dict],
    vehicle: Optional[dict],
    driver: Optional[dict],
    conductor: Optional[dict],
    manifest: list[dict],
    branch_name: Optional[str] = None,
) -> bytes:
    styles = getSampleStyleSheet()
    story: list = []

    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"], fontSize=20, textColor=colors.HexColor("#0B3D91")
    )
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=11, textColor=colors.grey)
    head_style = ParagraphStyle("Head", parent=styles["Heading3"], textColor=colors.HexColor("#0B3D91"))

    story.append(Paragraph("TransitOS Waybill", title_style))
    story.append(Paragraph(branch_name or "Trip waybill", subtitle_style))
    story.append(Spacer(1, 10))

    route_name = route.get("name", "—") if route else "—"
    origin_city = route.get("origin_city", "—") if route else "—"
    dest_city = route.get("destination_city", "—") if route else "—"
    story.append(Paragraph(f"<b>Route:</b> {route_name}", styles["Normal"]))
    story.append(Paragraph(f"<b>From:</b> {origin_city}  →  <b>To:</b> {dest_city}", styles["Normal"]))
    story.append(Paragraph(
        f"<b>Departure:</b> {_fmt_date(trip.get('scheduled_departure'))} · "
        f"<b>Status:</b> {trip.get('status', '').upper()}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Vehicle:</b> {vehicle.get('reg_number') if vehicle else '—'} · "
        f"<b>Driver:</b> {driver.get('full_name') if driver else '—'} · "
        f"<b>Conductor:</b> {conductor.get('full_name') if conductor else '—'}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Manifest", head_style))
    table_data = [["Type", "Name / Cargo", "Seat / Weight", "Fare", "Payment"]]
    for m in manifest:
        if m.get("type") == "cargo":
            name = m.get("cargo_description") or "Parcel"
            seat_w = f"{m.get('cargo_weight_kg') or 0} kg"
        else:
            name = m.get("passenger_name") or "Passenger"
            seat_w = m.get("seat_number") or "—"
        table_data.append([
            (m.get("type") or "").capitalize(),
            name,
            seat_w,
            _ngn(m.get("fare")),
            (m.get("payment_status") or "").upper(),
        ])
    if not manifest:
        table_data.append(["—", "No entries", "—", "—", "—"])

    t = Table(table_data, colWidths=[60, 170, 90, 70, 70])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D91")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        f"<b>Total passengers:</b> {trip.get('passenger_count', 0)} · "
        f"<b>Cargo:</b> {trip.get('cargo_weight_kg', 0)} kg · "
        f"<b>Revenue:</b> {_ngn(trip.get('total_revenue'))}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Signatures", head_style))
    sig_table = Table(
        [["Driver", "Conductor", "Approver"], ["", "", ""]],
        colWidths=[155, 155, 155],
        rowHeights=[20, 40],
    )
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("LINEABOVE", (0, 1), (-1, 1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sig_table)

    return _build_pdf(story)


def generate_cash_up_pdf(cash_up: dict, trip: Optional[dict], conductor: Optional[dict]) -> bytes:
    styles = getSampleStyleSheet()
    story: list = []

    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"], fontSize=20, textColor=colors.HexColor("#0B3D91")
    )
    head_style = ParagraphStyle("Head", parent=styles["Heading3"], textColor=colors.HexColor("#0B3D91"))

    story.append(Paragraph("TransitOS Cash-up Report", title_style))
    story.append(Paragraph(
        f"Cash-up {_fmt_date(cash_up.get('created_at'))} · Status: {(cash_up.get('status') or '').upper()}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        f"<b>Conductor:</b> {conductor.get('full_name') if conductor else '—'} · "
        f"<b>Badge:</b> {conductor.get('badge_no') if conductor else '—'}",
        styles["Normal"],
    ))
    if trip:
        story.append(Paragraph(
            f"<b>Trip:</b> {_fmt_date(trip.get('scheduled_departure'))} · "
            f"<b>Passengers:</b> {trip.get('passenger_count', 0)} · "
            f"<b>Revenue:</b> {_ngn(trip.get('total_revenue'))}",
            styles["Normal"],
        ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Breakdown", head_style))
    bd = cash_up.get("breakdown") or []
    table_data = [["Method", "Amount"]]
    for b in bd:
        table_data.append([(b.get("method") or "—").capitalize(), _ngn(b.get("amount"))])
    if not bd:
        table_data.append(["—", "—"])
    table_data.append([Paragraph("<b>Declared total</b>", styles["Normal"]),
                       Paragraph(f"<b>{_ngn(cash_up.get('declared_total'))}</b>", styles["Normal"])])

    t = Table(table_data, colWidths=[200, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D91")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    variance = float(cash_up.get("variance") or 0)
    var_color = "#047857" if variance >= 0 else "#B91C1C"
    story.append(Paragraph(
        f"<b>Expected:</b> {_ngn(cash_up.get('expected_total'))} · "
        f"<font color='{var_color}'><b>Variance: {('+' if variance >= 0 else '')}{_ngn(variance)}</b></font>",
        styles["Normal"],
    ))
    if cash_up.get("notes"):
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"<b>Notes:</b> {cash_up['notes']}", styles["Normal"]))
    if cash_up.get("rejection_reason"):
        story.append(Paragraph(f"<b>Rejection reason:</b> {cash_up['rejection_reason']}", styles["Normal"]))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Signatures", head_style))
    sig_table = Table(
        [["Conductor", "Reviewer"], ["", ""]],
        colWidths=[230, 230],
        rowHeights=[20, 40],
    )
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("LINEABOVE", (0, 1), (-1, 1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sig_table)

    return _build_pdf(story)


__all__ = ["generate_trip_waybill_pdf", "generate_cash_up_pdf"]
