"""Demo video for social posts: the same frames as assets/demo.svg, as MP4.

    python scripts/gen_video.py [OUT_DIR]        # default build/media

Needs Chrome/Chromium (frame rendering) and ffmpeg on PATH. Writes:

    x.mp4       1920×1080 — X / YouTube
    feed.mp4    1080×1350 — Instagram / Telegram feed (4:5)

Each terminal frame is rendered once (cached in OUT_DIR/.frames), the backdrop
with the logo once per layout; ffmpeg lays the frames over it with the
durations from the demo scenario. The 9:16 reel is a separate, 1-bit piece.
"""
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
}


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
    else:
        body = f"""
        <img src="{logo}" style="position:absolute;left:40px;top:{fy - 285}px;width:1000px">
        <ul style="top:{bottom}px">{points}</ul>{foot}"""
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
    .foot {{ position:absolute; left:0; right:0; bottom:{26 if kind == 'wide' else 44}px; text-align:center; color:#5f6f5f; font-size:24px; }}
    </style></head><body>{body}</body></html>""", encoding="utf-8")
    png = work / f"bg_{layout}.png"
    chrome_png(html, png, (width, height))
    return png


def encode(frames: list[tuple[Path, float]], bg: Path, layout: str, out: Path) -> None:
    width, height, fw, fy, _ = LAYOUTS[layout]
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
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",   # a silent track: every platform accepts it
        "-filter_complex",
        f"[1:v]scale={fw}:-2:flags=lanczos,fps={FPS}[fg];"
        f"[0:v][fg]overlay=({width}-w)/2:{fy}:shortest=1,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a", "-t", f"{sum(d for _, d in frames):.2f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(out),
    ], check=True)
    listing.unlink()


def main() -> None:
    if not find_chrome() or not shutil.which("ffmpeg"):
        sys.exit("needs Chrome/Chromium (set JSRECON_BROWSER) and ffmpeg on PATH")
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "media"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, fw_px, fh_px = render_frames(out_dir / ".frames")
    with tempfile.TemporaryDirectory() as tmp:
        for layout, (_, _, fw, _, _) in LAYOUTS.items():
            bg = background(layout, Path(tmp), round(fh_px * fw / fw_px))
            target = out_dir / f"{layout}.mp4"
            encode(frames, bg, layout, target)
            print(f"  {target}  {target.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
