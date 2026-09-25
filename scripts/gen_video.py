"""Demo video for social posts: the same frames as assets/demo.svg, as MP4.

    python scripts/gen_video.py [OUT_DIR] [--music FILE --at SECONDS]    # default build/media

Needs Chrome/Chromium (frame rendering) and ffmpeg on PATH. Writes:

    x.mp4       1920×1080 — X / YouTube
    feed.mp4    1080×1350 — Instagram / Telegram feed (4:5)
    reels.mp4   1080×1920 — Reels / Shorts, the same card layout as httpcrabber's reels

With --music the track is laid under every video from SECONDS on (pick the spot
so the drop lands when the report starts streaming, ~2.3 s in); otherwise the
videos carry a silent track.

Each terminal frame is rendered once (cached in OUT_DIR/.frames), the backdrop
with the logo once per layout; ffmpeg lays the frames over it with the
durations from the demo scenario. The beat-cut 1-bit reel is a separate piece.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_demo import ROWS, THEME, Lines, console, scenario  # noqa: E402
from gen_logo import chrome_png, find_chrome  # noqa: E402

from jsrecon import __version__  # noqa: E402

FPS = 30
POINTS = ["source maps → the original TypeScript",
          "endpoints with methods, GraphQL ops, routes",
          "an OpenAPI 3.1 skeleton, ready for a client"]
# layout: (width, height, terminal frame width, frame y, kind)
LAYOUTS = {
    "x": (1920, 1080, 1320, 134, "wide"),
    "feed": (1080, 1350, 1000, 300, "feed"),
    "reels": (1080, 1920, 1000, 500, "reels"),
}
TAGLINE = "point it at a web app — get the <b>API</b> its JavaScript talks to"


def render_frames(work: Path) -> tuple[list[tuple[Path, float]], int, int]:
    frames = scenario()
    out, size = [], (0, 0)
    work.mkdir(parents=True, exist_ok=True)
    for i, (renderables, duration) in enumerate(frames):
        con = console()
        con.print(Lines(renderables, ROWS))
        svg = con.export_svg(title="jsrecon", theme=THEME, unique_id=f"v{i}")
        vb = svg.split('viewBox="0 0 ', 1)[1].split('"', 1)[0].split()
        w, h = int(float(vb[0])), int(float(vb[1]))
        size = (w, h)
        page = work / f"{i:03d}.html"
        png = work / f"{i:03d}.png"
        html = f'<html><body style="margin:0;background:transparent">{svg}</body></html>'
        if not png.exists() or page.read_text(encoding="utf-8") != html:
            page.write_text(html, encoding="utf-8")
            chrome_png(page, png, (w, h), scale=2)
        out.append((png, duration))
        print(f"\r  frames: {i + 1}/{len(frames)}", end="", flush=True)
    print()
    return out, *size


def background(layout: str, work: Path, frame_h: int) -> Path:
    width, height, fw, fy, kind = LAYOUTS[layout]
    logo = (ROOT / "assets" / "logo.svg").as_uri()
    bottom = fy + frame_h + 34
    foot = f'<div class="foot">github.com/web3daemon/jsrecon · v{__version__}</div>'
    points = "".join(f"<li>{p}</li>" for p in POINTS)
    if kind == "wide":        # the post text says the rest
        body = f"""<img src="{logo}" style="position:absolute;left:{(width - 400) // 2}px;top:12px;width:400px">{foot}"""
    elif kind == "feed":
        body = f"""
        <img src="{logo}" style="position:absolute;left:40px;top:{fy - 285}px;width:1000px">
        <ul style="top:{bottom}px">{points}</ul>{foot}"""
    else:                     # reels: keep clear of the buttons on the right and the caption at the bottom
        body = f"""
        <img src="{logo}" style="position:absolute;left:40px;top:{fy - 290}px;width:1000px">
        <div class="tag" style="top:{bottom + 6}px">{TAGLINE}</div>
        <ul style="top:{bottom + 110}px">{points}</ul>
        <div class="cmd" style="top:{bottom + 320}px">$ pipx install jsrecon</div>{foot}"""
    html = work / f"bg_{layout}.html"
    html.write_text(f"""<html><head><meta charset="utf-8"><style>
    body {{ margin:0; width:{width}px; height:{height}px; overflow:hidden; position:relative;
           background: radial-gradient(circle at 20% 15%, rgba(127,140,255,.16), transparent 45%),
                       radial-gradient(circle at 85% 90%, rgba(255,47,208,.14), transparent 50%), #0b0f0c;
           font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace; color:#d6ded6; }}
    body::before {{ content:""; position:absolute; inset:0;
           background-image: linear-gradient(rgba(57,255,20,.06) 1px, transparent 1px),
                             linear-gradient(90deg, rgba(57,255,20,.06) 1px, transparent 1px);
           background-size: 32px 32px; }}
    ul {{ position:absolute; left:80px; right:60px; margin:0; padding:0; list-style:none; font-size:30px; line-height:1.8; }}
    li::before {{ content:"◆  "; color:#ff2fd0; }}
    .tag {{ position:absolute; left:0; right:0; text-align:center; color:#00e5ff; font-size:32px; padding:0 60px; line-height:1.4; }}
    .tag b {{ color:#39ff14; font-weight:700; }}
    .cmd {{ position:absolute; left:90px; right:90px; padding:22px 30px; border:2px solid rgba(57,255,20,.45);
            border-radius:14px; background:#0f1511; color:#39ff14; font-size:34px; font-weight:700; }}
    .foot {{ position:absolute; left:0; right:0; bottom:{ {'wide': 26, 'feed': 44}.get(kind, 70) }px; text-align:center; color:#5f6f5f; font-size:24px; }}
    </style></head><body>{body}</body></html>""", encoding="utf-8")
    png = work / f"bg_{layout}.png"
    chrome_png(html, png, (width, height))
    return png


def encode(frames: list[tuple[Path, float]], bg: Path, layout: str, out: Path,
           music: Path | None = None, at: float = 0.0) -> None:
    width, height, fw, fy, _ = LAYOUTS[layout]
    total = sum(d for _, d in frames)
    audio = (["-ss", f"{at:.3f}", "-i", str(music)] if music
             else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])   # a silent track: every platform accepts it
    afx = ["-af", f"afade=t=out:st={total - 0.6:.3f}:d=0.6"] if music else []
    listing = out.with_suffix(".txt")
    lines = []
    for png, duration in frames:
        lines += [f"file '{png.as_posix()}'", f"duration {duration:.3f}"]
    lines.append(f"file '{frames[-1][0].as_posix()}'")   # concat wants the last frame repeated
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", str(bg),
        "-f", "concat", "-safe", "0", "-i", str(listing),
        *audio,
        "-filter_complex",
        f"[1:v]scale={fw}:-2:flags=lanczos,fps={FPS}[fg];"
        f"[0:v][fg]overlay=({width}-w)/2:{fy}:shortest=1,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a", "-t", f"{total:.2f}", *afx,
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k" if music else "64k", "-movflags", "+faststart", str(out),
    ], check=True)
    listing.unlink()


def main() -> None:
    if not find_chrome() or not shutil.which("ffmpeg"):
        sys.exit("needs Chrome/Chromium (set JSRECON_BROWSER) and ffmpeg on PATH")
    ap = argparse.ArgumentParser(description="render the demo as MP4s")
    ap.add_argument("out_dir", nargs="?", default=str(ROOT / "build" / "media"))
    ap.add_argument("--music", type=Path, help="audio track to lay under the videos")
    ap.add_argument("--at", type=float, default=0.0, help="start the track from this second")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, fw_px, fh_px = render_frames(out_dir / ".frames")
    with tempfile.TemporaryDirectory() as tmp:
        for layout, (_, _, fw, _, _) in LAYOUTS.items():
            bg = background(layout, Path(tmp), round(fh_px * fw / fw_px))
            target = out_dir / f"{layout}.mp4"
            encode(frames, bg, layout, target, args.music, args.at)
            print(f"  {target}  {target.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
