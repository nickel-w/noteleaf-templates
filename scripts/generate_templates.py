"""
Noteleaf – A5 Template Generator
===================================
Generates print-ready A5 PDF templates for the Noteleaf system.

Each template contains:
  - Four black circular crosshair "registration target" corner markers for
    perspective correction during scanning (see `_draw_markers`; a square
    marker style also exists for older printed sheets predating this one)
  - A QR code encoding the template type and version
  - A unique geometric type symbol (bottom-left) for secondary recognition
  - Structured content zones that the Noteleaf Nextcloud app processes with OCR

Symbol legend (bottom-left box, 18×18 mm):
  daily      → clock face (ring + 12 ticks + centre dot)
  weekly     → 7 vertical bars (Sa/So slightly shorter)
  checklist  → bold checkmark
  notes      → 5×5 dot grid
  meeting    → 4 horizontal strokes (last one shorter), reads as notes lines
  dailyWide  → clock face + 3 small footer blocks (time / tasks / notes columns)

Usage
-----
  # Generate all blank templates
  python scripts/generate_templates.py

  # Generate a single prefilled daily template
  from scripts.generate_templates import make_tagesplan
  make_tagesplan(
      "out.pdf",
      date_str="Fr, 11. April 2026",
      events=[{"time": "07:00", "title": "Standup"}],
      tasks=[{"title": "PR reviewen", "completed": False}],
  )

QR payload format and content zones are defined in ../templates/manifest.json,
which is the single source of truth shared with the Noteleaf Nextcloud app
(nickel-w/noteleaf, lib/Service/Scan/ScanTemplateRegistry.php is generated
from that manifest — see that repo's bin/generate-scan-registry.php). Keep
the drawing geometry below visually consistent with the zone boxes declared
in manifest.json whenever you change a layout; the manifest, not this
docstring, is what noteleaf's scan code is generated against.

Dependencies:  pip install -r requirements.txt
"""

from __future__ import annotations

import io
import json
import math
import os
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode

_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "manifest.json")
_manifest_cache: dict[str, Any] | None = None


def _load_manifest() -> dict[str, Any]:
    """Loads templates/manifest.json — the shared source of truth for QR
    payloads and content zones (also consumed by noteleaf's PHP codegen)."""
    global _manifest_cache
    if _manifest_cache is None:
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            _manifest_cache = json.load(f)
    return _manifest_cache


def _qr_payload(template_type: str) -> str:
    for tmpl in _load_manifest()["templates"]:
        if tmpl["type"] == template_type:
            return tmpl["qrPayload"]
    raise KeyError(f"No manifest entry for template type {template_type!r}")

# ── Page dimensions ──────────────────────────────────────────────────────────
W, H = A5   # 419.53 × 595.28 pt  (ReportLab units, portrait A5)

# ── Design tokens ────────────────────────────────────────────────────────────
MARGIN      = 10 * mm
MARKER_SIZE =  5 * mm
QR_SIZE     = 18 * mm
BOTTOM_SAFE = MARGIN + MARKER_SIZE + QR_SIZE + 4 * mm

FONT_BOLD = "Helvetica-Bold"
FONT_BODY = "Helvetica"

C_BLACK      = colors.HexColor("#1a1a1a")
C_DARK       = colors.HexColor("#444444")
C_MID        = colors.HexColor("#888888")
C_LIGHT      = colors.HexColor("#cccccc")
C_XLIGHT     = colors.HexColor("#eeeeee")
C_PREFILL_BG = colors.HexColor("#ddeeff")
C_PREFILL_FG = colors.HexColor("#4a80b0")
C_CHECK      = colors.HexColor("#1D9E75")
C_HEADER_BG  = colors.HexColor("#f4f4f4")


# ── Low-level helpers ────────────────────────────────────────────────────────

def _qr_image(data: str) -> ImageReader:
    qr = qrcode.QRCode(version=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _draw_registration_target(c: canvas.Canvas, cx: float, cy: float) -> None:
    """Circular crosshair 'registration target' marker (newer marker style),
    centred at (cx, cy), sized to fit the same MARKER_SIZE box as the square
    markers."""
    r_outer = MARKER_SIZE / 2 * 0.86
    r_dot   = MARKER_SIZE / 2 * 0.26
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.35 * mm)
    c.circle(cx, cy, r_outer, fill=0, stroke=1)
    c.setLineWidth(0.25 * mm)
    c.line(cx, cy - MARKER_SIZE / 2, cx, cy + MARKER_SIZE / 2)
    c.line(cx - MARKER_SIZE / 2, cy, cx + MARKER_SIZE / 2, cy)
    c.setFillColor(C_BLACK)
    c.circle(cx, cy, r_dot, fill=1, stroke=0)


def _draw_markers(c: canvas.Canvas, style: str = "target", *,
                  page_w: float = W, page_h: float = H) -> None:
    """Draws the four corner registration markers.

    style: "target" (current default, circular crosshair registration
    targets) or "square" (black 5×5 mm squares, the older style kept only
    for reference) — see module docstring.
    """
    corners = [
        (MARGIN,                       MARGIN),
        (page_w - MARGIN - MARKER_SIZE, MARGIN),
        (MARGIN,                       page_h - MARGIN - MARKER_SIZE),
        (page_w - MARGIN - MARKER_SIZE, page_h - MARGIN - MARKER_SIZE),
    ]
    if style == "target":
        for x, y in corners:
            _draw_registration_target(c, x + MARKER_SIZE / 2, y + MARKER_SIZE / 2)
    else:
        c.setFillColor(C_BLACK)
        for x, y in corners:
            c.rect(x, y, MARKER_SIZE, MARKER_SIZE, fill=1, stroke=0)


def _draw_qr(c: canvas.Canvas, payload: str, *, page_w: float = W) -> None:
    c.drawImage(_qr_image(payload),
                page_w - MARGIN - QR_SIZE, MARGIN, QR_SIZE, QR_SIZE)


def _draw_footer(c: canvas.Canvas, template_id: str, *, page_w: float = W) -> None:
    c.setFont(FONT_BODY, 5)
    c.setFillColor(C_LIGHT)
    c.drawCentredString(page_w / 2, MARGIN + 1 * mm,
                        f"{_qr_payload(template_id)} · A5")


# ── Type symbol ──────────────────────────────────────────────────────────────

def _draw_type_symbol(c: canvas.Canvas, template_type: str) -> None:
    """
    Draws a unique machine-readable geometric symbol identifying the template.

    Position: bottom-left corner, same size as QR code (18 × 18 mm).
    The Scan-App uses this symbol as a secondary recognition marker when
    the QR code is not readable (e.g. obscured ink, torn corner).

    Symbol designs
    ──────────────
    daily     : clock face – outer ring + 12 radial ticks + filled centre dot
    weekly    : 7 vertical bars (weekday bars full-height, weekend bars shorter)
    checklist : bold L-shaped checkmark
    notes     : 5 × 5 dot grid (matches printed dot-grid pattern)
    meeting   : 4 horizontal strokes, last one shorter (reads as notes lines,
                not a task list)
    dailyWide : small clock face + 3 footer blocks (time / tasks / notes
                columns), signalling the three-column landscape layout
    """
    sx = MARGIN           # symbol box origin x (same x as left marker)
    sy = MARGIN           # symbol box origin y (same y as QR code)
    s  = QR_SIZE          # 18 mm

    pad = 2.2 * mm        # inner padding inside the border box
    ix  = sx + pad
    iy  = sy + pad
    iw  = s - 2 * pad
    ih  = s - 2 * pad
    cxs = ix + iw / 2     # inner centre x
    cys = iy + ih / 2     # inner centre y

    # ── border box (same visual weight as QR code border) ────────────────
    c.setStrokeColor(C_BLACK)
    c.setFillColor(colors.white)
    c.setLineWidth(0.8)
    c.rect(sx, sy, s, s, fill=1, stroke=1)

    c.setFillColor(C_BLACK)
    c.setStrokeColor(C_BLACK)

    # ── per-type drawing ──────────────────────────────────────────────────
    if template_type == "daily":
        # Clock face: outer ring, 12 hour ticks, filled centre dot
        r_outer = iw / 2
        r_tick_in = r_outer * 0.62   # inner end of hour tick
        r_tick_in_half = r_outer * 0.78  # inner end of half-hour tick

        c.setLineWidth(0.9)
        c.circle(cxs, cys, r_outer, fill=0, stroke=1)

        for i in range(12):
            angle = math.radians(90 - i * 30)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            r_in = r_tick_in if i % 3 == 0 else r_tick_in_half
            lw   = 1.0       if i % 3 == 0 else 0.45
            c.setLineWidth(lw)
            c.line(cxs + r_in    * cos_a, cys + r_in    * sin_a,
                   cxs + r_outer * cos_a, cys + r_outer * sin_a)

        # Filled centre dot
        c.circle(cxs, cys, 1.0 * mm, fill=1, stroke=0)

        # Short clock hand pointing to ~10 o'clock (decorative)
        hand_angle = math.radians(90 + 60)   # 10 o'clock direction
        c.setLineWidth(1.0)
        c.line(cxs, cys,
               cxs + r_outer * 0.50 * math.cos(hand_angle),
               cys + r_outer * 0.50 * math.sin(hand_angle))

    elif template_type == "weekly":
        # 7 vertical bars: Mon–Fri full height, Sat–Sun at 60 %
        n     = 7
        gap   = 0.7 * mm
        bar_w = (iw - gap * (n - 1)) / n

        for i in range(n):
            h_frac = 0.60 if i >= 5 else 1.0
            bh = ih * h_frac
            bx = ix + i * (bar_w + gap)
            by = iy  # align to bottom
            c.rect(bx, by, bar_w, bh, fill=1, stroke=0)

        # Thin separator line between weekdays and weekend
        sep_x = ix + 5 * (bar_w + gap) - gap / 2
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.8)
        c.line(sep_x, iy, sep_x, iy + ih)
        c.setStrokeColor(C_BLACK)

    elif template_type == "checklist":
        # Bold checkmark: thin arm + thick arm, classic tick shape
        lw = 2.2
        c.setLineWidth(lw)
        c.setLineCap(1)   # round caps

        # Checkmark vertices (relative to inner box)
        p1x = ix + iw * 0.08;  p1y = iy + ih * 0.52
        p2x = ix + iw * 0.38;  p2y = iy + ih * 0.16
        p3x = ix + iw * 0.92;  p3y = iy + ih * 0.84

        p = c.beginPath()
        p.moveTo(p1x, p1y)
        p.lineTo(p2x, p2y)
        p.lineTo(p3x, p3y)
        c.drawPath(p, stroke=1, fill=0)
        c.setLineCap(0)

    elif template_type == "notes":
        # 5 × 5 dot grid – mirrors the printed dot-grid of the notes page
        n   = 5
        r   = 0.75 * mm
        gx  = iw / (n - 1)
        gy  = ih / (n - 1)

        for row in range(n):
            for col in range(n):
                dx = ix + col * gx
                dy = iy + row * gy
                c.circle(dx, dy, r, fill=1, stroke=0)

    elif template_type == "meeting":
        # 4 horizontal strokes, last one shorter — reads as notes lines
        lw = 1.1 * mm
        c.setLineWidth(lw)
        c.setLineCap(2)   # square caps
        fracs_y = [0.85, 0.62, 0.39, 0.16]
        fracs_x2 = [1.0, 1.0, 0.72, 0.89]
        for fy, fx2 in zip(fracs_y, fracs_x2):
            yy = iy + ih * fy
            c.line(ix, yy, ix + iw * fx2, yy)
        c.setLineCap(0)

    elif template_type == "dailyWide":
        # Small clock face (top) + 3 footer blocks (time / tasks / notes)
        r_outer = iw * 0.30
        ccx, ccy = ix + iw * 0.5, iy + ih * 0.62
        c.setLineWidth(0.9)
        c.circle(ccx, ccy, r_outer, fill=0, stroke=1)
        for i in range(4):
            angle = math.radians(90 - i * 90)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            r_in = r_outer * 0.6
            c.setLineWidth(1.0)
            c.line(ccx + r_in * cos_a, ccy + r_in * sin_a,
                   ccx + r_outer * cos_a, ccy + r_outer * sin_a)
        c.circle(ccx, ccy, 0.9 * mm, fill=1, stroke=0)
        c.line(ccx, ccy, ccx - r_outer * 0.5, ccy - r_outer * 0.3)

        n     = 3
        gap   = 0.9 * mm
        block_w = (iw - gap * (n - 1)) / n
        block_h = ih * 0.2
        by = iy
        for i in range(n):
            bx = ix + i * (block_w + gap)
            c.rect(bx, by, block_w, block_h, fill=1, stroke=0)


def _header_bar(c: canvas.Canvas, title: str, subtitle: str = "", *,
                page_w: float = W, page_h: float = H) -> float:
    """Draws header; returns bottom y of header (= top of content area)."""
    bx = MARGIN + MARKER_SIZE + 3 * mm
    bw = page_w - 2 * (MARGIN + MARKER_SIZE + 3 * mm)
    by = page_h - MARGIN - MARKER_SIZE - 2 * mm - 8 * mm
    c.setFillColor(C_HEADER_BG)
    c.rect(bx, by, bw, 8 * mm, fill=1, stroke=0)
    c.setFillColor(C_BLACK)
    c.setFont(FONT_BOLD, 9)
    c.drawString(bx + 3 * mm, by + 2.8 * mm, title)
    if subtitle:
        c.setFont(FONT_BODY, 7)
        c.setFillColor(C_MID)
        c.drawRightString(bx + bw - 3 * mm, by + 2.8 * mm, subtitle)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.6)
    c.line(bx, by, bx + bw, by)
    return by


def _section_label(c: canvas.Canvas, x: float, y: float, text: str) -> None:
    c.setFont(FONT_BOLD, 6)
    c.setFillColor(C_MID)
    c.drawString(x, y, text.upper())
    c.setStrokeColor(C_XLIGHT)
    c.setLineWidth(0.3)
    c.line(x, y - 0.8 * mm, x + 35 * mm, y - 0.8 * mm)


def _hline(c, x1, x2, y, color=None, lw=0.25):
    c.setStrokeColor(color or C_XLIGHT)
    c.setLineWidth(lw)
    c.line(x1, y, x2, y)


def _vline(c, x, y1, y2, color=None, lw=0.25):
    c.setStrokeColor(color or C_XLIGHT)
    c.setLineWidth(lw)
    c.line(x, y1, x, y2)


def _checkbox(c, x, y, size=2.8*mm, checked=False, bg=None):
    if bg:
        c.setFillColor(bg)
        c.rect(x, y, size, size, fill=1, stroke=0)
    c.setStrokeColor(C_DARK)
    c.setLineWidth(0.4)
    c.rect(x, y, size, size, fill=0, stroke=1)
    if checked:
        c.setStrokeColor(C_CHECK)
        c.setLineWidth(0.8)
        c.line(x+0.4*mm, y+1.4*mm, x+1.0*mm, y+0.5*mm)
        c.line(x+1.0*mm, y+0.5*mm, x+2.4*mm, y+2.2*mm)


def _content_cols():
    """Returns (col_left, col_split, col2_left, col_right)."""
    cl = MARGIN + MARKER_SIZE + 3 * mm
    cs = cl + 56 * mm
    c2 = cs + 2 * mm
    cr = W - MARGIN - MARKER_SIZE - 3 * mm - QR_SIZE - 2 * mm
    return cl, cs, c2, cr


def _new_canvas(path: str) -> canvas.Canvas:
    c = canvas.Canvas(path, pagesize=A5)
    c.setTitle("Noteleaf Template")
    c.setAuthor("Noteleaf")
    return c


# ══════════════════════════════════════════════════════════════════════════════
#  Template 1 – Tagesplan
# ══════════════════════════════════════════════════════════════════════════════

def make_tagesplan(path: str, date_str: str = "", *,
                   events: list[dict] | None = None,
                   tasks:  list[dict] | None = None) -> None:
    """
    Daily planner A5 PDF.

    Parameters
    ----------
    path      : output file path
    date_str  : header date label, e.g. "Fr, 11. April 2026"
    events    : list of {"time": "HH:MM", "title": str}
    tasks     : list of {"title": str, "completed": bool}
    """
    events = events or []
    tasks  = tasks  or []

    c = _new_canvas(path)
    _draw_qr(c, _qr_payload("daily"))
    _draw_type_symbol(c, "daily")
    _draw_footer(c, "daily")
    _draw_markers(c)
    top = _header_bar(c, "Tagesplan", date_str or "________________")

    cl, cs, c2, _ = _content_cols()
    # Task list & notes column run to the header bar's right edge (130 mm)
    # rather than stopping short for the QR carve-out — both zones end well
    # above BOTTOM_SAFE, so there is no overlap with the QR code.
    cr_wide  = W - MARGIN - MARKER_SIZE - 3 * mm
    ct       = top - 3 * mm
    row_h    = 5.5 * mm
    time_w   = 9 * mm
    cb_size  = 2.8 * mm

    # event lookup: slot string -> event
    ev_lookup: dict[str, dict] = {}
    for ev in events:
        try:
            h, m = map(int, ev["time"].split(":"))
        except (KeyError, ValueError):
            continue
        ev_lookup[f"{h:02d}:{'30' if m >= 30 else '00'}"] = ev

    # ── Left: time grid ──────────────────────────────────────────────────────
    _section_label(c, cl, ct, "Zeitplan")
    y     = ct - 4 * mm
    slots = [f"{h:02d}:{m:02d}" for h in range(6, 22) for m in (0, 30)]
    drawn = 0

    for i, slot in enumerate(slots):
        ry = y - i * row_h
        if ry - row_h < BOTTOM_SAFE:
            break
        drawn += 1

        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#fafafa"))
            c.rect(cl, ry - row_h + 0.5*mm, cs - cl, row_h - 0.5*mm, fill=1, stroke=0)

        if slot in ev_lookup:
            ev = ev_lookup[slot]
            c.setFillColor(C_PREFILL_BG)
            c.rect(cl + time_w, ry - row_h + 0.5*mm,
                   cs - cl - time_w, row_h - 0.5*mm, fill=1, stroke=0)
            c.setFont(FONT_BODY, 6.5)
            c.setFillColor(C_PREFILL_FG)
            c.drawString(cl + time_w + 1*mm, ry - row_h + 1.5*mm,
                         str(ev.get("title", ""))[:28])

        c.setFont(FONT_BODY, 6)
        c.setFillColor(C_MID)
        c.drawString(cl, ry - row_h + 1.8*mm, slot)
        _hline(c, cl + time_w, cs, ry - row_h + 0.5*mm)

    box_h = drawn * row_h
    c.setStrokeColor(C_LIGHT)
    c.setLineWidth(0.4)
    c.rect(cl, y - box_h, cs - cl, box_h, fill=0, stroke=1)
    _vline(c, cl + time_w, y, y - box_h, C_LIGHT, 0.4)

    # ── Right: tasks ─────────────────────────────────────────────────────────
    _section_label(c, c2, ct, "Aufgaben")
    ty        = ct - 4 * mm
    task_row  = 6 * mm
    num_tasks = 9

    for i in range(num_tasks):
        ry   = ty - i * task_row
        task = tasks[i] if i < len(tasks) else None
        done = bool(task.get("completed", False)) if task else False
        _checkbox(c, c2, ry - cb_size, checked=done,
                  bg=colors.HexColor("#e8fff5") if done else None)
        if task:
            c.setFont(FONT_BODY, 7.5)
            c.setFillColor(C_MID if done else C_DARK)
            c.drawString(c2 + cb_size + 1.5*mm, ry - cb_size + 0.3*mm,
                         str(task.get("title", ""))[:30])
        else:
            _hline(c, c2 + cb_size + 1.5*mm, cr_wide, ry - cb_size + 0.5*mm, C_XLIGHT)
        _hline(c, c2, cr_wide, ry - task_row + 0.3*mm, C_XLIGHT, 0.15)

    # ── Right: notes (light dot grid, borderless) ────────────────────────────
    nt = ty - num_tasks * task_row - 3 * mm
    _section_label(c, c2, nt, "Notizen")
    notes_top = nt - 4 * mm
    dot_gap   = 5 * mm
    c.setFillColor(C_LIGHT)
    x = c2
    while x <= cr_wide:
        y = BOTTOM_SAFE
        while y <= notes_top:
            c.circle(x, y, 0.4*mm, fill=1, stroke=0)
            y += dot_gap
        x += dot_gap
    c.save()


# ══════════════════════════════════════════════════════════════════════════════
#  Template 2 – Wochenplan
# ══════════════════════════════════════════════════════════════════════════════

def make_wochenplan(path: str, week_str: str = "", *,
                    events: list[dict] | None = None) -> None:
    """
    Weekly planner A5 PDF.

    Parameters
    ----------
    path      : output file path
    week_str  : header label, e.g. "KW 15 · 07.–13. April 2026"
    events    : list of {"date": "yyyy-mm-dd", "time": "HH:MM", "title": str}
    """
    events = events or []
    c = _new_canvas(path)
    _draw_qr(c, _qr_payload("weekly"))
    _draw_type_symbol(c, "weekly")
    _draw_footer(c, "weekly")
    _draw_markers(c)
    top = _header_bar(c, "Wochenplan", week_str or "KW ____")

    cl = MARGIN + MARKER_SIZE + 3 * mm
    cr = W - MARGIN - MARKER_SIZE - 3 * mm
    ct = top - 3 * mm
    cb = BOTTOM_SAFE

    days      = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    col_w     = (cr - cl) / 7
    hdr_h     = 5 * mm
    row_count = 15
    row_h     = (ct - cb - hdr_h) / row_count

    for i, day in enumerate(days):
        x    = cl + i * col_w
        fill = colors.HexColor("#f8eeee") if i >= 5 else C_HEADER_BG
        c.setFillColor(fill)
        c.rect(x, ct - hdr_h, col_w, hdr_h, fill=1, stroke=0)
        c.setFont(FONT_BOLD, 7)
        c.setFillColor(colors.HexColor("#aa4444") if i >= 5 else C_BLACK)
        c.drawCentredString(x + col_w/2, ct - hdr_h + 1.5*mm, day)
        c.setFont(FONT_BODY, 5.5)
        c.setFillColor(C_MID)
        c.drawCentredString(x + col_w/2, ct - hdr_h + 4*mm, "__.__")

    hours = [f"{h:02d}" for h in range(7, 22)]
    for row in range(row_count):
        y     = ct - hdr_h - (row + 1) * row_h
        color = C_LIGHT if row % 2 == 0 else C_XLIGHT
        lw    = 0.4   if row % 2 == 0 else 0.2
        if row < len(hours):
            c.setFont(FONT_BODY, 5)
            c.setFillColor(C_MID)
            c.drawString(cl + 0.5*mm, y + 0.8*mm, hours[row])
        _hline(c, cl, cr, y, color, lw)

    for i in range(8):
        _vline(c, cl + i * col_w, ct - hdr_h, cb, C_LIGHT, 0.4)

    c.setStrokeColor(C_LIGHT); c.setLineWidth(0.5)
    c.rect(cl, cb, cr - cl, ct - cb, fill=0, stroke=1)
    c.setStrokeColor(C_BLACK); c.setLineWidth(0.5)
    c.line(cl, ct - hdr_h, cr, ct - hdr_h)
    c.save()


# ══════════════════════════════════════════════════════════════════════════════
#  Template 3 – Checkliste
# ══════════════════════════════════════════════════════════════════════════════

def make_checkliste(path: str, *,
                    groups: list[dict] | None = None) -> None:
    """
    Checklist A5 PDF with grouped task rows.

    Parameters
    ----------
    path   : output file path
    groups : list of {"label": str, "tasks": [{"title": str, "completed": bool}],
                      "n_rows": int}
             n_rows is used when tasks list is shorter than desired blank rows.
    """
    default = [
        {"label": "Kategorie", "n_rows": 6},
        {"label": "Kategorie", "n_rows": 6},
        {"label": "Kategorie", "n_rows": 5},
    ]
    groups = groups or default

    c = _new_canvas(path)
    _draw_qr(c, _qr_payload("checklist"))
    _draw_type_symbol(c, "checklist")
    _draw_footer(c, "checklist")
    _draw_markers(c)
    top = _header_bar(c, "Checkliste", "________________")

    cl, _, _, cr = _content_cols()
    ct  = top - 3 * mm
    y   = ct - 4 * mm
    rh  = 6.5 * mm
    cbs = 3.0 * mm

    _section_label(c, cl, ct, "Aufgaben")

    for grp in groups:
        if y - 4*mm < BOTTOM_SAFE:
            break
        label = grp.get("label", "Kategorie")
        tasks = grp.get("tasks", [])
        n     = max(grp.get("n_rows", 6), len(tasks))

        c.setFont(FONT_BOLD, 6.5); c.setFillColor(C_MID)
        c.drawString(cl, y, label)
        c.setStrokeColor(C_XLIGHT); c.setLineWidth(0.3)
        c.line(cl + 18*mm, y + 1*mm, cr, y + 1*mm)
        y -= 4 * mm

        for idx in range(n):
            if y - rh < BOTTOM_SAFE:
                break
            t    = tasks[idx] if idx < len(tasks) else None
            done = bool(t.get("completed", False)) if t else False
            _checkbox(c, cl, y - cbs, size=cbs, checked=done)
            if t:
                c.setFont(FONT_BODY, 8); c.setFillColor(C_MID if done else C_DARK)
                c.drawString(cl + cbs + 2*mm, y - cbs + 0.3*mm,
                             str(t.get("title", ""))[:35])
            else:
                _hline(c, cl + cbs + 2*mm, cr, y - cbs + 0.5*mm, C_XLIGHT)
            _hline(c, cl, cr, y - rh + 0.3*mm, C_XLIGHT, 0.15)
            y -= rh
        y -= 2 * mm
    c.save()


# ══════════════════════════════════════════════════════════════════════════════
#  Template 4 – Notizseite
# ══════════════════════════════════════════════════════════════════════════════

def make_notizseite(path: str, *, title: str = "", tags: str = "") -> None:
    """
    Dot-grid notes page A5 PDF.

    Parameters
    ----------
    path  : output file path
    title : pre-filled title text
    tags  : pre-filled tags text
    """
    c = _new_canvas(path)
    _draw_qr(c, _qr_payload("notes"))
    _draw_type_symbol(c, "notes")
    _draw_footer(c, "notes")
    _draw_markers(c)
    top = _header_bar(c, "Notizen", "________________")

    cl, _, _, cr = _content_cols()
    ct = top - 3 * mm

    for offset, label, value, max_chars in [
        (0,       "Titel", title, 50),
        (-5*mm,   "Tags",  tags,  60),
    ]:
        c.setFont(FONT_BODY, 6.5); c.setFillColor(C_MID)
        c.drawString(cl, ct + offset, label)
        if value:
            c.setFont(FONT_BODY, 8); c.setFillColor(C_DARK)
            c.drawString(cl + 8*mm, ct + offset, str(value)[:max_chars])
        c.setStrokeColor(C_DARK if not value else C_XLIGHT)
        c.setLineWidth(0.5 if not value else 0.3)
        c.line(cl + 8*mm, ct + offset + 1.5*mm, cr, ct + offset + 1.5*mm)

    grid_top = ct - 11 * mm
    dot_gap  = 5 * mm
    c.setFillColor(C_LIGHT)
    x = cl
    while x <= cr:
        y = BOTTOM_SAFE
        while y <= grid_top:
            c.circle(x, y, 0.4*mm, fill=1, stroke=0)
            y += dot_gap
        x += dot_gap

    c.setStrokeColor(C_XLIGHT); c.setLineWidth(0.4)
    c.rect(cl, BOTTOM_SAFE, cr - cl, grid_top - BOTTOM_SAFE, fill=0, stroke=1)
    c.save()


# ══════════════════════════════════════════════════════════════════════════════
#  Template 5 – Meeting-Notizen
# ══════════════════════════════════════════════════════════════════════════════

def make_meeting_notizen(path: str, *, topic: str = "", when: str = "",
                         participants: str = "",
                         action_items: list[dict] | None = None) -> None:
    """
    Meeting notes A5 PDF. New template type, noteleaf://meeting/v1.

    On scan, the notes area becomes a note and each filled action-item row
    becomes a task (checkbox title, "Wer" assignee, "Bis" due date).

    Parameters
    ----------
    path          : output file path
    topic         : meeting topic ("Thema")
    when          : date/time header field, e.g. "11.04.2026 · 09:00-09:30"
    participants  : "Teilnehmer" field
    action_items  : list of {"title": str, "who": str, "due": str, "completed": bool}
    """
    action_items = action_items or []

    c = _new_canvas(path)
    _draw_qr(c, _qr_payload("meeting"))
    _draw_type_symbol(c, "meeting")
    _draw_footer(c, "meeting")
    _draw_markers(c)

    cl = MARGIN + MARKER_SIZE + 3 * mm
    cr = W - MARGIN - MARKER_SIZE - 3 * mm
    y  = H - MARGIN - MARKER_SIZE - 2 * mm - 6 * mm

    c.setFont(FONT_BOLD, 15)
    c.setFillColor(C_BLACK)
    c.drawString(cl, y, "Meeting")
    c.setFont(FONT_BODY, 7)
    c.setFillColor(C_DARK if when else C_MID)
    c.drawRightString(cr, y + 0.8 * mm, when or "Datum · Uhrzeit")
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.3)
    c.line(cr - 44 * mm, y - 0.8 * mm, cr, y - 0.8 * mm)

    y -= 8 * mm
    for label, value in [("Thema", topic), ("Teilnehmer", participants)]:
        c.setFont(FONT_BODY, 7)
        c.setFillColor(C_DARK if value else C_MID)
        c.drawString(cl, y, value or label)
        c.setStrokeColor(C_BLACK)
        c.setLineWidth(0.3)
        c.line(cl, y - 1 * mm, cr, y - 1 * mm)
        y -= 7 * mm

    # ── Fixed-height action items block, anchored above BOTTOM_SAFE ─────────
    action_rows      = 4
    action_row_h     = 9.5 * mm
    action_hdr_h     = 4.5 * mm
    action_label_h   = 8 * mm
    action_block_h   = action_label_h + action_hdr_h + action_rows * action_row_h
    ai_top           = BOTTOM_SAFE + action_block_h

    col_cb_w  = 7 * mm
    col_who_w = 24 * mm
    col_due_w = 18 * mm
    who_x     = cr - col_who_w - col_due_w
    due_x     = cr - col_due_w

    c.setFont(FONT_BODY, 7)
    c.setFillColor(C_BLACK)
    c.drawString(cl, ai_top - 4 * mm, "ACTION ITEMS")

    hdr_y = ai_top - action_label_h
    c.setFont(FONT_BODY, 5.5)
    c.setFillColor(C_MID)
    c.drawString(cl + col_cb_w, hdr_y, "WAS")
    c.drawString(who_x + 1 * mm, hdr_y, "WER")
    c.drawString(due_x + 1 * mm, hdr_y, "BIS")

    row_top = hdr_y - action_hdr_h + 2 * mm
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.3)
    c.line(cl, row_top, cr, row_top)

    cb_size = 4.5 * mm
    for i in range(action_rows):
        item      = action_items[i] if i < len(action_items) else None
        done      = bool(item.get("completed", False)) if item else False
        row_bot   = row_top - action_row_h
        _checkbox(c, cl + 1 * mm, row_top - action_row_h / 2 - cb_size / 2,
                 size=cb_size, checked=done)
        if item:
            c.setFont(FONT_BODY, 7)
            c.setFillColor(C_MID if done else C_DARK)
            c.drawString(cl + col_cb_w + 1 * mm, row_top - action_row_h / 2 - 1 * mm,
                        str(item.get("title", ""))[:22])
            c.drawString(who_x + 1 * mm, row_top - action_row_h / 2 - 1 * mm,
                        str(item.get("who", ""))[:9])
            c.drawString(due_x + 1 * mm, row_top - action_row_h / 2 - 1 * mm,
                        str(item.get("due", ""))[:7])
        c.setStrokeColor(C_BLACK)
        c.setLineWidth(0.25)
        c.line(who_x, row_bot, who_x, row_top)
        c.line(due_x, row_bot, due_x, row_top)
        c.line(cl, row_bot, cr, row_bot)
        row_top = row_bot

    # ── Notes (dot grid, fills the space above the action items block) ──────
    y -= 2 * mm
    c.setFont(FONT_BODY, 7)
    c.setFillColor(C_BLACK)
    c.drawString(cl, y, "NOTIZEN")
    notes_top    = y - 5 * mm
    notes_bottom = ai_top + 3 * mm
    dot_gap = 5 * mm
    c.setFillColor(C_LIGHT)
    x = cl
    while x <= cr:
        yy = notes_bottom
        while yy <= notes_top:
            c.circle(x, yy, 0.4 * mm, fill=1, stroke=0)
            yy += dot_gap
        x += dot_gap

    c.save()


# ══════════════════════════════════════════════════════════════════════════════
#  Template 6 – Tagesplan quer
# ══════════════════════════════════════════════════════════════════════════════

def make_tagesplan_quer(path: str, date_str: str = "", *,
                        events: list[dict] | None = None,
                        tasks:  list[dict] | None = None) -> None:
    """
    Daily planner, A5 landscape. New template type, noteleaf://daily-wide/v1.

    Three equal-weight zones side by side — time / tasks / notes — matching
    the portrait Tagesplan's baseline visual language (grey header bar,
    crosshair corner markers, half-hour time grid), just splitting the day
    across two time sub-columns instead of squeezing everything into one
    narrow column.

    Parameters
    ----------
    path      : output file path
    date_str  : header date label
    events    : list of {"time": "HH:MM", "title": str}
    tasks     : list of {"title": str, "completed": bool}
    """
    events = events or []
    tasks  = tasks  or []

    lw, lh = landscape(A5)
    c = canvas.Canvas(path, pagesize=(lw, lh))
    c.setTitle("Noteleaf Template")
    c.setAuthor("Noteleaf")

    _draw_qr(c, _qr_payload("daily-wide"), page_w=lw)
    _draw_type_symbol(c, "dailyWide")
    _draw_footer(c, "daily-wide", page_w=lw)
    _draw_markers(c, page_w=lw, page_h=lh)
    top = _header_bar(c, "Tagesplan", date_str or "________________",
                      page_w=lw, page_h=lh)

    cl = MARGIN + MARKER_SIZE + 3 * mm
    cr = lw - MARGIN - MARKER_SIZE - 3 * mm
    ct = top - 3 * mm
    gap = 6 * mm
    col_w = (cr - cl - 2 * gap) / 3
    time_col_l = cl
    task_col_l = cl + col_w + gap
    note_col_l = cl + 2 * (col_w + gap)

    # ── Time, split across two half-hour sub-columns ─────────────────────────
    _section_label(c, time_col_l, ct, "Zeitplan")
    row_h = 5.5 * mm
    y0    = ct - 4 * mm

    all_slots     = [f"{h:02d}:{m:02d}" for h in range(5, 24) for m in (0, 30)]
    rows_per_col  = max(1, int((y0 - BOTTOM_SAFE) // row_h))
    n_slots       = min(len(all_slots), rows_per_col * 2)
    half          = (n_slots + 1) // 2
    half_a, half_b = all_slots[:half], all_slots[half:n_slots]

    sub_gap = 4 * mm
    sub_w   = (col_w - sub_gap) / 2
    grid_bottom = y0 - half * row_h

    for sub_l, slots in [(time_col_l, half_a), (time_col_l + sub_w + sub_gap, half_b)]:
        for i, slot in enumerate(slots):
            ry = y0 - i * row_h
            if i % 2 == 0:
                c.setFillColor(colors.HexColor("#fafafa"))
                c.rect(sub_l, ry - row_h + 0.5 * mm, sub_w, row_h - 0.5 * mm, fill=1, stroke=0)
            c.setFont(FONT_BODY, 6)
            c.setFillColor(C_MID)
            c.drawString(sub_l, ry - row_h + 1.8 * mm, slot)
            _hline(c, sub_l, sub_l + sub_w, ry - row_h + 0.5 * mm)
        box_h = len(slots) * row_h
        c.setStrokeColor(C_LIGHT)
        c.setLineWidth(0.4)
        c.rect(sub_l, y0 - box_h, sub_w, box_h, fill=0, stroke=1)

    # ── Tasks ─────────────────────────────────────────────────────────────────
    _section_label(c, task_col_l, ct, "Aufgaben")
    ty        = ct - 4 * mm
    task_row  = 7.5 * mm
    cb_size   = 3.2 * mm
    num_tasks = 11

    for i in range(num_tasks):
        ry = ty - i * task_row
        if ry - task_row < grid_bottom:
            break
        task = tasks[i] if i < len(tasks) else None
        done = bool(task.get("completed", False)) if task else False
        _checkbox(c, task_col_l, ry - cb_size, size=cb_size, checked=done)
        if task:
            c.setFont(FONT_BODY, 7)
            c.setFillColor(C_MID if done else C_DARK)
            c.drawString(task_col_l + cb_size + 1.5 * mm, ry - cb_size + 0.3 * mm,
                        str(task.get("title", ""))[:26])
        else:
            _hline(c, task_col_l + cb_size + 1.5 * mm, task_col_l + col_w,
                  ry - cb_size + 0.5 * mm, C_XLIGHT)
        _hline(c, task_col_l, task_col_l + col_w, ry - task_row + 0.3 * mm, C_XLIGHT, 0.15)

    # ── Notes (dot grid) ──────────────────────────────────────────────────────
    _section_label(c, note_col_l, ct, "Notizen")
    notes_top = ct - 4 * mm
    dot_gap   = 5 * mm
    c.setFillColor(C_LIGHT)
    x = note_col_l
    while x <= note_col_l + col_w:
        y = grid_bottom
        while y <= notes_top:
            c.circle(x, y, 0.4 * mm, fill=1, stroke=0)
            y += dot_gap
        x += dot_gap

    c.save()


# ══════════════════════════════════════════════════════════════════════════════
#  Generate all blank templates
# ══════════════════════════════════════════════════════════════════════════════

def generate_all(output_dir: str = "templates") -> None:
    """Generates all six blank templates into *output_dir*."""
    os.makedirs(output_dir, exist_ok=True)
    make_tagesplan        (f"{output_dir}/01_tagesplan.pdf")
    make_wochenplan       (f"{output_dir}/02_wochenplan.pdf")
    make_checkliste       (f"{output_dir}/03_checkliste.pdf")
    make_notizseite       (f"{output_dir}/04_notizseite.pdf")
    make_meeting_notizen  (f"{output_dir}/05_meeting_notizen.pdf")
    make_tagesplan_quer   (f"{output_dir}/06_tagesplan_quer.pdf")
    print(f"✓  6 Vorlagen erstellt in '{output_dir}/'")


if __name__ == "__main__":
    generate_all()
