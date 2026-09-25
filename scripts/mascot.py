"""The jsrecon mascot: a visor made of `{ }` with two eyes reading the code.

The braces are the head; the eyes dart left and right like they're scanning a
bundle. Sibling of httpcrabber's pixel crab (same pixel grid, same palette), and
one grid serves the animated README logo, the social preview, and the 1-bit reel
and posts.

    python scripts/mascot.py        # preview → build/mascot.png
"""

# . empty   G brace (gradient across the width)   W eye   K pupil
_LEFT = (
    "....GGGG....",
    "...GGGG.....",
    "...GG.......",
    "...GG.WWWW..",
    "...GG.WWWW..",
    "..GG..WKKW..",
    "GGG...WKKW..",
    "..GG..WWWW..",
    "...GG.......",
    "...GG.......",
    "...GG.......",
    "...GGGG.....",
    "....GGGG....",
)
GRID = tuple(row + row[-2::-1] for row in _LEFT)     # mirrored around the centre column
WIDTH, HEIGHT = len(GRID[0]), len(GRID)
assert all(len(row) == WIDTH for row in GRID)

GRADIENT = ("#39ff14", "#00e5ff", "#ff2fd0")          # the httpcrabber / jsrecon wordmark ramp
COLORS = {"W": "#ffffff", "K": "#0b0f0c"}

EYE_ROWS = range(3, 8)
EYES = ((6, 9), (13, 16))                             # (first, last) column of each eye
PUPIL_ROWS = (5, 6)


def ramp(k: float) -> str:
    k = min(1.0, max(0.0, k))
    pos = k * (len(GRADIENT) - 1)
    i = min(int(pos), len(GRADIENT) - 2)
    f = pos - i
    a, b = GRADIENT[i].lstrip("#"), GRADIENT[i + 1].lstrip("#")
    c = [round(int(a[j:j + 2], 16) + (int(b[j:j + 2], 16) - int(a[j:j + 2], 16)) * f) for j in (0, 2, 4)]
    return "#{:02x}{:02x}{:02x}".format(*c)


def color(x: int, ch: str) -> str:
    return ramp(x / (WIDTH - 1)) if ch == "G" else COLORS[ch]


def grid(look: int = 0, blink: bool = False) -> list[list[str]]:
    """Rows with the pupils shifted (-1 left, 0 centre, +1 right) or the eyes shut."""
    rows = [list(r) for r in GRID]
    for x0, x1 in EYES:
        for y in EYE_ROWS:
            for x in range(x0, x1 + 1):
                rows[y][x] = "W"
        if blink:
            for y in EYE_ROWS:
                for x in range(x0, x1 + 1):
                    rows[y][x] = "W" if y == 6 else "."
            continue
        left = x0 + 1 + look                           # 2×2 pupil, low in the 4×5 eye
        for y in PUPIL_ROWS:
            rows[y][left] = rows[y][left + 1] = "K"
    return rows


def cells(look: int = 0, blink: bool = False):
    for y, row in enumerate(grid(look, blink)):
        for x, ch in enumerate(row):
            if ch != ".":
                yield x, y, ch


def onebit(block: int = 10, look: int = 0, blink: bool = False):
    """(coverage, tone) arrays for the 1-bit kit (reel, posts): white braces and
    eyes, black pupils."""
    import numpy as np

    rows = grid(look, blink)
    cov = np.zeros((HEIGHT * block, WIDTH * block), np.float32)
    tone = np.zeros_like(cov)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            sl = (slice(y * block, (y + 1) * block), slice(x * block, (x + 1) * block))
            cov[sl] = 1.0
            tone[sl] = 0.0 if ch == "K" else 1.0
    return cov, tone


if __name__ == "__main__":
    from pathlib import Path

    from PIL import Image, ImageDraw

    px = 16
    frames = [(0, False), (1, False), (-1, False), (0, True)]
    img = Image.new("RGB", ((WIDTH * px + 48) * len(frames) + 16, HEIGHT * px + 64), "#0b0f0c")
    d = ImageDraw.Draw(img)
    for i, (look, blink) in enumerate(frames):
        ox = 32 + i * (WIDTH * px + 48)
        for x, y, ch in cells(look, blink):
            d.rectangle([ox + x * px, 32 + y * px, ox + (x + 1) * px - 1, 32 + (y + 1) * px - 1],
                        fill=color(x, ch))
    out = Path(__file__).resolve().parent.parent / "build" / "mascot.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out)
    print(out)
