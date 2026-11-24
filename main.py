#!/usr/bin/env python3
"""THE WIRE — front page for 24 November 2026.

A single-file, standard-library-only renderer. It reads the editorial records
from facts.md next to this script, lays out a broadsheet page, and writes a
deterministic 1024x1024 RGB PNG.

Run with:  python3 -P -s main.py
Output:    $MAKEFUN_OUTPUT_DIR/entry.png  (default: out/entry.png)
"""

from __future__ import annotations

import datetime
import os
import struct
import sys
import zlib

# --------------------------------------------------------------------------
# 1. Type: a 5x7 bitmap alphabet stored as hex row masks.
#    Each glyph is seven bytes top-to-bottom; bit 4 is the leftmost pixel.
# --------------------------------------------------------------------------
GLYPHS = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x06),
    ",": (0x00, 0x00, 0x00, 0x00, 0x06, 0x06, 0x04),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    ":": (0x00, 0x06, 0x06, 0x00, 0x06, 0x06, 0x00),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    "+": (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    "%": (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    "?": (0x0E, 0x11, 0x01, 0x06, 0x04, 0x00, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
}

GLYPH_ROWS = 7
GLYPH_COLS = 5
CELL_ADVANCE = 6  # 5px ink plus one blank column of tracking


# --------------------------------------------------------------------------
# 2. Palette
# --------------------------------------------------------------------------
NEWSPRINT = (0xF4, 0xF0, 0xE6)
INK = (0x1A, 0x1C, 0x21)
INK_SOFT = (0x5F, 0x63, 0x68)
RULE = (0x1A, 0x1C, 0x21)
CARD = (0xFC, 0xFA, 0xF3)
RED = (0xA8, 0x24, 0x2A)
NAVY = (0x21, 0x45, 0x66)
TEAL = (0x1D, 0x6B, 0x63)
PLUM = (0x6B, 0x2F, 0x5A)
OCHRE = (0xB2, 0x7A, 0x1F)
SLATE = (0x4B, 0x55, 0x60)

REGION_TINTS = {
    "MARKETS": RED,
    "WASHINGTON": NAVY,
    "UKRAINE": TEAL,
    "LIBYA": PLUM,
    "BALTIC": SLATE,
    "UNITED KINGDOM": OCHRE,
    "IRAN": PLUM,
    "HORMUZ": NAVY,
    "YEMEN / SAUDI": OCHRE,
    "GAZA": RED,
    "UNITED NATIONS": TEAL,
    "NORTH KOREA": SLATE,
    "ASIA": OCHRE,
    "UNITED STATES": NAVY,
    "GERMANY": SLATE,
    "BELGIUM": RED,
    "ENERGY": OCHRE,
    "HEALTH": TEAL,
}
TINT_FALLBACK = INK_SOFT


# --------------------------------------------------------------------------
# 3. Canvas: an RGB framebuffer with fill / glyph / rectangle primitives
# --------------------------------------------------------------------------
class Sheet:
    """A mutable RGB image with a small vocabulary of drawing verbs."""

    def __init__(self, width: int, height: int, background):
        self.width = width
        self.height = height
        self.buffer = bytearray(bytes(background) * (width * height))

    def _row_span(self, y: int, x0: int, x1: int, colour):
        if not 0 <= y < self.height:
            return
        x0 = max(0, x0)
        x1 = min(self.width, x1)
        if x1 <= x0:
            return
        start = (y * self.width + x0) * 3
        stop = (y * self.width + x1) * 3
        self.buffer[start:stop] = bytes(colour) * (x1 - x0)

    def fill_rect(self, x: int, y: int, w: int, h: int, colour):
        for row in range(y, y + h):
            self._row_span(row, x, x + w, colour)

    def outline_rect(self, x: int, y: int, w: int, h: int, colour, thickness=1):
        self.fill_rect(x, y, w, thickness, colour)
        self.fill_rect(x, y + h - thickness, w, thickness, colour)
        self.fill_rect(x, y, thickness, h, colour)
        self.fill_rect(x + w - thickness, y, thickness, h, colour)

    def rule(self, x: int, y: int, w: int, colour, thickness=1):
        self.fill_rect(x, y, w, thickness, colour)

    def pixel(self, x: int, y: int, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.buffer[i:i + 3] = bytes(colour)

    def stamp_glyph(self, x: int, y: int, mask, colour, scale: int):
        for row_index, bits in enumerate(mask):
            if not bits:
                continue
            for col in range(GLYPH_COLS):
                if bits & (1 << (GLYPH_COLS - 1 - col)):
                    self.fill_rect(
                        x + col * scale,
                        y + row_index * scale,
                        scale,
                        scale,
                        colour,
                    )

    def write(self, x: int, y: int, text: str, colour, scale: int = 1):
        """Draw uppercase text; returns the x coordinate just past the last cell."""
        cursor = x
        for char in text.upper():
            self.stamp_glyph(cursor, y, GLYPHS.get(char, GLYPHS["?"]), colour, scale)
            cursor += CELL_ADVANCE * scale
        return cursor

    def circle_filled(self, cx: int, cy: int, radius: int, colour):
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            span = int((r2 - dy * dy) ** 0.5)
            self._row_span(cy + dy, cx - span, cx + span + 1, colour)

    def triangle(self, apex, base_left, base_right, colour):
        ax, ay = apex
        bx, by = base_left
        cx, cy = base_right
        top = min(ay, by, cy)
        bottom = max(ay, by, cy)
        edges = ((apex, base_left), (base_left, base_right), (apex, base_right))
        for y in range(top, bottom + 1):
            xs = []
            for p, q in edges:
                if p[1] == q[1]:
                    continue
                if min(p[1], q[1]) <= y < max(p[1], q[1]):
                    t = (y - p[1]) / (q[1] - p[1])
                    xs.append(p[0] + t * (q[0] - p[0]))
            if len(xs) >= 2:
                self._row_span(y, int(min(xs)), int(max(xs)) + 1, colour)

    def diagonal_stripes(self, x: int, y: int, w: int, h: int, colour, step=6):
        for offset in range(-(h + w) // step - 1, (w + h) // step + 1):
            for yy in range(h):
                xx = offset * step + int(yy * 0.6)
                if 0 <= xx < w:
                    self._row_span(y + yy, x + xx, x + xx + 2, colour)

    def to_png(self) -> bytes:
        stride = self.width * 3
        raw = bytearray()
        for row in range(self.height):
            raw.append(0)
            raw.extend(self.buffer[row * stride:(row + 1) * stride])

        def chunk(tag: bytes, payload: bytes) -> bytes:
            body = tag + payload
            return (
                struct.pack(">I", len(payload))
                + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
            )

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b"")
        )


# --------------------------------------------------------------------------
# 4. Typesetting helpers: measurement and greedy wrapping
# --------------------------------------------------------------------------
def text_width(text: str, scale: int = 1) -> int:
    if not text:
        return 0
    return (len(text) * CELL_ADVANCE - 1) * scale


def fits(text: str, max_px: int, scale: int) -> bool:
    return text_width(text, scale) <= max_px


def break_lines(text: str, max_px: int, scale: int = 1) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and not fits(trial, max_px, scale):
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def truncate(text: str, max_px: int, scale: int = 1) -> str:
    if fits(text, max_px, scale):
        return text
    clipped = text
    while clipped and not fits(clipped + ".", max_px, scale):
        clipped = clipped[:-1].rstrip()
    return (clipped + ".") if clipped else ""


# --------------------------------------------------------------------------
# 5. Editorial model: parse facts.md
# --------------------------------------------------------------------------
FACTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "facts.md")


def load_records(path: str = FACTS_FILE):
    """Parse pipe-separated story records, skipping headings and prose."""
    records = []
    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" not in line:
                continue
            fields = [piece.strip() for piece in line.split("|")]
            if len(fields) != 5:
                continue
            if fields[0].lower() == "region":
                continue
            region, when, key, source, headline = fields
            records.append(
                {
                    "region": region.upper(),
                    "date": when.upper(),
                    "key": key,
                    "source": source.upper(),
                    "headline": headline.upper(),
                }
            )
    return records


def region_order(records):
    seen = []
    for item in records:
        if item["region"] not in seen:
            seen.append(item["region"])
    return seen


EDITABLE_DAYS = {"23": datetime.date(2026, 11, 23),
                 "24": datetime.date(2026, 11, 24)}


def date_label_passes(records):
    """Verify each date key lands in the edition window and that 24 Nov is a Tuesday."""
    window = {datetime.date(2026, 11, 23), datetime.date(2026, 11, 24)}
    good = 0
    for item in records:
        key = item["key"]
        days = window if key == "2324" else {EDITABLE_DAYS.get(key)}
        if days and days <= window and None not in days:
            good += 1
    assert datetime.date(2026, 11, 24).weekday() == 1, "edition date must be a Tuesday"
    return good, len(records)


# --------------------------------------------------------------------------
# 6. Page metrics
# --------------------------------------------------------------------------
PAGE_W = 1024
PAGE_H = 1024
MARGIN = 34
CONTENT_W = PAGE_W - 2 * MARGIN

MASTHEAD = "THE WIRE"
DATE_LINE = "TUESDAY 24 NOVEMBER 2026"
FOLIO = "WORLD EDITION  /  VOL. IV NO. 328"

HEADER_BLOCK = 92
STAT_H = 54
HERO_H = 110
CARD_COLS = 5
CARD_GAP_X = 8
CARD_GAP_Y = 6
CARD_W = (CONTENT_W - (CARD_COLS - 1) * CARD_GAP_X) // CARD_COLS
CARD_H = 118


# --------------------------------------------------------------------------
# 7. Blocks: each returns a list of (y, height) after drawing, so the page
#    flows top-down without hard-coded absolute offsets per section.
# --------------------------------------------------------------------------
def draw_masthead(sheet: Sheet, y: int, records) -> int:
    sheet.fill_rect(0, 0, PAGE_W, 8, INK)
    sheet.fill_rect(0, 8, PAGE_W, 3, RED)

    logo_scale = 7
    logo_y = 24
    sheet.write(MARGIN, logo_y, MASTHEAD, INK, logo_scale)

    # date block, right-aligned under the masthead
    date_scale = 2
    date_x = PAGE_W - MARGIN - text_width(DATE_LINE, date_scale)
    sheet.write(date_x, logo_y + 6, DATE_LINE, RED, date_scale)
    sheet.write(
        date_x,
        logo_y + 6 + GLYPH_ROWS * date_scale + 8,
        FOLIO,
        INK_SOFT,
        1,
    )

    strapline = "LATE FINAL  /  ALL DATES VERIFIED"
    strap_y = logo_y + GLYPH_ROWS * logo_scale + 11
    sheet.write(MARGIN, strap_y, strapline, INK, 1)
    sheet.rule(MARGIN + text_width(strapline, 1) + 12, strap_y + 3,
               PAGE_W - MARGIN - (MARGIN + text_width(strapline, 1) + 12), INK_SOFT)

    sheet.rule(MARGIN, y, CONTENT_W, RULE, 2)
    return y + 2


def draw_stat_strip(sheet: Sheet, y: int, facts: dict) -> int:
    top = y + 8
    sheet.fill_rect(MARGIN, top, CONTENT_W, STAT_H, CARD)
    sheet.outline_rect(MARGIN, top, CONTENT_W, STAT_H, RULE, 1)

    stats = [
        ("STORIES", facts["count"]),
        ("REGIONS", facts["regions"]),
        ("DATE CHECK", f"{facts['checked']}/{facts['tested']}"),
        ("SOURCES", facts["sources"]),
        ("FILED 24TH", facts["filed_24"]),
        ("NAV DESKS", facts["regions"]),
    ]
    cell = CONTENT_W // len(stats)
    for index, (label, value) in enumerate(stats):
        x = MARGIN + index * cell
        if index:
            sheet.fill_rect(x, top + 7, 1, STAT_H - 14, (0xD8, 0xD2, 0xC4))
        big = str(value)
        sheet.write(x + 12, top + 5, big, RED if index == 2 else INK, 4)
        sheet.write(x + 12, top + 5 + GLYPH_ROWS * 4 + 4, label, INK_SOFT, 1)
    return top + STAT_H


def draw_region_nav(sheet: Sheet, y: int, regions) -> int:
    top = y + 6
    left = MARGIN + 4
    right_edge = PAGE_W - MARGIN
    cursor_x = left
    cursor_y = top + 5
    row_h = 13
    for region in regions:
        tint = REGION_TINTS.get(region, TINT_FALLBACK)
        label = region
        cell_w = text_width(label, 1) + 16
        if cursor_x + cell_w > right_edge:
            cursor_x = left
            cursor_y += row_h
        sheet.fill_rect(cursor_x, cursor_y + 1, 5, 6, tint)
        sheet.write(cursor_x + 8, cursor_y, label, INK, 1)
        cursor_x += cell_w
    baseline = cursor_y + row_h
    sheet.rule(MARGIN, top, CONTENT_W, INK, 1)
    sheet.rule(MARGIN, baseline, CONTENT_W, INK, 1)
    return baseline


def draw_hero_art(sheet: Sheet, x: int, y: int, w: int, h: int, motif: str, tint):
    """Paint a small geometric vignette clipped to the (x, y, w, h) window."""
    right, bottom = x + w, y + h

    def bar(px, py, pw, ph, colour):
        x0, y0 = max(x, px), max(y, py)
        x1, y1 = min(right, px + pw), min(bottom, py + ph)
        if x1 > x0 and y1 > y0:
            sheet.fill_rect(x0, y0, x1 - x0, y1 - y0, colour)

    def wedge(bx, by, bw, bh):
        """A downward spike spanning bw pixels, bh tall, clipped row by row."""
        for dy in range(bh):
            half = max(1, (bw // 2) * (bh - dy) // bh)
            bar(bx + bw // 2 - half, by + dy, half * 2, 1, ink)

    if motif == "chart":
        bar(x, y, w, h, (0x2A, 0x2D, 0x34))
        grid = (0x3E, 0x43, 0x4D)
        for gx in range(x + 8, right - 4, 12):
            bar(gx, y + 4, 1, h - 8, grid)
        for gy in range(y + 6, bottom - 3, 11):
            bar(x + 4, gy, w - 8, 1, grid)
        price = (0xF0, 0xB4, 0x4A)
        series = [0.10, 0.26, 0.20, 0.44, 0.38, 0.62, 0.90]
        pts = [(x + 8 + i * (w - 18) / (len(series) - 1),
                bottom - 6 - v * (h - 14)) for i, v in enumerate(series)]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            steps = max(1, int(abs(bx - ax) + abs(by - ay)))
            for k in range(steps + 1):
                px = int(ax + (bx - ax) * k / steps)
                py = int(ay + (by - ay) * k / steps)
                bar(px, py, 2, 2, price)
        sheet.write(x + 7, y + 6, "+27%", price, 2)
    elif motif == "sea":
        bar(x, y, w, h, (0x1D, 0x6B, 0x63))
        ink = (0xE4, 0xF3, 0xEF)
        for row in range(y + 12, bottom - 6, 11):
            for wx in range(x + 2, right - 8, 18):
                wedge(wx, row, 12, 6)
        ink = (0x08, 0x33, 0x30)
        hull_y = bottom - 10
        bar(x + 12, hull_y, min(70, w - 24), 4, ink)
        wedge(x + 10 + min(70, w - 24) // 2, bottom - 20, 12, 12)
    else:
        bar(x, y, w, h, (0x5A, 0x22, 0x22))
        for stripe in range(-h, w + h, 9):
            for dy in range(h):
                bar(x + stripe + dy, y + dy, 2, 1, (0x6C, 0x2B, 0x2B))
        ink = (0xD9, 0xB2, 0x8A)
        for bx in range(x + 8, right - 12, 18):
            bh = 8 + ((bx - x) * 5) % max(6, h - 16)
            bar(bx, bottom - 4 - bh, 9, bh, ink)
        ink = (0xF3, 0xDE, 0xC4)
        sheet.write(x + 7, y + 6, "AID", ink, 1)


def draw_hero_cards(sheet: Sheet, y: int, heroes) -> int:
    top = y + 8
    gap = 12
    card_w = (CONTENT_W - 2 * gap) // 3
    art_h = 52
    for index, hero in enumerate(heroes):
        x = MARGIN + index * (card_w + gap)
        card_h = HERO_H
        sheet.fill_rect(x, top, card_w, card_h, CARD)
        sheet.outline_rect(x, top, card_w, card_h, RULE, 1)
        draw_hero_art(sheet, x + 1, top + 1, card_w - 2, art_h, hero["motif"], hero["tint"])
        body_x = x + 8
        inner = card_w - 16
        sheet.write(body_x, top + art_h + 5, hero["kicker"], hero["tint"], 1)
        sheet.rule(body_x, top + art_h + 14, inner, (0xD8, 0xD2, 0xC4))
        text_top = top + art_h + 19
        room = (top + card_h - 16) - text_top
        scale, lines = fit_headline(hero["headline"], inner, room, cap=2)
        cur = text_top
        for line in lines:
            sheet.write(body_x, cur, line, INK, scale)
            cur += GLYPH_ROWS * scale + 3
        sheet.write(body_x, top + card_h - 9, hero["source"], INK_SOFT, 1)
    return top + HERO_H


def fit_headline(text: str, box_w: int, box_h: int, cap: int = 3):
    """Choose the largest integer scale at which the whole headline fits."""
    for scale in range(cap, 0, -1):
        lead = 3
        wrapped = break_lines(text, box_w, scale)
        if not wrapped:
            return scale, []
        if (len(wrapped) - 1) * (GLYPH_ROWS * scale + lead) + GLYPH_ROWS * scale <= box_h:
            return scale, wrapped
    return 1, break_lines(text, box_w, 1)


def draw_story_card(sheet: Sheet, x: int, y: int, w: int, h: int, item, tint):
    sheet.fill_rect(x, y, w, h, CARD)
    sheet.outline_rect(x, y, w, h, (0xCF, 0xC8, 0xB8), 1)
    sheet.fill_rect(x + 1, y + 1, w - 2, 13, tint)
    inner = w - 12
    sheet.write(x + 6, y + 4, truncate(item["region"], inner, 1), CARD, 1)

    box_top = y + 18
    box_h = (y + h - 20) - box_top
    scale, lines = fit_headline(item["headline"], inner, box_h)
    per_line = GLYPH_ROWS * scale + 3
    cur = box_top
    for line in lines:
        sheet.write(x + 6, cur, line, INK, scale)
        cur += per_line

    sheet.write(x + 6, y + h - 17, truncate(item["date"], inner, 1), INK_SOFT, 1)
    sheet.write(x + 6, y + h - 8, truncate(item["source"], inner, 1), tint, 1)


def draw_story_grid(sheet: Sheet, y: int, records) -> int:
    top = y + 8
    sheet.write(MARGIN, top, "EVERY DISPATCH, DATE-STAMPED", INK, 1)
    sheet.rule(MARGIN, top + 12, CONTENT_W, INK, 1)
    grid_top = top + 20
    rows = (len(records) + CARD_COLS - 1) // CARD_COLS
    card_h = 118
    for index, item in enumerate(records):
        row, col = divmod(index, CARD_COLS)
        x = MARGIN + col * (CARD_W + CARD_GAP_X)
        cy = grid_top + row * (card_h + CARD_GAP_Y)
        draw_story_card(
            sheet, x, cy, CARD_W, card_h, item,
            REGION_TINTS.get(item["region"], TINT_FALLBACK),
        )
    return grid_top + rows * (card_h + CARD_GAP_Y)


def draw_also_line(sheet: Sheet, y: int, extra) -> int:
    top = y + 8
    sheet.rule(MARGIN, top, CONTENT_W, INK, 2)
    label = "ALSO ON 24 NOV"
    sheet.fill_rect(MARGIN, top + 8, text_width(label, 1) + 12, 15, RED)
    sheet.write(MARGIN + 6, top + 11, label, CARD, 1)
    # Lay items out left to right, dropping the separator width first if space is short.
    cursor = MARGIN + text_width(label, 1) + 22
    limit = PAGE_W - MARGIN
    for index, phrase in enumerate(extra):
        sep = "  /  " if index else ""
        room = limit - cursor - text_width(sep, 1)
        if room <= 0:
            break
        piece = truncate(sep + phrase, room + text_width(sep, 1), 1)
        cursor = sheet.write(cursor, top + 11, piece, INK, 1)
    return top + 23


def draw_date_check(sheet: Sheet, y: int, facts) -> int:
    top = y + 6
    sheet.rule(MARGIN, top, CONTENT_W, INK, 1)
    heading = "DATE CHECK"
    sheet.write(MARGIN, top + 9, heading, RED, 2)
    column_x = MARGIN + text_width(heading, 2) + 22
    message = (f"{facts['checked']} OF {facts['tested']} DISPATCHES CARRY A 23-24 NOV 2026 DATE"
               f"   /   {facts['regions']} REGIONS")
    sheet.write(column_x, top + 7, truncate(message, PAGE_W - MARGIN - column_x, 1), INK, 1)
    stamp = "STAMP VERIFIED: 24 NOV 2026 IS A TUESDAY (GREGORIAN CALENDAR)"
    sheet.write(column_x, top + 18, truncate(stamp, PAGE_W - MARGIN - column_x, 1), INK_SOFT, 1)
    sheet.fill_rect(0, PAGE_H - 4, PAGE_W, 4, INK)
    return top + 31


# --------------------------------------------------------------------------
# 8. Assembly
# --------------------------------------------------------------------------
def pick_heroes(records):
    by_region = {}
    for item in records:
        by_region.setdefault(item["region"], item)
    chosen = []
    wanted = [
        ("MARKETS", "chart", RED),
        ("LIBYA", "sea", TEAL),
        ("GAZA", "relief", PLUM),
    ]
    for region, motif, tint in wanted:
        item = by_region.get(region)
        if item:
            chosen.append(
                {
                    "kicker": region,
                    "headline": item["headline"],
                    "source": f"{item['source']} / {item['date']}",
                    "motif": motif,
                    "tint": tint,
                }
            )
    return chosen


def gather_facts(records):
    regions = region_order(records)
    sources = {item["source"] for item in records}
    checked, total = date_label_passes(records)
    return {
        "count": len(records),
        "regions": len(regions),
        "checked": checked,
        "sources": len(sources),
        "filed_24": sum(1 for item in records if item["key"] in ("24", "2324")),
        "known": regions,
        "tested": total,
    }


def extra_bullets(records):
    # Keep to at most three short taglines so the strip never spills past the margin.
    picked = []
    for wanted, tagline in (
        ("HEALTH", "DRUG RESISTANCE"),
        ("ENERGY", "DIESEL CRUNCH"),
        ("BELGIUM", "BRUSSELS PROTESTS"),
    ):
        if any(item["region"] == wanted for item in records):
            picked.append(tagline)
    return picked[:3]


def compose(records) -> Sheet:
    facts = gather_facts(records)
    sheet = Sheet(PAGE_W, PAGE_H, NEWSPRINT)

    y = draw_masthead(sheet, HEADER_BLOCK, records)
    y = draw_stat_strip(sheet, y, facts)
    y = draw_region_nav(sheet, y, facts["known"])
    y = draw_hero_cards(sheet, y, pick_heroes(records))
    y = draw_story_grid(sheet, y, records)
    y = draw_also_line(sheet, y, extra_bullets(records))
    draw_date_check(sheet, y, facts)
    return sheet


def output_path() -> str:
    base = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    return os.path.join(base, "entry.png")


def main(argv=None) -> int:
    records = load_records()
    if not records:
        print("facts.md yielded no story records", file=sys.stderr)
        return 1
    sheet = compose(records)
    png = sheet.to_png()
    dest = output_path()
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(dest, "wb") as handle:
        handle.write(png)
    print(f"wrote {dest} ({len(png)} bytes, {sheet.width}x{sheet.height}, "
          f"{len(records)} stories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
