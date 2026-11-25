"""Generate ATICA's vector brand assets (logos and background drawings).

Run from the repository root (needs PySide6 installed):  python docs/_make_brand_assets.py

* ``logo.svg`` / ``logo_light.svg``                 - the "A" symbol for light / dark backgrounds;
* ``logo_wordmark.svg`` / ``logo_wordmark_light.svg`` - symbol + the word ATICA set in IBM Plex Sans
  SemiBold and converted to outlines, so the logo is pure vector and needs no font at render time;
* ``backgrounds/*.svg``                             - subtle engineering-drawing backdrops.

The palette values below are the ATICA identity colours and must match ``gui/styles/theme.py``.
"""

from __future__ import annotations

import math
import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QPainterPath

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "src" / "atica" / "gui" / "resources"

LIGHT_GREY = "#E3E4E7"
COOL_GREY = "#C9CCD2"
OFF_WHITE = "#F3F0F2"
BEIGE = "#D9C7C0"
MAUVE = "#B8B5B9"
INK = "#23262B"


def path_data(path: QPainterPath) -> str:
    """SVG path data (absolute commands) of a QPainterPath."""
    out = []
    i, n = 0, path.elementCount()
    while i < n:
        e = path.elementAt(i)
        if e.type == QPainterPath.ElementType.MoveToElement:
            out.append("M%.2f %.2f" % (e.x, e.y))
        elif e.type == QPainterPath.ElementType.LineToElement:
            out.append("L%.2f %.2f" % (e.x, e.y))
        elif e.type == QPainterPath.ElementType.CurveToElement:
            c2, end = path.elementAt(i + 1), path.elementAt(i + 2)
            out.append("C%.2f %.2f %.2f %.2f %.2f %.2f" % (e.x, e.y, c2.x, c2.y, end.x, end.y))
            i += 2
        i += 1
    return "".join(out) + "Z"


def wordmark_outline(text: str, size_px: float, tracking_em: float) -> tuple[str, float, float]:
    """Outlines of ``text`` in IBM Plex Sans SemiBold; returns (path data, width, cap height)."""
    font = QFont("IBM Plex Sans")
    font.setWeight(QFont.Weight.DemiBold)
    font.setPixelSize(int(size_px))
    from PySide6.QtGui import QFontMetricsF

    metrics = QFontMetricsF(font)
    combined = QPainterPath()
    x = 0.0
    for ch in text:
        glyph = QPainterPath()
        glyph.addText(QPointF(x, 0.0), font, ch)
        combined.addPath(glyph)
        x += metrics.horizontalAdvance(ch) + tracking_em * size_px
    width = x - tracking_em * size_px
    return path_data(combined), width, metrics.capHeight()


def symbol(fill: str, ink: str, accent: str) -> str:
    """The ATICA symbol: a squared tile with a geometric 'A' and a crossbar (64 x 64 units)."""
    return (
        '<rect x="4" y="4" width="56" height="56" rx="8" fill="%s"/>'
        '<path d="M18 46 32 17l14 29" fill="none" stroke="%s" stroke-width="5.5" stroke-linecap="square" stroke-linejoin="miter"/>'
        '<path d="M24 37h16" fill="none" stroke="%s" stroke-width="4.5" stroke-linecap="square"/>'
        % (fill, ink, accent)
    )


#: Background drawings are deliberately faint; their stroke opacities are scaled by this factor.
BACKDROP_OPACITY_SCALE = 0.5


def _fade(content: str) -> str:
    import re

    return re.sub(
        r'stroke-opacity="([0-9.]+)"',
        lambda m: 'stroke-opacity="%g"' % round(float(m.group(1)) * BACKDROP_OPACITY_SCALE, 3),
        content,
    )


def write(path: pathlib.Path, content: str) -> None:
    if path.parent.name == "backgrounds":
        content = _fade(content)
    path.write_text(content, encoding="utf-8")
    print("wrote", path.relative_to(ROOT), "(%d bytes)" % len(content.encode("utf-8")))


def logos() -> None:
    write(
        RES / "icons" / "logo.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">%s</svg>\n'
        % symbol(INK, OFF_WHITE, BEIGE),
    )
    write(
        RES / "icons" / "logo_light.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">%s</svg>\n'
        % symbol(OFF_WHITE, INK, MAUVE),
    )
    data, width, cap = wordmark_outline("ATICA", 40, 0.14)
    height = 64
    baseline = 32 + cap / 2
    total = 64 + 14 + width
    for name, fill, ink, accent, text in (
        ("logo_wordmark.svg", INK, OFF_WHITE, BEIGE, INK),
        ("logo_wordmark_light.svg", OFF_WHITE, INK, MAUVE, OFF_WHITE),
    ):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.1f %d" role="img" aria-label="ATICA">%s'
            '<path transform="translate(78 %.2f)" fill="%s" fill-rule="nonzero" d="%s"/></svg>\n'
            % (total, height, symbol(fill, ink, accent), baseline, text, data)
        )
        write(RES / "icons" / name, svg)


def gear(cx: float, cy: float, teeth: int, r_outer: float, r_root: float, rotate: float = 0.0) -> str:
    """Closed outline of a spur gear with trapezoidal teeth."""
    pts = []
    step = 2 * math.pi / teeth
    for k in range(teeth):
        a = rotate + k * step
        for frac, r in ((0.0, r_root), (0.18, r_root), (0.30, r_outer), (0.52, r_outer), (0.64, r_root)):
            ang = a + frac * step
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return "M" + "L".join("%.1f %.1f" % p for p in pts) + "Z"


def grid(w: int, h: int, minor: int, major: int, minor_op: float, major_op: float) -> str:
    out = ['<g stroke="%s" fill="none" stroke-width="1">' % MAUVE]
    out.append('<g stroke-opacity="%.2f">' % minor_op)
    out += ['<path d="M%d 0V%d"/>' % (x, h) for x in range(0, w + 1, minor) if x % major]
    out += ['<path d="M0 %dH%d"/>' % (y, w) for y in range(0, h + 1, minor) if y % major]
    out.append("</g>")
    out.append('<g stroke-opacity="%.2f">' % major_op)
    out += ['<path d="M%d 0V%d"/>' % (x, h) for x in range(0, w + 1, major)]
    out += ['<path d="M0 %dH%d"/>' % (y, w) for y in range(0, h + 1, major)]
    out.append("</g></g>")
    return "".join(out)


def registration(cx: float, cy: float, r: float = 10, op: float = 0.55) -> str:
    return (
        '<g stroke="%s" stroke-opacity="%.2f" fill="none" stroke-width="1.2"><circle cx="%.1f" cy="%.1f" r="%.1f"/>'
        '<path d="M%.1f %.1fH%.1fM%.1f %.1fV%.1f"/></g>'
        % (MAUVE, op, cx, cy, r, cx - r * 1.8, cy, cx + r * 1.8, cx, cy - r * 1.8, cy + r * 1.8)
    )


def ruler(x0: float, y0: float, length: int, step: int, op: float, vertical: bool = False) -> str:
    ticks = []
    for i in range(0, length + 1, step):
        long = (i // step) % 5 == 0
        size = 12 if long else 6
        if vertical:
            ticks.append("M%.1f %.1fh%d" % (x0, y0 + i, size))
        else:
            ticks.append("M%.1f %.1fv%d" % (x0 + i, y0, size))
    return '<path d="%s" stroke="%s" stroke-opacity="%.2f" stroke-width="1" fill="none"/>' % (
        "".join(ticks),
        MAUVE,
        op,
    )


def construction(cx: float, cy: float, radii, op: float) -> str:
    parts = ['<g stroke="%s" fill="none" stroke-width="1.2">' % MAUVE]
    for r in radii:
        parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f" stroke-opacity="%.2f"/>' % (cx, cy, r, op))
    far = max(radii) * 1.12
    parts.append(
        '<path stroke-dasharray="10 6 2 6" stroke-opacity="%.2f" d="M%.1f %.1fH%.1fM%.1f %.1fV%.1f"/>'
        % (op + 0.1, cx - far, cy, cx + far, cx, cy - far, cy + far)
    )
    parts.append("</g>")
    return "".join(parts)


def backgrounds() -> None:
    folder = RES / "backgrounds"
    folder.mkdir(exist_ok=True)

    # dashboard: the most visible one - technical grid, meshing gears and construction geometry bottom-right
    w, h = 1600, 1000
    g_big = gear(1290, 700, 20, 250, 218)
    g_small = gear(1000, 560, 12, 128, 104, rotate=math.pi / 12)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMaxYMax slice">'
        % (w, h),
        grid(w, h, 40, 200, 0.10, 0.20),
        construction(1290, 700, (330, 218, 120, 46), 0.28),
        '<g fill="none" stroke="%s" stroke-opacity="0.38" stroke-width="1.3" stroke-linejoin="round">'
        % MAUVE,
        '<path d="%s"/><path d="%s"/>' % (g_big, g_small),
        '<circle cx="1290" cy="700" r="30"/><circle cx="1000" cy="560" r="20"/></g>',
        construction(1000, 560, (170, 104, 50), 0.24),
        ruler(40, 24, 1520, 20, 0.32),
        ruler(24, 40, 920, 20, 0.32, vertical=True),
        registration(60, 60),
        registration(w - 60, 60),
        registration(60, h - 60),
        registration(w - 60, h - 60),
        '<g stroke="%s" stroke-opacity="0.45" stroke-width="1" fill="none"><path d="M760 940H1180M760 930v20M1180 930v20"/>'
        '<path d="M780 934l-12 6 12 6M1160 934l12 6-12 6"/></g>' % MAUVE,
        "</svg>\n",
    ]
    write(folder / "bg_dashboard.svg", "".join(parts))

    # calculation pages: quieter - faint grid, corner marks and a partial construction circle at top-right
    w, h = 1600, 1000
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMaxYMin slice">'
        % (w, h),
        grid(w, h, 40, 200, 0.10, 0.18),
        construction(1480, 40, (360, 240, 120), 0.26),
        ruler(40, 10, 1520, 20, 0.30),
        registration(w - 50, h - 50, 9, 0.38),
        registration(50, h - 50, 9, 0.38),
        "</svg>\n",
    ]
    write(folder / "bg_page.svg", "".join(parts))

    # sidebar: a thin measurement scale and a faint arc, almost invisible
    w, h = 248, 1000
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMax slice">'
        % (w, h),
        ruler(w - 22, 0, h, 20, 0.28, vertical=True),
        construction(30, 960, (190, 120, 60), 0.20),
        '<g stroke="%s" stroke-opacity="0.26" stroke-width="1.2" fill="none"><path d="%s"/></g>'
        % (MAUVE, gear(30, 960, 14, 96, 80)),
        "</svg>\n",
    ]
    write(folder / "bg_nav.svg", "".join(parts))


def main() -> int:
    app = QGuiApplication(sys.argv)
    for weight in ("Regular", "Medium", "SemiBold"):
        font_file = RES / "fonts" / ("IBMPlexSans-%s.ttf" % weight)
        if QFontDatabase.addApplicationFont(str(font_file)) < 0:
            print("cannot load", font_file)
            return 1
    logos()
    backgrounds()
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
