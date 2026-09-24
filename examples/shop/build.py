"""Build the demo shop the way a real front-end ships: one minified, hashed
bundle plus its source map (with `sourcesContent`), and an index.html.

    python examples/shop/build.py          # needs Node.js; esbuild is fetched by npx

Then serve it and point jsrecon at it:

    python -m http.server 8080 -d examples/shop/dist
    jsrecon map http://localhost:8080

The built `dist/` is committed, so you only need this to change the sources.
"""
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
ESBUILD = "esbuild@0.28.2"

INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Shop</title>
  <script type="module" crossorigin src="/{bundle}"></script>
</head>
<body>
  <div id="app"></div>
</body>
</html>
"""


def main() -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    meta = HERE / "meta.json"
    npx = shutil.which("npx") or "npx"
    subprocess.run([npx, "--yes", ESBUILD, "src/main.ts", "--bundle", "--minify", "--sourcemap",
                    "--format=esm", "--target=es2020", "--outdir=dist/assets",
                    "--entry-names=[name]-[hash]", f"--metafile={meta.name}"],
                   cwd=HERE, check=True)
    outputs = json.loads(meta.read_text(encoding="utf-8"))["outputs"]
    meta.unlink()
    bundle = next(k for k in outputs if k.endswith(".js")).removeprefix("dist/")
    (DIST / "index.html").write_text(INDEX.format(bundle=bundle), encoding="utf-8", newline="\n")
    print(f"built dist/{bundle} (+ .map) and dist/index.html")


if __name__ == "__main__":
    main()
