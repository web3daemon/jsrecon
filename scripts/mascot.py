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

# grey levels for the 1-bit kit (reel, posts): shell light, braces cut out
TONES = {"O": 1.0, "H": 1.0, "D": 0.55, "W": 1.0, "K": 0.0,
         "S": 0.82, "L": 1.0, "s": 0.55, "G": 0.0, "C": 0.0}

# animation groups for the SVG logo
EYES = {(c, r) for r in range(3, 6) for c in (21, 22, 23, 25, 26, 27)}
CLAW_TIP = {(28, 5), (31, 5), (31, 6), (31, 7)}          # pincer tips
CURSOR = {(c, r) for c in (9, 10) for r in (10, 11)}

WIDTH, HEIGHT = len(HERMIT[0]), len(HERMIT)
assert all(len(row) == WIDTH for row in HERMIT), [len(r) for r in HERMIT]


def cells():
    for y, row in enumerate(HERMIT):
        for x, ch in enumerate(row):
            if ch != ".":
                yield x, y, ch


def mask(block: int = 10, tones: dict | None = None):
    """Grey-level array for the 1-bit kit (numpy)."""
    import numpy as np

    tones = tones or TONES
    m = np.zeros((HEIGHT * block, WIDTH * block), np.float32)
    for x, y, ch in cells():
        m[y * block:(y + 1) * block, x * block:(x + 1) * block] = tones[ch]
    return m


def alpha(block: int = 10):
    """Coverage mask (1 where the mascot has a pixel)."""
    import numpy as np

    m = np.zeros((HEIGHT * block, WIDTH * block), np.float32)
    for x, y, _ in cells():
        m[y * block:(y + 1) * block, x * block:(x + 1) * block] = 1.0
    return m


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
