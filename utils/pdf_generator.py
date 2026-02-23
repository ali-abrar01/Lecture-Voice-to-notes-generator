"""
utils/pdf_generator.py
=======================
Generates a downloadable PDF of the lecture notes.
Uses ReportLab (pure Python, no external tools needed).

TO INSTALL: pip install reportlab
"""

import os
import tempfile
import unicodedata
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER

# ── Colours ───────────────────────────────────────────────────────────────────
PRIMARY   = colors.HexColor('#4F46E5')
SECONDARY = colors.HexColor('#7C3AED')
LIGHT_BG  = colors.HexColor('#EEF2FF')
DARK_TEXT = colors.HexColor('#1E1B4B')
GRAY      = colors.HexColor('#6B7280')
WHITE     = colors.white


def safe_text(text) -> str:
    """Strip characters Helvetica cannot encode (emojis, CJK, etc.)."""
    if not text:
        return ""
    text = unicodedata.normalize('NFC', str(text))
    return ''.join(ch if ord(ch) <= 0x00FF else ' ' for ch in text)


def generate_pdf(data: dict) -> str:
    """
    Build a PDF from the notes data dict.

    Args:
        data: dict with keys transcript, summary, bullets, quiz, flashcards

    Returns:
        Path to the generated PDF file (in system temp dir).
    """
    # Create temp file to write PDF into
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    pdf_path = tmp.name
    tmp.close()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=2 * cm,
    )

    styles = _make_styles()
    story  = []

    # ── Title ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("LECTURE NOTES", styles['title']))
    story.append(Paragraph(
        "Generated on " + datetime.now().strftime('%B %d, %Y at %I:%M %p'),
        styles['subtitle']
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY))
    story.append(Spacer(1, 0.4 * cm))

    # ── Summary ───────────────────────────────────────────────────────────────
    try:
        if data.get('summary'):
            story.append(Paragraph("[SUMMARY]", styles['section_header']))
            story.append(Paragraph(safe_text(data['summary']), styles['body']))
            story.append(Spacer(1, 0.4 * cm))
    except Exception as exc:
        story.append(Paragraph("Summary error: " + str(exc), styles['body']))

    # ── Key Points ────────────────────────────────────────────────────────────
    try:
        bullets = data.get('bullets') or []
        if bullets:
            story.append(Paragraph("[KEY POINTS]", styles['section_header']))
            for idx, bullet in enumerate(bullets, 1):
                cleaned = safe_text(bullet)
                if cleaned.strip():
                    story.append(Paragraph(str(idx) + ".  " + cleaned, styles['bullet']))
            story.append(Spacer(1, 0.4 * cm))
    except Exception as exc:
        story.append(Paragraph("Key points error: " + str(exc), styles['body']))

    # ── Quiz Questions ────────────────────────────────────────────────────────
    try:
        quiz = data.get('quiz') or []
        if quiz:
            story.append(Paragraph("[QUIZ QUESTIONS]", styles['section_header']))
            for idx, item in enumerate(quiz, 1):
                q = safe_text(item.get('question', ''))
                a = safe_text(item.get('answer', ''))
                if not q:
                    continue
                block = [
                    Paragraph("Q" + str(idx) + ": " + q, styles['quiz_q']),
                    Paragraph("Answer: " + a,             styles['quiz_a']),
                    Spacer(1, 0.2 * cm),
                ]
                story.append(KeepTogether(block))
            story.append(Spacer(1, 0.4 * cm))
    except Exception as exc:
        story.append(Paragraph("Quiz error: " + str(exc), styles['body']))

    # ── Flashcards ────────────────────────────────────────────────────────────
    # NOTE: ROWBACKGROUNDS is NOT a valid ReportLab command.
    # We use a manual loop to set alternating row backgrounds instead.
    try:
        flashcards = data.get('flashcards') or []
        if flashcards:
            story.append(Paragraph("[FLASHCARDS]", styles['section_header']))

            # Build table: header row + one row per card
            table_data = [[
                Paragraph("TERM / CONCEPT",      styles['tbl_head']),
                Paragraph("DEFINITION / ANSWER", styles['tbl_head']),
            ]]

            for card in flashcards:
                front = safe_text(card.get('front', ''))
                back  = safe_text(card.get('back',  ''))
                if not front and not back:
                    continue
                table_data.append([
                    Paragraph(front, styles['tbl_cell']),
                    Paragraph(back,  styles['tbl_cell']),
                ])

            if len(table_data) > 1:
                # Alternating row colours — built with individual BACKGROUND
                # commands per row (ROWBACKGROUNDS does not exist in ReportLab)
                row_bg_cmds = []
                for row_i in range(1, len(table_data)):
                    bg = LIGHT_BG if row_i % 2 == 1 else WHITE
                    row_bg_cmds.append(
                        ('BACKGROUND', (0, row_i), (-1, row_i), bg)
                    )

                tbl = Table(table_data, colWidths=[8 * cm, 9 * cm], repeatRows=1)
                tbl.setStyle(TableStyle([
                    ('BACKGROUND',    (0, 0), (-1, 0), PRIMARY),
                    ('TEXTCOLOR',     (0, 0), (-1, 0), WHITE),
                    ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE',      (0, 0), (-1, 0), 10),
                    ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE',      (0, 1), (-1, -1), 9),
                    ('TEXTCOLOR',     (0, 1), (-1, -1), DARK_TEXT),
                    ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
                    ('TOPPADDING',    (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
                    *row_bg_cmds,
                ]))
                story.append(tbl)
                story.append(Spacer(1, 0.4 * cm))

    except Exception as exc:
        story.append(Paragraph("Flashcards error: " + str(exc), styles['body']))

    # ── Full Transcript ───────────────────────────────────────────────────────
    try:
        if data.get('transcript'):
            story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph("[FULL TRANSCRIPT]", styles['section_header']))
            story.append(Paragraph(safe_text(data['transcript']), styles['transcript']))
    except Exception as exc:
        story.append(Paragraph("Transcript error: " + str(exc), styles['body']))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Paragraph(
        "Generated by Lecture Voice-to-Notes Generator  |  "
        "Powered by ElevenLabs and HuggingFace",
        styles['footer']
    ))

    doc.build(story)
    return pdf_path


def _make_styles() -> dict:
    """Return all named ParagraphStyle objects. Uses only built-in PDF fonts."""
    return {
        'title': ParagraphStyle(
            'pdf_title', fontSize=22, textColor=PRIMARY,
            spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold',
        ),
        'subtitle': ParagraphStyle(
            'pdf_subtitle', fontSize=10, textColor=GRAY,
            spaceAfter=12, alignment=TA_CENTER, fontName='Helvetica',
        ),
        'section_header': ParagraphStyle(
            'pdf_section_header', fontSize=13, textColor=PRIMARY,
            spaceBefore=14, spaceAfter=8, fontName='Helvetica-Bold',
        ),
        'body': ParagraphStyle(
            'pdf_body', fontSize=10, textColor=DARK_TEXT,
            spaceAfter=6, leading=16, fontName='Helvetica',
        ),
        'bullet': ParagraphStyle(
            'pdf_bullet', fontSize=10, textColor=DARK_TEXT,
            spaceAfter=5, leftIndent=12, leading=15, fontName='Helvetica',
        ),
        'quiz_q': ParagraphStyle(
            'pdf_quiz_q', fontSize=10, textColor=SECONDARY,
            spaceAfter=3, fontName='Helvetica-Bold',
        ),
        'quiz_a': ParagraphStyle(
            'pdf_quiz_a', fontSize=10, textColor=DARK_TEXT,
            spaceAfter=4, leftIndent=14, fontName='Helvetica',
        ),
        'tbl_head': ParagraphStyle(
            'pdf_tbl_head', fontSize=10, textColor=WHITE,
            fontName='Helvetica-Bold', leading=14,
        ),
        'tbl_cell': ParagraphStyle(
            'pdf_tbl_cell', fontSize=9, textColor=DARK_TEXT,
            fontName='Helvetica', leading=13,
        ),
        'transcript': ParagraphStyle(
            'pdf_transcript', fontSize=9, textColor=GRAY,
            leading=14, spaceAfter=6, fontName='Helvetica',
        ),
        'footer': ParagraphStyle(
            'pdf_footer', fontSize=8, textColor=GRAY,
            alignment=TA_CENTER, spaceBefore=6,
            fontName='Helvetica-Oblique',
        ),
    }