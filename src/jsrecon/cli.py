"""jsrecon command line.

    jsrecon map <url|path> [--out DIR] [--json] [--no-secrets] [--timeout N]

Fetches the JavaScript, unpacks any source maps, parses it and prints what it
found. With --out it also writes the recovered original sources and the reports.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__, report, sourcemaps
from .extract import Analysis, analyze_code
from .fetch import Loader

METHOD_STYLE = {"GET": "bold cyan", "POST": "bold magenta", "PUT": "bold yellow", "PATCH": "bold yellow",
                "DELETE": "bold red", "HEAD": "bold blue", "OPTIONS": "bold blue"}


class NoJavaScript(RuntimeError):
    pass


def analyse(target: str, timeout: float = 20.0, src_dir: Path | None = None,
            status=None) -> tuple[Analysis, dict]:
    """Fetch, unpack and analyse `target`. Returns the deduped Analysis and run
    stats. `src_dir` receives recovered original sources; `status` is an
    optional context manager shown while parsing (a rich spinner)."""
    from contextlib import nullcontext

    started = time.perf_counter()
    n_maps = n_originals = 0
    total = Analysis()
    with Loader(timeout=timeout) as loader:
        assets = loader.collect(target)            # RuntimeError on a bad target
        if not assets:
            raise NoJavaScript("no JavaScript found at that target.")
        with status or nullcontext():
            for asset in assets:
                # originals first: on a tie, dedupe keeps the finding from the
                # readable source rather than from the minified bundle
                sm = sourcemaps.load(asset.text, asset.map_base, asset.fetch)
                if sm is not None:
                    originals = sm.originals()
                    n_maps += 1
                    n_originals += len(originals)
                    for name, content in originals:
                        total.merge(analyze_code(content, sourcemaps._safe(name)))
                    if src_dir is not None:
                        sourcemaps.write_originals(sm, src_dir)
                total.merge(analyze_code(asset.text, asset.label))
    total.dedupe()
    stats = {"assets": len(assets), "maps": n_maps, "originals": n_originals,
             "seconds": time.perf_counter() - started}
    return total, stats


def write_reports(a: Analysis, target: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "findings.json").write_text(report.to_json(a, target), encoding="utf-8")
    (out_dir / "findings.md").write_text(report.to_markdown(a, target), encoding="utf-8")
    (out_dir / "openapi.json").write_text(json.dumps(report.to_openapi(a, target), indent=2), encoding="utf-8")


def _run_map(args: argparse.Namespace) -> int:
    from rich.console import Console

    # with --json, stdout carries only JSON (pipe it to jq); the table goes to stderr
    console = Console(stderr=args.json)
    err = Console(stderr=True)
    out_dir = Path(args.out) if args.out else None
    src_dir = out_dir / "sources" if out_dir else None

    try:
        total, stats = analyse(args.target, args.timeout, src_dir,
                               status=console.status("[bold]analysing…", spinner="line"))
    except NoJavaScript as e:
        err.print(f"[yellow]{e}[/yellow]")
        return 1
    except RuntimeError as e:
        err.print(f"[red]error:[/red] {e}")
        return 2
    if args.no_secrets:
        total.secrets = []

    print_summary(console, total, args.target, stats)

    if out_dir:
        write_reports(total, args.target, out_dir)
        err.print(f"[green]wrote[/green] {out_dir}/ (findings.json, findings.md, openapi.json"
                  + (", sources/" if src_dir and src_dir.exists() else "") + ")")

    if args.json:
        # machine output is always UTF-8, whatever the console code page is
        sys.stdout.flush()
        sys.stdout.buffer.write((report.to_json(total, args.target) + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    return 0


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _table(title: str, style: str = "bold"):
    from rich.table import Table

    return Table(title=title, title_justify="left", title_style=style, header_style="dim",
                 box=None, padding=(0, 2, 0, 1), pad_edge=False)


def print_summary(console, a: Analysis, target: str, stats: dict) -> None:
    console.rule(f"[bold]jsrecon[/bold] [cyan]{target}[/cyan]")
    head = [_plural(stats["assets"], "asset")]
    if stats["maps"]:
        head.append(f"[green]{_plural(stats['originals'], 'original file')} from "
                    f"{_plural(stats['maps'], 'source map')}[/green]")
    head += [f"{_plural(len(a.sources), 'file')} parsed", f"{stats['seconds']:.2f}s"]
    console.print(" · ".join(head) + "\n")

    if a.endpoints:
        t = _table(f"Endpoints ({len(a.endpoints)})")
        t.add_column("METHOD"); t.add_column("URL", overflow="fold"); t.add_column("FOUND IN", style="dim"); t.add_column("")
        for e in a.endpoints[:200]:
            m = e.method or "—"
            kind = "[green]call[/green]" if e.kind == "call" else "[dim]literal[/dim]"
            t.add_row(f"[{METHOD_STYLE.get(m, 'dim')}]{m}[/]", e.url, report.where(e.source, e.line), kind)
        console.print(t, "")
    if a.graphql:
        t = _table(f"GraphQL ({len(a.graphql)})")
        t.add_column("OP"); t.add_column("NAME"); t.add_column("FOUND IN", style="dim")
        for g in a.graphql[:100]:
            t.add_row(f"[magenta]{g.operation}[/magenta]", f"[bold]{g.name}[/bold]", report.where(g.source, g.line))
        console.print(t, "")
    if a.routes:
        t = _table(f"Client-side routes ({len(a.routes)})")
        t.add_column("PATH", overflow="fold"); t.add_column("FOUND IN", style="dim")
        for r in a.routes[:100]:
            t.add_row(r.path, report.where(r.source, r.line))
        console.print(t, "")
    if a.secrets:
        t = _table(f"Secrets not meant for the client ({len(a.secrets)})", "bold red")
        t.add_column("SEV"); t.add_column("KIND"); t.add_column("PREVIEW"); t.add_column("FOUND IN", style="dim")
        for s in a.secrets[:100]:
            sev = {"high": "bold red", "medium": "yellow"}.get(s.severity, "dim")
            t.add_row(f"[{sev}]{s.severity}[/]", s.label, s.preview, report.where(s.source, s.line))
        console.print(t, "")
    if not (a.endpoints or a.graphql or a.routes or a.secrets):
        console.print("[dim]nothing recognised.[/dim]")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jsrecon", description="Map a web app's JavaScript to its API.")
    p.add_argument("--version", action="version", version=f"jsrecon {__version__}")
    sub = p.add_subparsers(dest="command")

    m = sub.add_parser("map", help="analyse a URL or local .js files")
    m.add_argument("target", help="page URL, .js URL, file, or directory")
    m.add_argument("-o", "--out", help="write recovered sources and reports into this directory")
    m.add_argument("--json", action="store_true", help="also print findings as JSON to stdout")
    m.add_argument("--no-secrets", action="store_true", help="skip the client-secret audit")
    m.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout, seconds (default 20)")
    m.set_defaults(func=_run_map)
    return p


def main(argv: list[str] | None = None) -> int:
    # a legacy Windows console (cp1251, cp437…) can't encode every character a
    # bundle may contain; degrade to "?" instead of crashing mid-report
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    argv = list(sys.argv[1:] if argv is None else argv)
    # allow `jsrecon <target>` as shorthand for `jsrecon map <target>`
    if argv and argv[0] not in ("map", "-h", "--help", "--version"):
        argv.insert(0, "map")
    args = build_parser().parse_args(argv)
    if not getattr(args, "command", None):
        build_parser().print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
