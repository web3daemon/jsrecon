"""Instagram Reels 9:16 with burned-in captions — the httpcrabber reels kit, for jsrecon.

    python scripts/gen_reels.py [--music FILE --at SECONDS]     # → build/media/reels/

Every frame is 1080×1920, built in Chrome from an HTML template: the logo on top,
a real jsrecon terminal frame in the middle, the caption under it. Nothing sits in
Instagram's overlays — the buttons on the right (140 px) and the caption at the
bottom (the last ~420 px). The first scene is the result itself, not the logo:
viewers decide in the first two seconds.

Everything on screen is a real run on examples/shop (served on localhost), the
same run as the README demo. Writes jsrecon-ru.mp4 / jsrecon-en.mp4 with an .srt
next to each; with --music the track plays under them from SECONDS on.
"""
import argparse
import hashlib
import html
import io
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_demo import PORT, THEME, Lines, serve  # noqa: E402
from gen_logo import chrome_png, find_chrome  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.syntax import Syntax  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

from jsrecon import cli, report  # noqa: E402

OUT = ROOT / "build" / "media" / "reels"
CACHE = ROOT / "build" / "media" / ".frames" / "reels"
W, H, FPS = 1080, 1920, 30
COLS, ROWS = 46, 19                  # a narrow terminal: big type on a phone
NEON, CYAN, MAGENTA, DIM = "bold #39ff14", "#00e5ff", "bold #ff2fd0", "#5f6f5f"
METHOD = {"GET": "bold #00e5ff", "POST": "bold #ff2fd0", "PUT": "bold #ffcc00", "DELETE": "bold #ff3b3b"}


@dataclass
class Scene:
    caption: str                                   # **this** is highlighted
    frames: list[tuple[Path, float]] = field(default_factory=list)
    card: str | None = None                        # HTML instead of a frame (the end card)


# ── the real run ─────────────────────────────────────────────────────────────

def run():
    target = f"http://localhost:{PORT}"
    srv = serve()
    tmp = Path(tempfile.mkdtemp())
    try:
        a, stats = cli.analyse(target, src_dir=tmp / "sources")
        tree = sorted(p.relative_to(tmp / "sources").as_posix() for p in (tmp / "sources").rglob("*") if p.is_file())
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    return target, a, stats, tree


# ── terminal frames ──────────────────────────────────────────────────────────

def terminal_png(renderables, chrome: str, rows: int = ROWS) -> Path:
    con = Console(record=True, width=COLS, force_terminal=True, color_system="truecolor",
                  legacy_windows=False, file=io.StringIO())
    con.print(Lines(renderables, rows))
    svg = con.export_svg(title="jsrecon", theme=THEME, unique_id="t")
    png = CACHE / f"term_{hashlib.sha1(svg.encode()).hexdigest()[:16]}.png"
    if not png.exists():
        png.parent.mkdir(parents=True, exist_ok=True)
        view = svg.split('viewBox="0 0 ', 1)[1].split('"', 1)[0].split()
        page = png.with_suffix(".html")
        page.write_text(f'<html><body style="margin:0">{svg}</body></html>', encoding="utf-8")
        chrome_png(page, png, (int(float(view[0])), int(float(view[1]))), scale=2)
    return png


def table(*cols):
    t = Table(box=None, padding=(0, 2, 0, 0), pad_edge=False, show_header=True, header_style=DIM)
    for c in cols:
        t.add_column(c)
    return t


def where(source: str, line: int) -> str:
    return f"{Path(source).name}:{line}"


def endpoints_view(a, n: int = 11):
    t = table("METHOD", "PATH", "FOUND IN")
    calls = [e for e in a.endpoints if e.kind == "call" and e.url.startswith("/")]
    for e in calls[:n]:
        t.add_row(Text(e.method, style=METHOD.get(e.method, "bold")), e.url, Text(where(e.source, e.line), style=DIM))
    return [Text(f"Endpoints ({len(a.endpoints)})", style="bold"), t]


def command_frames(chrome: str, command: str, result: list) -> list[tuple[Path, float]]:
    prompt = Text("$ ", style=NEON)
    out = []
    for k in (0.3, 0.6, 1.0):
        line = prompt + Text(command[:int(len(command) * k)], style="bold white") + Text("▌", style=NEON)
        out.append((terminal_png([line], chrome), 0.16))
    out.append((terminal_png([prompt + Text(command, style="bold white"), Text(""), *result], chrome), 2.2))
    return out


def sources_view(tree: list[str], stats: dict):
    lines = [Text(f"{stats['originals']} original files from 1 source map", style=NEON), Text("")]
    dirs_done = set()
    for path in tree:
        parts = path.split("/")
        for depth in range(len(parts) - 1):
            d = "/".join(parts[:depth + 1])
            if d not in dirs_done:
                dirs_done.add(d)
                lines.append(Text("  " * depth + parts[depth] + "/", style="bold #7f8cff"))
        lines.append(Text("  " * (len(parts) - 1) + parts[-1], style=CYAN))
    return lines


def openapi_view(a, target: str):
    spec = report.to_openapi(a, target)
    op = spec["paths"]["/orders/{id}/refund"]["post"]
    snippet = {"/orders/{id}/refund": {"post": {"parameters": op["parameters"]}}}
    code = json.dumps(snippet, indent=2)
    return [Text("openapi.json", style="bold"), Text(""),
            Syntax(code, "json", theme="monokai", background_color="#0b0f0c", word_wrap=True)]


def graph_routes_view(a):
    g = table("OP", "NAME")
    for op in a.graphql:
        g.add_row(Text(op.operation, style=MAGENTA), Text(op.name, style="bold"))
    r = table("SCREEN")
    for route in a.routes[:6]:
        r.add_row(route.path)
    return [Text(f"GraphQL ({len(a.graphql)})", style="bold"), g, Text(""),
            Text(f"Screens ({len(a.routes)})", style="bold"), r]


def secret_view(a):
    s = a.secrets[0]
    t = table("SEV", "KIND", "PREVIEW")
    t.add_row(Text(s.severity, style="bold #ff3b3b"), s.label, s.preview)
    return [Text("Secrets not meant for the client (1)", style="bold #ff3b3b"), t, Text(""),
            Text(f"found in {where(s.source, s.line)}", style=DIM),
            Text("value masked — never printed in full", style=DIM)]


# ── frame and video ──────────────────────────────────────────────────────────

CSS = f"""
body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; position:relative; color:#e8f0e8;
  font-family:'JetBrains Mono','Cascadia Code',Consolas,monospace;
  background: radial-gradient(circle at 20% 12%, rgba(127,140,255,.18), transparent 42%),
              radial-gradient(circle at 85% 88%, rgba(255,47,208,.15), transparent 48%), #0b0f0c; }}
body::before {{ content:""; position:absolute; inset:0;
  background-image: linear-gradient(rgba(57,255,20,.06) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(57,255,20,.06) 1px, transparent 1px);
  background-size: 32px 32px; }}
.logo {{ position:absolute; left:40px; top:120px; width:560px; }}
.stage {{ position:absolute; left:40px; right:150px; top:330px; height:1000px;
  display:flex; align-items:center; justify-content:center; }}
.stage img {{ width:890px; max-height:1000px; object-fit:contain; border-radius:16px;
  box-shadow: 0 0 0 2px rgba(57,255,20,.35), 0 20px 60px rgba(0,0,0,.6); }}
.cap {{ position:absolute; left:60px; right:150px; top:1360px; font-size:50px; line-height:1.28;
  font-weight:700; text-shadow:0 2px 12px #000; }}
.cap b {{ color:#39ff14; }}
.card {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center;
  justify-content:center; gap:56px; padding-bottom:300px; }}
.card img {{ width:900px; }}
.card .cmd {{ font-size:52px; font-weight:700; color:#39ff14; padding:26px 40px;
  border:3px solid rgba(57,255,20,.5); border-radius:18px; background:#0f1511; }}
.card .sub {{ font-size:40px; color:#00e5ff; }}
"""


def _caption_html(text: str) -> str:
    parts = html.escape(text).split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


def compose(scene: Scene, content: Path | None, work: Path) -> Path:
    logo = (ROOT / "assets" / "logo.svg").as_uri()
    key = hashlib.sha1(f"{content}|{scene.caption}|{scene.card}|{CSS}".encode()).hexdigest()[:16]
    png = work / f"frame_{key}.png"
    if png.exists():
        return png
    if scene.card is not None:
        body = f'<div class="card"><img src="{logo}">{scene.card}</div>'
    else:
        body = (f'<img class="logo" src="{logo}"><div class="stage"><img src="{content.as_uri()}">'
                f'</div><div class="cap">{_caption_html(scene.caption)}</div>')
    page = png.with_suffix(".html")
    page.write_text(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head>"
                    f"<body>{body}</body></html>", encoding="utf-8")
    chrome_png(page, png, (W, H))
    return png


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def build(name: str, scenes: list[Scene], work: Path, music: Path | None, at: float) -> Path:
    timeline, srt, t = [], [], 0.0
    for scene in scenes:
        start = t
        for content, duration in scene.frames or [(None, 2.6)]:
            timeline.append((compose(scene, content, work), duration))
            t += duration
        if scene.card is None:
            srt.append(f"{len(srt) + 1}\n{_srt_time(start)} --> {_srt_time(t)}\n{scene.caption.replace('**', '')}\n")
    OUT.mkdir(parents=True, exist_ok=True)
    listing = work / f"{name}.txt"
    lines = []
    for png, duration in timeline:
        lines += [f"file '{png.as_posix()}'", f"duration {duration:.3f}"]
    lines.append(f"file '{timeline[-1][0].as_posix()}'")
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    audio = (["-ss", f"{at:.3f}", "-i", str(music)] if music
             else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
    afx = ["-af", f"afade=t=out:st={t - 0.6:.3f}:d=0.6"] if music else []
    target = OUT / f"{name}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), *audio,
        "-vf", f"fps={FPS},format=yuv420p", "-map", "0:v", "-map", "1:a", "-t", f"{t:.2f}", *afx,
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-c:a", "aac", "-b:a", "192k" if music else "64k",
        "-movflags", "+faststart", str(target)], check=True)
    target.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")
    print(f"  {target.relative_to(ROOT)}  {t:.1f}s  {target.stat().st_size / 1024 / 1024:.1f} MB")
    return target


# ── the reel ─────────────────────────────────────────────────────────────────

TEXT = {
    "ru": ["Наведи на сайт — получи **его API**",
           "Одна команда: **jsrecon map**",
           "Source map в проде? Внутри **весь исходник**",
           "`${id}` в коде → **/orders/{id}** в OpenAPI",
           "GraphQL и **все экраны** приложения",
           "Ключ в сборке? Найдёт — **и замаскирует**"],
    "en": ["Point it at a site — get **its API**",
           "One command: **jsrecon map**",
           "Source map in prod? **All of your source** is in it",
           "`${id}` in code → **/orders/{id}** in OpenAPI",
           "GraphQL and **every screen** of the app",
           "A key in the build? Found — **and masked**"],
}
END = {
    "ru": '<div class="cmd">$ pipx install jsrecon</div><div class="sub">open source · ссылка в профиле</div>',
    "en": '<div class="cmd">$ pipx install jsrecon</div><div class="sub">open source · link in bio</div>',
}


def scenes(chrome: str, lang: str, data) -> list[Scene]:
    target, a, stats, tree = data
    summary = [Text.from_markup(f"[{NEON}]{len(a.endpoints)}[/] endpoints · [{NEON}]{len(a.graphql)}[/] GraphQL ops"),
               Text.from_markup(f"[{NEON}]{len(a.routes)}[/] screens · [bold #ff3b3b]1[/] leaked key"),
               Text(f"{stats['originals']} source files · {stats['seconds']:.2f}s", style=DIM)]
    text = TEXT[lang]
    return [
        Scene(text[0], [(terminal_png(endpoints_view(a), chrome), 2.6)]),
        Scene(text[1], command_frames(chrome, f"jsrecon map {target}", summary)),
        Scene(text[2], [(terminal_png(sources_view(tree, stats), chrome), 2.6)]),
        Scene(text[3], [(terminal_png(openapi_view(a, target), chrome), 2.8)]),
        Scene(text[4], [(terminal_png(graph_routes_view(a), chrome), 2.6)]),
        Scene(text[5], [(terminal_png(secret_view(a), chrome), 2.4)]),
        Scene("", card=END[lang]),
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Instagram Reels with captions")
    ap.add_argument("--music", type=Path, help="audio track to lay under the reels")
    ap.add_argument("--at", type=float, default=0.0, help="start the track from this second")
    args = ap.parse_args()
    chrome = find_chrome()
    if not chrome or not shutil.which("ffmpeg"):
        sys.exit("needs Chrome/Chromium (set JSRECON_BROWSER) and ffmpeg on PATH")
    CACHE.mkdir(parents=True, exist_ok=True)
    data = run()
    for lang in ("ru", "en"):
        build(f"jsrecon-{lang}", scenes(chrome, lang, data), CACHE, args.music, args.at)


if __name__ == "__main__":
    main()
