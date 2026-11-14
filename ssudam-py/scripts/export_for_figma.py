"""Figma 작업용 화면 내보내기

실행 중인 쓰담 서버에서 시연 흐름의 각 화면을 순서대로 열어 다음을 만듭니다.

  screens/   화면별 PNG (데스크톱 1440px, 모바일 390px). Figma에 끌어다 놓아 바로 사용
  html/      화면별 단독 HTML (CSS 포함). html.to.design 등으로 Figma 레이어로 변환할 때 사용
  tokens/    디자인 토큰 (색·글자·모서리·그림자) JSON + 한눈에 보는 토큰 시트

⚠️ 서버의 저장 상태를 초기화하고 시연 데이터를 새로 쌓으므로, 반드시 내보내기 전용 서버에 대고 실행하세요.

    SSUDAM_STATE=/tmp/ssudam-export.json SSUDAM_TODAY=2026-11-13 uvicorn app.main:app --port 8010
    python scripts/export_for_figma.py --base http://localhost:8010 --out ../figma-export

필요한 것: Google Chrome, Pillow (pip install pillow)
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FIGMA_MAX = 4096  # Figma는 한 변이 4096px을 넘는 이미지를 축소하므로 그보다 길면 나눠 저장
WIDTHS = {"desktop": 1440, "mobile": 390}

# (파일 이름, 화면 설명, 주소, 열기 전에 보낼 요청들)
SCREENS: list[tuple[str, str, str, list[tuple[str, dict]]]] = [
    ("01-landing", "랜딩", "/", [("/reset", {})]),
    ("02-student-home", "학생 홈 · 체크인 전", "/student", []),
    ("03-student-support", "도움 요청 · 요청 전", "/student/support", []),
    (
        "04-student-checkin-input",
        "학생 홈 · 감정 선택 후 입력 단계",
        "/student?edit=checkin",
        [("/student/checkin", {"emotion": "anxious", "intensity": "3", "note": "발표 준비 때문에 조금 긴장됐다"})],
    ),
    ("05-student-home-checked", "학생 홈 · 체크인 완료", "/student", []),
    ("06-student-insights", "마음 분석", "/student/insights", []),
    (
        "07-student-support-sent",
        "도움 요청 · 요청 보낸 뒤",
        "/student/support?sent=1",
        [
            ("/student/consent", {"key": "trend", "on": "1"}),
            ("/student/support", {"topic": "친구 관계", "message": "요즘 반 친구들과 지내는 게 힘들어요. 조용히 이야기하고 싶어요."}),
        ],
    ),
    ("08-teacher-dashboard", "상담교사 · 요청 현황", "/teacher", []),
    ("09-teacher-student", "상담교사 · 학생 상세 (그래프 공유)", "/teacher/students/S01", []),
    ("10-teacher-student-private", "상담교사 · 학생 상세 (그래프 비공유)", "/teacher/students/S06", []),
    ("11-agencies", "지원기관 추천", "/teacher/agencies?student=S01", []),
    ("12-agency-modal", "지원기관 · 연결 요청 창", "/teacher/agencies?student=S01&refer=AG04", []),
]

# 단독 HTML 안의 링크를 다른 화면 파일로 이어 줌 (폼 버튼은 동작하지 않음)
LINKS = {
    "/": "01-landing.html",
    "/student": "05-student-home-checked.html",
    "/student/insights": "06-student-insights.html",
    "/student/support": "07-student-support-sent.html",
    "/teacher": "08-teacher-dashboard.html",
    "/teacher/students/S01": "09-teacher-student.html",
    "/teacher/students/S06": "10-teacher-student-private.html",
    "/teacher/agencies": "11-agencies.html",
    "/teacher/agencies?student=S01": "11-agencies.html",
}

FREEZE = "<style>*,*::before,*::after{animation:none!important;transition:none!important}html{scroll-behavior:auto}</style>"


def request(base: str, path: str, form: dict | None = None) -> str:
    data = urllib.parse.urlencode(form, doseq=True).encode() if form is not None else None
    with urllib.request.urlopen(urllib.request.Request(base + path, data=data)) as res:
        return res.read().decode("utf-8")


def snapshot(page: str, css: str) -> str:
    """서버가 그린 화면을 CSS를 품은 단독 HTML로 바꿈 (애니메이션은 최종 상태로 고정)"""
    page = re.sub(r'<link rel="stylesheet" href="/static/app\.css[^"]*"\s*/>', lambda _: f"<style>{css}</style>{FREEZE}", page)
    page = re.sub(r'<script src="/static/app\.js"[^>]*></script>', "", page)

    def relink(m: re.Match) -> str:
        target = html.unescape(m.group(1))
        return f'href="{LINKS.get(target, "#")}"' if target.startswith("/") else m.group(0)

    return re.sub(r'href="([^"]*)"', relink, page)


def chrome(args: list[str], profile: Path) -> subprocess.CompletedProcess:
    base = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            "--no-default-browser-check", "--force-device-scale-factor=1", "--virtual-time-budget=6000",
            f"--user-data-dir={profile}"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=120)


FRAME_WINDOW = 1000  # 헤드리스 Chrome은 창을 일정 폭보다 좁게 만들지 못하므로, 좁은 화면은 이 폭의 창 안 iframe에 그림


def _framed(src: Path, width: int, height: int) -> str:
    """정확히 width 폭의 화면으로 그리기 위해 iframe에 담은 페이지"""
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}'
        f'iframe{{display:block;border:0;width:{width}px;height:{height}px}}</style></head>'
        f'<body><iframe src="{src.as_uri()}"></iframe>'
        "<script>addEventListener('message',e=>document.documentElement.setAttribute('data-h',e.data))</script>"
        "</body></html>"
    )


def capture(html_file: Path, width: int, out: Path) -> list[Path]:
    """화면 전체 높이를 잰 뒤 그 높이로 한 장에 찍고, Figma 한도를 넘으면 나눔"""
    report = (
        "<script>addEventListener('load',()=>setTimeout(()=>{const h=document.documentElement.scrollHeight;"
        "document.documentElement.setAttribute('data-h',h);parent.postMessage(h,'*')},800))</script></body>"
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        probe = tmp / "probe.html"
        probe.write_text(html_file.read_text(encoding="utf-8").replace("</body>", report), encoding="utf-8")

        # 1) 높이 재기
        if width >= FRAME_WINDOW:
            dom = chrome([f"--window-size={width},900", "--dump-dom", probe.as_uri()], tmp / "p1").stdout
        else:
            frame = tmp / "frame-probe.html"
            frame.write_text(_framed(probe, width, 900), encoding="utf-8")
            dom = chrome([f"--window-size={FRAME_WINDOW},900", "--dump-dom", frame.as_uri()], tmp / "p1").stdout
        m = re.search(r'data-h="(\d+)"', dom)
        if not m:
            raise RuntimeError(f"높이를 재지 못했습니다: {html_file.name}")
        height = int(m.group(1))

        # 2) 그 높이로 찍기
        if width >= FRAME_WINDOW:
            chrome([f"--window-size={width},{height}", f"--screenshot={out}", html_file.as_uri()], tmp / "p2")
        else:
            frame = tmp / "frame.html"
            frame.write_text(_framed(html_file, width, height), encoding="utf-8")
            chrome([f"--window-size={FRAME_WINDOW},{height}", f"--screenshot={out}", frame.as_uri()], tmp / "p2")
            with Image.open(out) as full:
                full.crop((0, 0, width, height)).save(out, optimize=True)

    image = Image.open(out)
    if image.width != width:
        raise RuntimeError(f"{out.name}: 폭이 {image.width}px로 찍혔습니다 (기대 {width}px)")
    if image.height <= FIGMA_MAX:
        return [out]
    parts = math.ceil(image.height / FIGMA_MAX)
    step = math.ceil(image.height / parts)
    files = []
    for i in range(parts):
        part = out.with_name(f"{out.stem}-part{i + 1}.png")
        image.crop((0, i * step, width, min(image.height, (i + 1) * step))).save(part, optimize=True)
        files.append(part)
    out.unlink()
    return files


# ── 디자인 토큰 ────────────────────────────────────────────────────────────────


def oklch_to_hex(value: str) -> str:
    l_pct, c, h = re.match(r"oklch\(([\d.]+)%\s+([\d.]+)\s+([\d.]+)\)", value).groups()
    L, C, H = float(l_pct) / 100, float(c), math.radians(float(h))
    a, b = C * math.cos(H), C * math.sin(H)
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )

    def channel(x: float) -> int:
        x = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
        return round(min(1, max(0, x)) * 255)

    return "#" + "".join(f"{channel(x):02x}" for x in rgb)


def build_tokens(css: str, source_css: str) -> dict:
    palette: dict[str, dict[str, str]] = {}
    for name, value in re.findall(r"--color-([a-z]+(?:-\d+)?):\s*([^;]+);", source_css):
        group, _, shade = name.partition("-")
        palette.setdefault(group, {})[shade or "DEFAULT"] = value.strip().lower()
    for name, value in re.findall(r"--color-((?:stone|amber|sky)-\d+):(oklch\([^)]*\))", css):
        group, shade = name.split("-")
        palette.setdefault(group, {})[shade] = oklch_to_hex(value)
    palette["white"] = {"DEFAULT": "#ffffff"}

    def color_of(cls: str) -> str | None:
        m = re.match(r"(?:bg|text)-([a-z]+)(?:-(\d+))?", cls)
        if not m:
            return None
        return palette.get(m.group(1), {}).get(m.group(2) or "DEFAULT")

    sys.path.insert(0, str(ROOT))
    from app.models import EMOTIONS, STATUS

    def tok(value, type_, desc=None):
        t = {"$type": type_, "$value": value}
        if desc:
            t["$description"] = desc
        return t

    def status_colors(classes: str) -> dict:
        parts = classes.split()
        return {
            "background": tok(color_of(next(p for p in parts if p.startswith("bg-"))), "color"),
            "text": tok(color_of(next(p for p in parts if p.startswith("text-"))), "color"),
        }

    tokens = {
        "$description": "쓰담(SSUDAM) 디자인 토큰 · W3C Design Tokens 형식. 값은 app/static/src/input.css 와 Tailwind 기본 색에서 추출",
        "color": {
            group: {shade: tok(hexv, "color") for shade, hexv in sorted(shades.items(), key=lambda kv: (kv[0] != "DEFAULT", kv[0].zfill(4)))}
            for group, shades in palette.items()
        },
        "emotion": {
            e.id: {"color": tok(e.color.lower(), "color", f"{e.emoji} {e.label}")} for e in EMOTIONS.values()
        },
        "status": {
            key: {**status_colors(s["chip"]), "$description": f"{s['label']} · {s['desc']}"} for key, s in STATUS.items()
        },
        "font": {
            "family": tok("Pretendard Variable, Pretendard, Apple SD Gothic Neo, Noto Sans KR, sans-serif", "fontFamily"),
            "weight": {k: tok(v, "fontWeight") for k, v in
                       {"regular": 400, "medium": 500, "semibold": 600, "bold": 700, "extrabold": 800}.items()},
        },
        "typography": {
            name: tok({"fontFamily": "{font.family}", "fontSize": f"{size}px", "lineHeight": f"{lh}px"}, "typography", use)
            for name, size, lh, use in [
                ("display", 48, 60, "랜딩 큰 제목"),
                ("4xl", 36, 40, "로고(대), 강조 이모지"),
                ("3xl", 30, 36, "학생 홈 인사, 숫자 타일"),
                ("2xl", 24, 32, "화면 제목"),
                ("xl", 20, 28, "로고, 요약 숫자"),
                ("lg", 18, 28, "카드 안 소제목"),
                ("base", 16, 24, "카드 제목"),
                ("sm", 14, 20, "본문 기본"),
                ("xs", 12, 16, "보조 설명, 칩"),
                ("2xs", 11, 16, "그래프 눈금, 작은 라벨"),
            ]
        },
        "radius": {k: tok(v, "dimension") for k, v in
                   {"xl": "12px", "2xl": "16px", "3xl": "24px", "full": "9999px"}.items()},
        "shadow": {
            "card": tok({"offsetX": "0px", "offsetY": "10px", "blur": "30px", "spread": "-12px", "color": "#6e5ac82e"}, "shadow", "기본 카드"),
            "button": tok({"offsetX": "0px", "offsetY": "8px", "blur": "20px", "spread": "-8px", "color": "#6d59d699"}, "shadow", "주요 버튼"),
            "hero": tok({"offsetX": "0px", "offsetY": "18px", "blur": "40px", "spread": "-18px", "color": "#6d59d699"}, "shadow", "학생 홈 상단 배너"),
        },
        "layout": {
            "contentMaxWidth": tok("1152px", "dimension", "본문 최대 폭"),
            "gutterMobile": tok("16px", "dimension"),
            "gutterDesktop": tok("24px", "dimension"),
            "cardPaddingMobile": tok("20px", "dimension"),
            "cardPaddingDesktop": tok("24px", "dimension"),
            "sectionGap": tok("20px", "dimension", "카드 사이 간격"),
            "breakpointTablet": tok("768px", "dimension", "이 폭부터 상단 메뉴, 미만은 하단 탭"),
            "breakpointDesktop": tok("1024px", "dimension", "이 폭부터 2단 배치"),
        },
    }
    return tokens


def token_sheet(tokens: dict, css: str) -> str:
    """토큰을 한 장에 보여 주는 HTML (Figma 참고용 이미지로 찍음)"""
    swatches = "".join(
        f'<div class="group"><h3>{g}</h3><div class="row">'
        + "".join(
            f'<div class="sw"><span style="background:{v["$value"]}"></span><b>{g}-{s}</b><i>{v["$value"]}</i></div>'
            for s, v in shades.items()
        )
        + "</div></div>"
        for g, shades in tokens["color"].items()
    )
    emotions = "".join(
        f'<div class="sw"><span style="background:{v["color"]["$value"]}"></span><b>{v["color"]["$description"]}</b><i>{v["color"]["$value"]}</i></div>'
        for v in tokens["emotion"].values()
    )
    statuses = "".join(
        f'<span class="chip" style="background:{v["background"]["$value"]};color:{v["text"]["$value"]}">{v["$description"].split(" · ")[0]}</span>'
        for v in tokens["status"].values()
    )
    types = "".join(
        f'<div class="type"><i>{name} · {v["$value"]["fontSize"]}/{v["$value"]["lineHeight"]}</i>'
        f'<p style="font-size:{v["$value"]["fontSize"]};line-height:{v["$value"]["lineHeight"]};font-weight:{800 if int(v["$value"]["fontSize"][:-2]) >= 24 else 600}">매일의 마음을 쓰담쓰담 · {v["$description"]}</p></div>'
        for name, v in tokens["typography"].items()
    )
    radii = "".join(
        f'<div class="rad"><span style="border-radius:{v["$value"]}"></span><i>{k} · {v["$value"]}</i></div>'
        for k, v in tokens["radius"].items()
    )
    shadows = "".join(
        f'<div class="shd" style="box-shadow:{v["$value"]["offsetX"]} {v["$value"]["offsetY"]} {v["$value"]["blur"]} {v["$value"]["spread"]} {v["$value"]["color"]}">{k}<br><i>{v["$description"]}</i></div>'
        for k, v in tokens["shadow"].items()
    )
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>쓰담 디자인 토큰</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
body{{margin:0;padding:48px;background:#fbf7f1;color:#3a3550;font-family:"Pretendard Variable",Pretendard,sans-serif;word-break:keep-all}}
h1{{font-size:32px;margin:0 0 4px}} h2{{font-size:20px;margin:40px 0 16px}} h3{{font-size:13px;margin:0 0 8px;color:#6f6a85}}
.note{{color:#6f6a85;font-size:14px;margin:0}}
.group{{margin-bottom:20px}} .row{{display:flex;flex-wrap:wrap;gap:12px}}
.sw{{width:120px;font-size:12px}} .sw span{{display:block;height:56px;border-radius:16px;border:1px solid #0000000f;margin-bottom:6px}}
.sw b{{display:block;font-weight:600}} .sw i,.type i,.rad i,.shd i{{font-style:normal;color:#6f6a85;font-size:12px}}
.chip{{display:inline-block;border-radius:9999px;padding:6px 12px;font-size:12px;font-weight:600;margin:0 8px 8px 0}}
.type{{display:grid;grid-template-columns:220px 1fr;align-items:baseline;gap:16px;padding:8px 0;border-bottom:1px solid #00000010}} .type p{{margin:0}}
.flex{{display:flex;gap:32px;flex-wrap:wrap;align-items:center}}
.rad span{{display:block;width:96px;height:64px;background:#ebe6ff;border:2px solid #9f8ef5;margin-bottom:6px}}
.shd{{width:200px;height:96px;background:#fff;border-radius:24px;padding:20px;box-sizing:border-box;font-weight:600}}
</style></head><body>
<h1>쓰담 디자인 토큰</h1><p class="note">tokens.json 과 같은 값입니다. 글꼴: Pretendard · 모든 색은 시연용 웹 프로토타입에서 추출</p>
<h2>색상 팔레트</h2>{swatches}
<h2>감정 색</h2><div class="row">{emotions}</div>
<h2>진행 상태 칩</h2><div>{statuses}</div>
<h2>글자 크기</h2>{types}
<h2>모서리 · 그림자</h2><div class="flex">{radii}</div><div class="flex" style="margin-top:32px">{shadows}</div>
</body></html>"""


# ── 실행 ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="http://localhost:8010", help="내보내기 전용 쓰담 서버 주소")
    parser.add_argument("--out", default=str(ROOT.parent / "figma-export"), help="결과 폴더")
    args = parser.parse_args()

    out = Path(args.out).resolve()
    for sub in ("screens", "html", "tokens"):
        shutil.rmtree(out / sub, ignore_errors=True)
        (out / sub).mkdir(parents=True)
    css = (ROOT / "app/static/app.css").read_text(encoding="utf-8")
    source_css = (ROOT / "app/static/src/input.css").read_text(encoding="utf-8")

    # 1) 시연 흐름 순서대로 상태를 쌓으며 화면 저장
    manifest = []
    for name, title, path, actions in SCREENS:
        for action, form in actions:
            request(args.base, action, form)
        file = out / "html" / f"{name}.html"
        file.write_text(snapshot(request(args.base, path), css), encoding="utf-8")
        manifest.append({"name": name, "title": title, "path": path, "html": f"html/{file.name}"})
        print(f"HTML  {file.name}")

    # 2) 토큰
    tokens = build_tokens(css, source_css)
    (out / "tokens" / "tokens.json").write_text(json.dumps(tokens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sheet = out / "tokens" / "token-sheet.html"
    sheet.write_text(token_sheet(tokens, css), encoding="utf-8")

    # 3) 화면 캡처 (병렬)
    jobs = [(out / m["html"], w, out / "screens" / f"{m['name']}--{kind}.png", m) for m in manifest for kind, w in WIDTHS.items()]
    jobs.append((sheet, 1440, out / "tokens" / "token-sheet.png", None))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda j: (j, capture(j[0], j[1], j[2])), jobs))
    for (src, width, _, m), files in results:
        if m is not None:
            m.setdefault("screens", []).extend(f"screens/{f.name}" for f in files)
        for f in files:
            with Image.open(f) as im:
                print(f"PNG   {f.relative_to(out)}  {im.width}x{im.height}")

    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"완료 → {out}")


if __name__ == "__main__":
    main()
