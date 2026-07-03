"""Award-memo PDF generation (reportlab). Produces the recommendation memo a
superintendent files: vessel + tender, the TEC ranking, the recommendation and
its rationale, and the contract checklist."""
from __future__ import annotations

import io
from datetime import datetime, timezone


def build_award_memo(*, tender_ref: str, vessel: str, yard: str, tec_usd: float,
                     ranking: list[dict], rationale: str, checklist: dict,
                     memo_note: str = "") -> bytes:
    """ranking: [{rank, yard, tec_usd, recommended}] ordered by rank."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=22 * mm, bottomMargin=20 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm, title=f"Award memo {tender_ref}")
    styles = getSampleStyleSheet()
    chrome = colors.HexColor("#0B1826")
    ink2 = colors.HexColor("#4E5D6B")
    h = ParagraphStyle("h", parent=styles["Title"], fontName="Helvetica-Bold",
                       fontSize=18, textColor=chrome, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=ink2, spaceAfter=14)
    hd = ParagraphStyle("hd", parent=styles["Heading2"], fontName="Helvetica-Bold",
                        fontSize=12, textColor=chrome, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10.5, leading=15)

    story = []
    story.append(Paragraph("Award Recommendation Memorandum", h))
    story.append(Paragraph(
        f"Tender {tender_ref} &nbsp;·&nbsp; {vessel} &nbsp;·&nbsp; "
        f"{datetime.now(timezone.utc).strftime('%d %b %Y')}", sub))

    story.append(Paragraph("Recommendation", hd))
    story.append(Paragraph(
        f"Award to <b>{yard}</b> on a Total Evaluated Cost of "
        f"<b>${tec_usd / 1e6:.2f}M</b>. {rationale}", body))

    story.append(Paragraph("Evaluated ranking", hd))
    data = [["Rank", "Yard", "Total Evaluated Cost", ""]]
    for r in ranking:
        data.append([
            str(r["rank"]), r["yard"], f"${r['tec_usd'] / 1e6:.2f}M",
            "RECOMMENDED" if r.get("recommended") else "",
        ])
    tbl = Table(data, colWidths=[15 * mm, 80 * mm, 45 * mm, 30 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), chrome),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F7")]),
        ("TEXTCOLOR", (3, 1), (3, -1), colors.HexColor("#AD1257")),
        ("FONTNAME", (3, 1), (3, -1), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D3DAE0")),
    ]))
    story.append(tbl)

    story.append(Paragraph("Contract checklist", hd))
    checks = [
        ("Standard tariff annexed", checklist.get("tariff_annexed")),
        ("Bid validity confirmed", checklist.get("validity")),
        ("Dock and slot confirmed", checklist.get("dock_confirmed")),
        ("Commercial terms agreed", checklist.get("terms")),
    ]
    cdata = [[("[x]" if ok else "[ ]"), label] for (label, ok) in checks]
    ctbl = Table(cdata, colWidths=[12 * mm, 158 * mm])
    ctbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2C7A57")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ctbl)

    if memo_note:
        story.append(Paragraph("Notes", hd))
        story.append(Paragraph(memo_note, body))

    story.append(Spacer(1, 16 * mm))
    story.append(Paragraph(
        "<i>Total Evaluated Cost = normalized bid + deviation + off-hire + VO exposure. "
        "Guide norms are planning-grade (Butler 2012; composite yard tariffs). This memo is a "
        "procurement recommendation, not a contract.</i>",
        ParagraphStyle("foot", parent=styles["Normal"], fontSize=8, textColor=ink2, leading=11)))

    doc.build(story)
    return buf.getvalue()
