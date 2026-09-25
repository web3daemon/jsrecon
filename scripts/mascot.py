"""The jsrecon mascot: a pixel hermit crab living in a `{ }` shell.

It is the sibling of httpcrabber's crab (same orange, same pixel size): that one
catches traffic, this one lives inside the bundle. One grid, three uses —
the animated README logo, the social preview, and the 1-bit reel / posts.

    python scripts/mascot.py        # preview → build/mascot.png
"""

# . empty   O shell-mate orange   H highlight   D shade   W eye   K pupil
# S shell   L shell highlight     s shell shade G brace   C cursor (blinks)
HERMIT = (
    "........LLLLLL..................",
    ".....LLLSSSSSSLL................",
    "....LSSSSSSSSSSSS...............",
    "...LSSSSSSSSSSSSSS...WWW.WWW....",
    "..LSSGGSSSSSSSSGGSS..WKW.WKW....",
    "..LSSGSSSSSSSSSSGSSS.WWW.WWWO..O",
    ".LSSSGSSSSSSSSSSGSSS..O...O.OO.O",
    ".LSSSGSSSSSSSSSSGSSS..O...O.OOOO",
    "LSSSGSSSSSSSSSSSSGSSS.O...O..OO.",
    "LSSSSGSSSSSSSSSSGSSSOOOOOOOO.O..",
    "SSSSSGSSSCCSSSSSGSSOOHHOOOOOOO..",
    "SSSSSGSSSCCSSSSSGSSOOOOOOOOOO...",
    "sSSSSSGGSSSSSSGGSSsOOOOOOOOO....",
    ".ssSSSSSSSSSSSSSSssDDDDDDDD.....",
    "..sssssssssssssss..O..O..O..O...",
    "....sssssssssss...O..O....O..O..",
    ".................O..O......O..O.",
)

COLORS = {
    "O": "#ff5a36", "H": "#ff9a6e", "D": "#b8321b", "W": "#ffffff", "K": "#0b0f0c",
    "S": "#7f8cff", "L": "#b7bfff", "s": "#4a52b8", "G": "#39ff14", "C": "#39ff14",
}

# animation groups for the SVG logo
EYES = {(c, r) for r in range(3, 6) for c in (21, 22, 23, 25, 26, 27)}
CLAW_TIP = {(28, 5), (31, 5), (31, 6), (31, 7)}          # pincer tips
CURSOR = {(c, r) for c in (9, 10) for r in (10, 11)}
CLAW_CLOSED = {(28, 5): ".", (31, 5): ".", (31, 6): ".", (31, 7): "O", (30, 5): "O", (29, 5): "O"}

WIDTH, HEIGHT = len(HERMIT[0]), len(HERMIT)
assert all(len(row) == WIDTH for row in HERMIT), [len(r) for r in HERMIT]


def cells():
    for y, row in enumerate(HERMIT):
        for x, ch in enumerate(row):
            if ch != ".":
                yield x, y, ch


def grid(blink: bool = False, snap: bool = False) -> list[list[str]]:
    """The grid as mutable rows, with eyes shut and/or the claw closed."""
    rows = [list(r) for r in HERMIT]
    if blink:
        for c, r in EYES:
            rows[r][c] = "W" if r == 4 else "."
    if snap:
        for (c, r), ch in CLAW_CLOSED.items():
            rows[r][c] = ch
    return rows


def onebit(block: int = 10, blink: bool = False, snap: bool = False, cursor: bool = True):
    """(coverage, tone) arrays for the 1-bit kit (reel, posts): a solid white crab,
    a diagonally hatched shell, braces cut out in black."""
    import numpy as np

    rows = grid(blink, snap)
    h, w = len(rows) * block, len(rows[0]) * block
    cov = np.zeros((h, w), np.float32)
    tone = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:block, 0:block]
    step = max(2, block // 6)
    hatch = (((xx + yy) // step) % 2 == 0).astype(np.float32)
    sparse = (((xx + yy) // step) % 3 == 0).astype(np.float32)
    fill = {"O": 1.0, "W": 1.0, "L": 1.0, "H": 0.55, "D": 0.55, "K": 0.0, "G": 0.0,
            "C": 1.0 if cursor else None, "S": None, "s": None}
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            sl = (slice(y * block, (y + 1) * block), slice(x * block, (x + 1) * block))
            cov[sl] = 1.0
            v = fill[ch]
            tone[sl] = (0.12 + 0.8 * (sparse if ch == "s" else hatch)) if v is None else v
    return cov, tone


if __name__ == "__main__":
    from pathlib import Path

    from PIL import Image, ImageDraw

    px = 16
    img = Image.new("RGB", (WIDTH * px + 64, HEIGHT * px + 64), "#0b0f0c")
    d = ImageDraw.Draw(img)
    for x, y, ch in cells():
        d.rectangle([32 + x * px, 32 + y * px, 32 + (x + 1) * px - 1, 32 + (y + 1) * px - 1], fill=COLORS[ch])
    out = Path(__file__).resolve().parent.parent / "build" / "mascot.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out)
    print(out)
