"""복복복 화면을 Figma에서 편집할 수 있는 SVG로 내보내기

export_for_figma.py 가 만든 화면별 단독 HTML(figma-export-bokbok/html)을 헤드리스 Chrome으로 열고,
html2svg.js 로 글자·박스·아이콘을 SVG 요소로 바꿔 저장합니다. 이 SVG를 Figma에 올리면
편집 가능한 텍스트·도형 레이어가 됩니다.

    python scripts/export_figma_svg.py --src ../figma-export-bokbok/html --out ../figma-export-bokbok/svg

필요한 것: Google Chrome(macOS 경로)
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTHS = {"desktop": 1440, "mobile": 390}
CONVERTER = (ROOT / "scripts" / "html2svg.js").read_text(encoding="utf-8")

PARENT = """<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0}}iframe{{display:block;border:0;width:{w}px;height:900px}}</style></head>
<body><iframe id="f" src="{src}"></iframe><pre id="out"></pre>
<script>
const f = document.getElementById('f');
addEventListener('message', (e) => {{
  if (e.data && e.data.h) {{ f.style.height = e.data.h + 'px'; setTimeout(() => f.contentWindow.postMessage('go', '*'), 300); }}
  if (e.data && e.data.svg) {{ document.getElementById('out').textContent = e.data.svg; }}
}});
</script></body></html>"""


def convert(html_file: Path, width: int, out: Path) -> tuple[Path, int]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        child = tmp / "page.html"
        child.write_text(html_file.read_text(encoding="utf-8").replace("</body>", f"<script>{CONVERTER}</script></body>"), encoding="utf-8")
        parent = tmp / "parent.html"
        parent.write_text(PARENT.format(w=width, src=child.as_uri()), encoding="utf-8")
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
               "--force-device-scale-factor=1", "--virtual-time-budget=15000", f"--user-data-dir={tmp / 'p'}",
               f"--window-size={max(width, 1000)},900", "--dump-dom", parent.as_uri()]
        dom = subprocess.run(cmd, capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
    if not m or not m.group(1).strip():
        raise RuntimeError(f"변환 실패: {html_file.name} ({width}px)")
    svg = html.unescape(m.group(1))
    out.write_text(svg, encoding="utf-8")
    return out, len(svg)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", default=str(ROOT.parent / "figma-export-bokbok" / "html"))
    parser.add_argument("--out", default=str(ROOT.parent / "figma-export-bokbok" / "svg"))
    parser.add_argument("--only", default="", help="이 글자가 들어간 화면만 (시험용)")
    args = parser.parse_args()
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pages = sorted(p for p in src.glob("[0-9][0-9]-*.html") if args.only in p.name)
    jobs = [(p, w, out / f"{p.stem}--{k}.svg") for p in pages for k, w in WIDTHS.items()]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for path, size in pool.map(lambda j: convert(*j), jobs):
            print(f"SVG  {path.name}  {size // 1024}KB")


if __name__ == "__main__":
    main()
