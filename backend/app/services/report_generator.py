"""
ThermaCity — PDF Report Generator

Generates publication-ready PDF reports with:
  - Executive summary of heat vulnerability
  - Tier distribution charts
  - Top-risk areas table
  - Recommendations for urban planners

Designed for deployment — generates PDFs on the backend server,
no browser or frontend rendering required.
"""

import io
import logging
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

logger = logging.getLogger(__name__)

# Tier colors (RGB tuples for reportlab)
TIER_COLORS = {
    "Heat-Safe": colors.HexColor("#10b981"),
    "Caution": colors.HexColor("#fbbf24"),
    "Stressed": colors.HexColor("#f97316"),
    "Emergency": colors.HexColor("#ef4444"),
}
ACCENT = colors.HexColor("#60a5fa")
DARK_BG = colors.HexColor("#1e293b")
TEXT_PRIMARY = colors.HexColor("#1e293b")
TEXT_MUTED = colors.HexColor("#64748b")


def generate_report(
    summary: dict[str, Any],
    top_cells: list[dict[str, Any]] | None = None,
    year: int = 2024,
) -> bytes:
    """Generate a PDF report and return it as bytes.

    Parameters
    ----------
    summary : dict
        City-wide HVI summary from the /demo/summary endpoint.
    top_cells : list[dict], optional
        Top 10 highest-risk cells with their properties.
    year : int
        The year of the data.

    Returns
    -------
    bytes
        The generated PDF as a byte string.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'ThermaTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=TEXT_PRIMARY,
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    subtitle_style = ParagraphStyle(
        'ThermaSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=TEXT_MUTED,
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        'ThermaHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=TEXT_PRIMARY,
        spaceBefore=20,
        spaceAfter=10,
        fontName='Helvetica-Bold',
    )
    body_style = ParagraphStyle(
        'ThermaBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=TEXT_PRIMARY,
        leading=16,
    )
    kpi_style = ParagraphStyle(
        'ThermaKPI',
        parent=styles['Normal'],
        fontSize=24,
        textColor=ACCENT,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )

    elements = []

    # ── Title Page ────────────────────────────────────────────
    elements.append(Spacer(1, 3 * cm))
    elements.append(Paragraph("ThermaCity", title_style))
    elements.append(Paragraph(
        f"Heat Vulnerability Assessment Report — {year}",
        subtitle_style
    ))
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(
        width="100%", thickness=2, color=ACCENT, spaceAfter=20
    ))
    elements.append(Paragraph(
        "AI-powered heat vulnerability analysis for Pune, India. "
        "This report identifies the most heat-stressed areas using satellite imagery, "
        "machine learning predictions, and a composite Heat Vulnerability Index (HVI).",
        body_style
    ))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        ParagraphStyle('Date', parent=body_style, textColor=TEXT_MUTED, fontSize=10)
    ))

    # ── Executive Summary ─────────────────────────────────────
    elements.append(PageBreak())
    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=15))

    total = summary.get('total_cells', 0)
    avg_hvi = summary.get('avg_hvi', 0)
    avg_lst = summary.get('avg_lst', 0)
    emergency = summary.get('emergency_cells', 0)
    high_risk = summary.get('high_risk_cells', 0)
    tier_dist = summary.get('tier_distribution', {})

    # KPI Table
    kpi_data = [
        ['Total Grid Cells', 'Average HVI', 'Average LST', 'High-Risk Cells'],
        [f'{total:,}', f'{avg_hvi:.1f}', f'{avg_lst:.1f}°C', f'{high_risk:,}'],
    ]
    kpi_table = Table(kpi_data, colWidths=[3.5*cm]*4)
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_MUTED),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 18),
        ('TEXTCOLOR', (0, 1), (-1, 1), ACCENT),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('TOPPADDING', (0, 1), (-1, 1), 3),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 1 * cm))

    # ── Tier Distribution ─────────────────────────────────────
    elements.append(Paragraph("Vulnerability Tier Distribution", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=15))

    tiers_ordered = ['Heat-Safe', 'Caution', 'Stressed', 'Emergency']
    tier_values = [tier_dist.get(t, 0) for t in tiers_ordered]

    # Bar chart
    drawing = Drawing(400, 200)
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 30
    chart.width = 300
    chart.height = 150
    chart.data = [tier_values]
    chart.categoryAxis.categoryNames = tiers_ordered
    chart.categoryAxis.labels.fontName = 'Helvetica'
    chart.categoryAxis.labels.fontSize = 9
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(tier_values) * 1.2 if tier_values else 100
    chart.valueAxis.labels.fontName = 'Helvetica'
    chart.valueAxis.labels.fontSize = 8
    chart.bars[0].fillColor = ACCENT

    # Color each bar by tier
    for i, tier in enumerate(tiers_ordered):
        chart.bars[0].fillColor = None  # Reset

    drawing.add(chart)

    # Add colored legend
    legend_y = 190
    for i, tier in enumerate(tiers_ordered):
        x = 50 + i * 95
        drawing.add(Rect(x, legend_y, 12, 12, fillColor=TIER_COLORS[tier], strokeColor=None))
        drawing.add(String(x + 16, legend_y + 2, f"{tier}: {tier_dist.get(tier, 0):,}",
                          fontName='Helvetica', fontSize=8))

    elements.append(drawing)
    elements.append(Spacer(1, 1 * cm))

    # Tier table
    tier_table_data = [['Tier', 'Cell Count', 'Percentage', 'HVI Range']]
    ranges = {'Heat-Safe': '0–25', 'Caution': '26–50', 'Stressed': '51–75', 'Emergency': '76–100'}
    for tier in tiers_ordered:
        count = tier_dist.get(tier, 0)
        pct = (count / total * 100) if total > 0 else 0
        tier_table_data.append([tier, f'{count:,}', f'{pct:.1f}%', ranges[tier]])

    tier_table = Table(tier_table_data, colWidths=[3.5*cm, 3*cm, 2.5*cm, 2.5*cm])
    tier_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    elements.append(tier_table)

    # ── Top Risk Cells ────────────────────────────────────────
    if top_cells:
        elements.append(PageBreak())
        elements.append(Paragraph("Top 10 Highest-Risk Grid Cells", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=15))

        cell_table_data = [['#', 'Cell ID', 'LST (°C)', 'NDVI', 'HVI Score', 'Tier']]
        for i, cell in enumerate(top_cells[:10], 1):
            cell_table_data.append([
                str(i),
                str(cell.get('cell_id', '—')),
                f"{cell.get('lst_predicted', 0):.1f}",
                f"{cell.get('ndvi', 0):.3f}",
                f"{cell.get('hvi_score', 0):.1f}",
                cell.get('hvi_tier', '—'),
            ])

        cell_table = Table(cell_table_data, colWidths=[1*cm, 3*cm, 2.5*cm, 2*cm, 2.5*cm, 2.5*cm])
        cell_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(cell_table)

    # ── Recommendations ───────────────────────────────────────
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph("Recommendations", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=15))

    recommendations = [
        "<b>Priority Afforestation:</b> Focus tree planting in Emergency and Stressed zones to reduce LST by 2–5°C through shade and evapotranspiration.",
        "<b>Cool Roof Mandates:</b> Implement reflective roofing policies in high-NDBI cells to reduce heat absorption by up to 30%.",
        "<b>Water Body Restoration:</b> Restore and create urban water features in cells with low NDWI to leverage evaporative cooling.",
        "<b>Early Warning Systems:</b> Deploy heat-health alerts in Emergency-tier wards during April–June to protect vulnerable populations.",
        "<b>Monitoring:</b> Schedule monthly satellite data updates to track intervention effectiveness and temporal heat trends.",
    ]
    for rec in recommendations:
        elements.append(Paragraph(f"• {rec}", body_style))
        elements.append(Spacer(1, 3 * mm))

    # ── Footer ────────────────────────────────────────────────
    elements.append(Spacer(1, 2 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=TEXT_MUTED, spaceAfter=10))
    elements.append(Paragraph(
        "ThermaCity — AI-Powered Heat Vulnerability Mapping | Pune, India",
        ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=TEXT_MUTED, alignment=TA_CENTER)
    ))

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info("PDF report generated: %d bytes", len(pdf_bytes))
    return pdf_bytes

def generate_cell_report(req: dict[str, Any]) -> bytes:
    """Generate a single-cell PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=24, textColor=TEXT_PRIMARY, spaceAfter=6, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=12, textColor=TEXT_MUTED, spaceAfter=20)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, textColor=TEXT_PRIMARY, spaceBefore=20, spaceAfter=10, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, textColor=TEXT_PRIMARY, leading=16)

    elements = []

    # Title
    elements.append(Paragraph(f"Block Assessment Report", title_style))
    elements.append(Paragraph(f"Cell ID: {req['cell_id']} | Year: {req['year']}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=20))

    # Baseline Status
    elements.append(Paragraph("Baseline Status", heading_style))
    kpi_data = [
        ['LST (°C)', 'HVI Score', 'Risk Tier', 'NDVI (Veg)', 'NDBI (Built)'],
        [f"{req['baseline_lst']:.1f}°C", f"{req['baseline_hvi_score']:.1f}", req['baseline_hvi_tier'], f"{req['baseline_ndvi']:.3f}", f"{req['baseline_ndbi']:.3f}"]
    ]
    kpi_table = Table(kpi_data, colWidths=[3*cm]*5)
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_MUTED),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('TEXTCOLOR', (0, 1), (-1, 1), TEXT_PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('TOPPADDING', (0, 1), (-1, 1), 3),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 1 * cm))

    # Simulation Impact
    if req.get('simulated_lst') is not None:
        elements.append(Paragraph("Simulation Impact", heading_style))
        elements.append(Paragraph(f"Interventions applied: +{req.get('applied_canopy_delta', 0)*100}% Canopy, -{req.get('applied_ndbi_delta', 0)*100}% Built-up (Cool Roofs).", body_style))
        elements.append(Spacer(1, 0.5 * cm))
        
        sim_data = [
            ['Simulated LST', 'LST Change', 'New Tier'],
            [f"{req['simulated_lst']:.1f}°C", f"{req['lst_delta']:+.1f}°C", req['simulated_hvi_tier']]
        ]
        sim_table = Table(sim_data, colWidths=[5*cm]*3)
        sim_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_MUTED),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor("#10b981") if req['lst_delta'] < 0 else TEXT_PRIMARY),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
            ('TOPPADDING', (0, 1), (-1, 1), 3),
        ]))
        elements.append(sim_table)
    else:
        elements.append(Paragraph("No simulation interventions applied to this block.", body_style))

    # Footer
    elements.append(Spacer(1, 2 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=TEXT_MUTED, spaceAfter=10))
    elements.append(Paragraph(f"ThermaCity | Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}", ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=TEXT_MUTED, alignment=TA_CENTER)))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
