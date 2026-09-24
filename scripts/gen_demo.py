"""Animated README demo: a real `jsrecon map` run, replayed as an SVG terminal.

    python scripts/gen_demo.py

The demo shop in examples/shop/dist is served on localhost, jsrecon analyses it
in-process, and its actual Rich output is cut into frames: typing the command,
the spinner, the report scrolling in, then `ls` on the recovered sources.
Frames are stacked into one SVG with CSS keyframes — no GIF, no screen capture.

assets/demo.svg — the README demo
"""
import functools
import http.server
import io
import re
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rich.console import Console, Group  # noqa: E402
from rich.segment import Segment  # noqa: E402
from rich.terminal_theme import TerminalTheme  # noqa: E402
from rich.text import Text  # noqa: E402

from jsrecon import cli  # noqa: E402

WIDTH, ROWS = 100, 30
PORT = 8080
OUT = ROOT / "assets"
DIST = ROOT / "examples" / "shop" / "dist"
SEP = "\x1f"
FMT = SEP.join(["{styles}", "{lines}", "{backgrounds}", "{matrix}", "{chrome}", "{width}",
                "{height}", "{terminal_x}", "{terminal_y}", "{terminal_width}",
                "{terminal_height}", "{char_height}", "{line_height}"])

# httpcrabber's palette, so the two READMEs look like one suite
THEME = TerminalTheme(
    (11, 15, 12), (214, 222, 214),
    [(11, 15, 12), (255, 59, 59), (57, 255, 20), (255, 204, 0),
     (127, 140, 255), (255, 47, 208), (0, 229, 255), (214, 222, 214)],
    [(95, 111, 95), (255, 110, 110), (150, 255, 130), (255, 225, 110),
     (170, 180, 255), (255, 130, 230), (120, 245, 255), (255, 255, 255)],
)


class Lines:
    """Render only the last `rows` lines — a scrolled terminal."""

    def __init__(self, renderables, rows: int):
        self.renderables, self.rows = renderables, rows

    def __rich_console__(self, console, options):
        lines = console.render_lines(Group(*self.renderables), options, pad=False)
        lines = lines[-self.rows:]
        lines += [[]] * (self.rows - len(lines))
        for line in lines:
            yield from line
            yield Segment.line()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    handler = functools.partial(Quiet, directory=str(DIST))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def console() -> Console:
    # legacy_windows off, or Rich falls back to ASCII rules when run on Windows
    return Console(record=True, width=WIDTH, force_terminal=True, color_system="truecolor",
                   legacy_windows=False, file=io.StringIO())


def prompt(cmd: str, cursor: bool = False) -> Text:
    t = Text.assemble(("~/shop", "bold #7f8cff"), " ", ("$ ", "bold #39ff14"), (cmd, "#d6ded6"))
    if cursor:
        t.append("▌", style="#39ff14")
    return t


def real_output():
    """Run jsrecon on the demo shop and return its report as Rich lines."""
    target = f"http://localhost:{PORT}"
    srv = serve()
    tmp = Path(tempfile.mkdtemp())
    try:
        a, stats = cli.analyse(target, src_dir=tmp / "recon" / "sources")
        api_files = sorted(p.name for p in (tmp / "recon" / "sources" / "src" / "api").iterdir())
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    con = console()
    cli.print_summary(con, a, target, stats)
    # re-parse the recorded ANSI into Text lines we can reveal one at a time
    ansi = con.export_text(styles=True)
    lines = [Text.from_ansi(line) for line in ansi.rstrip("\n").split("\n")]
    return target, lines, api_files


def scenario():
    target, report, api_files = real_output()
    cmd = f"jsrecon map {target} -o recon"
    frames, screen = [], []

    def show(duration: float, *extra):
        frames.append((list(screen) + list(extra), duration))

    show(0.6, prompt("", cursor=True))
    for i in range(1, len(cmd) + 1, 2):
        show(0.045, prompt(cmd[:i], cursor=True))
    show(0.35, prompt(cmd, cursor=True))
    screen.append(prompt(cmd))
    for ch in "-\\|/-\\":
        show(0.09, Text.assemble((ch, "bold #39ff14"), " ", ("analysing…", "bold")))

    # the report streams in; hold on the endpoints table so it can be read
    end_of_endpoints = next((i for i, ln in enumerate(report) if ln.plain.startswith("GraphQL")), len(report))
    for i, line in enumerate(report):
        screen.append(line)
        if line.plain.strip() or i < 3:
            show(0.05)
        if i == end_of_endpoints - 1:
            show(2.6)
    screen.append(Text(""))
    screen.append(Text.from_markup("[green]wrote[/green] recon/ (findings.json, findings.md, openapi.json, sources/)"))
    show(1.6)
    ls = "ls recon/sources/src/api"
    for i in range(1, len(ls) + 1, 3):
        show(0.04, prompt(ls[:i], cursor=True))
    screen.append(prompt(ls))
    screen.append(Text("  ".join(api_files), style="bold #00e5ff"))
    screen.append(prompt("", cursor=True))
    show(4.5)
    return frames


def render(frames, title: str) -> str:
    total = sum(d for _, d in frames)
    css, body, shared = [], [], {}
    head = None
    t0 = 0.0
    for i, (renderables, duration) in enumerate(frames):
        con = console()
        con.print(Lines(renderables, ROWS))
        (styles, _lines, backgrounds, matrix, chrome, width, height, tx, ty, tw, th, ch,
         lh) = con.export_svg(code_format=FMT, unique_id=f"f{i}", title=title,
                              theme=THEME).split(SEP)
        if head is None:
            head = (chrome, width, height, tx, ty, tw, th, ch, lh)
        # Rich emits its own classes and a clipPath per line per frame: fold
        # identical styles into shared classes and drop the per-line clips
        local = {}
        for rule, css_body in re.findall(rf"\.f{i}-(r\d+) \{{ (.*?) \}}", styles):
            local[rule] = shared.setdefault(css_body, f"c{len(shared)}")
        backgrounds, matrix = (
            re.sub(r' clip-path="url\(#[^)]*\)"', "",
                   re.sub(rf'class="f{i}-(r\d+)"', lambda m, lc=local: f'class="{lc[m.group(1)]}"', part))
            for part in (backgrounds, matrix)
        )
        a, b = t0 / total * 100, (t0 + duration) / total * 100
        keys = f"0%{{opacity:1}}{b:.3f}%{{opacity:0}}" if i == 0 else \
            f"0%{{opacity:0}}{a:.3f}%{{opacity:1}}{b:.3f}%{{opacity:0}}"
        css.append(f"@keyframes k{i}{{{keys}}}.f{i}{{animation:k{i} {total:.2f}s step-end infinite}}")
        body.append(f'<g class="fr f{i}">{backgrounds}<g class="mx">{matrix}</g></g>')
        t0 += duration
    chrome, width, height, tx, ty, tw, th, ch, lh = head
    style = f"""
    .mx {{ font-family: "Fira Code", ui-monospace, Menlo, Consolas, monospace; font-size: {ch}px; line-height: {lh}px; font-variant-east-asian: full-width }}
    .f0-title {{ font-size: 18px; font-weight: bold; font-family: arial }}
    .fr {{ opacity: 0 }}
    {"".join(f".{c}{{{v}}}" for v, c in shared.items())}
    {"".join(css)}
    """
    svg = f"""<svg class="rich-terminal" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">
<!-- Generated by scripts/gen_demo.py from a real jsrecon run on examples/shop -->
<style>{style}</style>
<defs><clipPath id="clip-terminal"><rect x="0" y="0" width="{tw}" height="{th}"/></clipPath></defs>
{chrome}
<g transform="translate({tx}, {ty})" clip-path="url(#clip-terminal)">
{"".join(body)}
</g>
</svg>
"""
    return re.sub(r"\n\s+", "\n", svg)


def main() -> None:
    frames = scenario()
    path = OUT / "demo.svg"
    path.write_text(render(frames, "jsrecon"), encoding="utf-8", newline="\n")
    total = sum(d for _, d in frames)
    print(f"  {path.relative_to(ROOT)}  {len(frames)} frames, {total:.1f}s, "
          f"{path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
