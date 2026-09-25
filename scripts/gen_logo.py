"""README logo and social preview, built from the pixel mascot in mascot.py.

    python scripts/gen_logo.py

assets/logo.svg           — README header, animated: the `{ }` visor's eyes scan
                            left and right and blink (CSS, plays like a GIF)
assets/social-preview.svg — 1280×640 card for link previews (X, Telegram, Discord)
assets/social-preview.png — the same, rasterised (needs Chrome/Chromium)

Same kit as httpcrabber's gen_logo.py: a built-in pixel font instead of a system
one, because an SVG inside <img> can't load web fonts.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mascot import HEIGHT, WIDTH, cells, color  # noqa: E402

OUT = ROOT / "assets"
BG = "#0b0f0c"
MONO = "ui-monospace, 'JetBrains Mono', 'Fira Code', Consolas, monospace"

# lowercase 5×9 pixel font: rows 0–1 ascenders, 2–6 x-height, 7–8 descenders
GLYPHS = {
    "j": ["...X.", ".....", "..XX.", "...X.", "...X.", "...X.", "...X.", "X..X.", ".XX.."],
    "s": [".....", ".....", ".XXXX", "X....", ".XXX.", "....X", "XXXX.", ".....", "....."],
    "r": [".....", ".....", "X.XX.", "XX..X", "X....", "X....", "X....", ".....", "....."],
    "e": [".....", ".....", ".XXX.", "X...X", "XXXXX", "X....", ".XXX.", ".....", "....."],
    "c": [".....", ".....", ".XXX.", "X...X", "X....", "X...X", ".XXX.", ".....", "....."],
    "o": [".....", ".....", ".XXX.", "X...X", "X...X", "X...X", ".XXX.", ".....", "....."],
    "n": [".....", ".....", "XXXX.", "X...X", "X...X", "X...X", "X...X", ".....", "....."],
}

def _rects(items, px: int) -> str:
    return "".join(
        f'<rect x="{x * px}" y="{y * px}" width="{px}" height="{px}" fill="{color(x, ch)}"/>'
        for x, y, ch in items)


def mascot_layers(px: int) -> str:
    """Braces, then the eyes: open (whites + a pupil per gaze) swapping with shut."""
    braces = _rects([c for c in cells() if c[2] == "G"], px)
    whites = _rects([(x, y, "W") for x, y, ch in cells() if ch in "WK"], px)
    pupils = {cls: _rects([c for c in cells(look) if c[2] == "K"], px)
              for cls, look in (("pc", 0), ("pr", 1), ("pl", -1))}
    shut = _rects([c for c in cells(blink=True) if c[2] == "W"], px)
    gaze = "".join(f'<g class="{cls}">{rects}</g>' for cls, rects in pupils.items())
    return f'{braces}<g class="eye-open">{whites}{gaze}</g><g class="eye-closed">{shut}</g>'


def mascot_static(px: int) -> str:
    return _rects(cells(), px)


def wordmark(text: str, px: int, fill: str) -> tuple[str, int]:
    rects, x0 = [], 0
    for ch in text:
        for y, row in enumerate(GLYPHS[ch]):
            for x, bit in enumerate(row):
                if bit == "X":
                    rects.append(f'<rect x="{(x0 + x) * px}" y="{y * px}" width="{px}" height="{px}"/>')
        x0 += len(GLYPHS[ch][0]) + 1
    return f'<g fill="{fill}">{"".join(rects)}</g>', (x0 - 1) * px


def defs(grad_x1: float, grad_x2: float, grid: int) -> str:
    return f"""<defs>
    <linearGradient id="word" gradientUnits="userSpaceOnUse" x1="{grad_x1}" y1="0" x2="{grad_x2}" y2="0">
      <stop offset="0" stop-color="#39ff14"/><stop offset="0.5" stop-color="#00e5ff"/><stop offset="1" stop-color="#ff2fd0"/>
    </linearGradient>
    <filter id="glow" x="-10%" y="-30%" width="120%" height="160%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="grid" width="{grid}" height="{grid}" patternUnits="userSpaceOnUse">
      <path d="M{grid} 0H0V{grid}" fill="none" stroke="#39ff14" stroke-opacity="0.07"/>
    </pattern>
  </defs>"""


ANIM_CSS = """<style>
    .eye-closed, .pr, .pl { opacity: 0 }
    .eye-open   { animation: blink-o 4.3s step-end infinite }
    .eye-closed { animation: blink-c 4.3s step-end infinite }
    .pc         { animation: gaze-c 3.6s step-end infinite }
    .pr         { animation: gaze-r 3.6s step-end infinite }
    .pl         { animation: gaze-l 3.6s step-end infinite }
    .bob        { animation: bob 1.2s step-end infinite }
    @keyframes blink-o { 0% {opacity:1} 90% {opacity:0} 94% {opacity:1} }
    @keyframes blink-c { 0% {opacity:0} 90% {opacity:1} 94% {opacity:0} }
    @keyframes gaze-c  { 0% {opacity:1} 35% {opacity:0} 55% {opacity:1} 70% {opacity:0} 90% {opacity:1} }
    @keyframes gaze-r  { 0% {opacity:0} 35% {opacity:1} 55% {opacity:0} }
    @keyframes gaze-l  { 0% {opacity:0} 70% {opacity:1} 90% {opacity:0} }
    @keyframes bob     { 0% {transform:translateY(0)} 50% {transform:translateY(-PXpx)} }
  </style>"""


def logo() -> str:
    w, h, px, wpx = 880, 240, 9, 8
    m_w, m_h = WIDTH * px, HEIGHT * px
    mx, my = 50, (h - m_h) // 2
    word, word_w = wordmark("jsrecon", wpx, "url(#word)")
    wx, wy = mx + m_w + 56, 40
    mascot = mascot_layers(px)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="jsrecon">
  <title>jsrecon</title>
  {ANIM_CSS.replace("PX", str(px // 2))}
  {defs(0, word_w, 24)}
  <rect width="{w}" height="{h}" rx="18" fill="{BG}"/>
  <rect width="{w}" height="{h}" rx="18" fill="url(#grid)"/>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="#ff2fd0" stroke-opacity="0.45"/>
  <g transform="translate({mx} {my})" shape-rendering="crispEdges">
    <g class="bob">{mascot}</g>
  </g>
  <g transform="translate({wx} {wy})" shape-rendering="crispEdges" filter="url(#glow)">{word}</g>
  <g font-family="{MONO}">
    <text x="{wx}" y="{wy + 9 * wpx + 30}" font-size="21" fill="#00e5ff">map a web app's JavaScript to its API</text>
    <text x="{wx}" y="{wy + 9 * wpx + 58}" font-size="14" fill="#6f7f6f">source maps · tree-sitter · endpoints · graphql · openapi</text>
  </g>
</svg>
"""


def _row(y: int, cells_: list[tuple[str, str, int]], newest: bool = False) -> str:
    sp = "&#160;"
    mark = f'<tspan fill="#39ff14">▸{sp}</tspan>' if newest else f"<tspan>{sp * 2}</tspan>"
    parts = []
    for text, fill, width in cells_:
        parts.append(f'<tspan fill="{fill}">{text.ljust(width).replace(" ", sp)}</tspan>')
    return f'<text x="584" y="{y}">{mark}{"".join(parts)}</text>'


def social() -> str:
    w, h, px, wpx = 1280, 640, 18, 11
    m_h = HEIGHT * px
    mx, my = 76, (h - m_h) // 2 - 14
    word, word_w = wordmark("jsrecon", wpx, "url(#word)")
    wx, wy = 560, 120
    dim = "#5f6f5f"
    rows = [
        _row(462, [("POST", "#ff2fd0", 7), ("/orders/{id}/refund", "#ffffff", 22), ("orders.ts:18", dim, 0)]),
        _row(492, [("query", "#ff2fd0", 7), ("SearchProducts", "#ffffff", 22), ("graphql.ts:11", dim, 0)]),
        _row(522, [("high", "#ff3b3b", 7), ("AWS key AKIA…LE", "#ffcc00", 22), ("config.ts:10", dim, 0)], True),
    ]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="jsrecon — map a web app's JavaScript to its API">
  <title>jsrecon — map a web app's JavaScript to its API</title>
  {defs(0, word_w, 32)}
  <radialGradient id="halo" cx="0.2" cy="0.5" r="0.45">
    <stop offset="0" stop-color="#7f8cff" stop-opacity="0.2"/><stop offset="1" stop-color="#7f8cff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="halo2" cx="0.85" cy="0.1" r="0.6">
    <stop offset="0" stop-color="#ff2fd0" stop-opacity="0.14"/><stop offset="1" stop-color="#ff2fd0" stop-opacity="0"/>
  </radialGradient>
  <rect width="{w}" height="{h}" fill="{BG}"/>
  <rect width="{w}" height="{h}" fill="url(#grid)"/>
  <rect width="{w}" height="{h}" fill="url(#halo)"/>
  <rect width="{w}" height="{h}" fill="url(#halo2)"/>
  <rect x="24" y="24" width="{w - 48}" height="{h - 48}" rx="22" fill="none" stroke="#ff2fd0" stroke-opacity="0.35"/>
  <g transform="translate({mx} {my})" shape-rendering="crispEdges">{mascot_static(px)}</g>
  <g transform="translate({wx} {wy})" shape-rendering="crispEdges" filter="url(#glow)">{word}</g>
  <g font-family="{MONO}">
    <text x="{wx}" y="300" font-size="27" fill="#d6ded6">Point it at a web app.</text>
    <text x="{wx}" y="338" font-size="27" fill="#d6ded6">Get the API its JavaScript talks to.</text>
    <text x="{wx}" y="386" font-size="21" fill="#00e5ff">source maps → original code → endpoints · graphql</text>
    <g font-size="17">
      <rect x="560" y="428" width="620" height="112" rx="10" fill="#0f1511" stroke="#39ff14" stroke-opacity="0.25"/>
      {"".join(rows)}
    </g>
    <text x="96" y="582" font-size="18" fill="#5f6f5f">tree-sitter · source maps · openapi 3.1 · routes · secret audit · python</text>
  </g>
</svg>
"""


def find_chrome() -> str | None:
    env = os.environ.get("JSRECON_BROWSER")
    if env:
        return env
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if Path(p).exists():
            return p
    return next((shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser")
                 if shutil.which(n)), None)


def chrome_png(html: Path, png: Path, size: tuple[int, int], scale: int = 1) -> bool:
    chrome = find_chrome()
    if not chrome:
        return False
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", f"--user-data-dir={profile}",
                        f"--force-device-scale-factor={scale}", "--virtual-time-budget=2000",
                        f"--window-size={size[0]},{size[1]}", f"--screenshot={png}",
                        html.as_uri()], check=True, capture_output=True)
    return True


def rasterize(svg: Path, png: Path, size: tuple[int, int]) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(f'<html><body style="margin:0;background:{BG}">{svg.read_text("utf-8")}'
                        "</body></html>", encoding="utf-8")
        return chrome_png(page, png, size)


def write(name: str, svg: str) -> Path:
    path = OUT / name
    path.write_text(svg, encoding="utf-8", newline="\n")
    print(f"  {path.relative_to(ROOT)}")
    return path


def main() -> None:
    OUT.mkdir(exist_ok=True)
    write("logo.svg", logo())
    sp = write("social-preview.svg", social())
    png = OUT / "social-preview.png"
    if rasterize(sp, png, (1280, 640)):
        print(f"  {png.relative_to(ROOT)}")
    else:
        print("  social-preview.png skipped: Chrome not found (set JSRECON_BROWSER)")


if __name__ == "__main__":
    main()
