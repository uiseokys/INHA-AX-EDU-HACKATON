"""쓰담 FastAPI 앱: 라우트와 화면 렌더링

실행: uvicorn app.main:app --reload
화면은 Jinja 템플릿(app/templates)으로 서버에서 그리고, 버튼은 모두 폼 전송(POST → 리다이렉트)으로 동작합니다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from . import charts, data, store
from .analysis import analyze, build_series, fmt, summarize
from .data import ME_ID
from .dates import add_days, day_label, full_label, relative_label, today_key, weekday
from .models import EMOTIONS, INTENSITY_LABELS, STATUS, STATUS_ORDER
from .privacy import teacher_view

BASE = Path(__file__).resolve().parent

app = FastAPI(title="쓰담 (SSUDAM)", description="시연용 프로토타입 · 합성 데이터")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

# ── 템플릿 도우미 ─────────────────────────────────────────────────────────────

ICONS: dict[str, list] = json.loads((BASE / "icons.json").read_text(encoding="utf-8"))


def icon(name: str, cls: str = "size-5") -> Markup:
    """Lucide 아이콘(ISC 라이선스)을 인라인 SVG로 출력"""
    inner = "".join(
        f"<{tag} " + " ".join(f'{k}="{escape(v)}"' for k, v in attrs.items()) + "/>" for tag, attrs in ICONS[name]
    )
    return Markup(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="{escape(cls)}" aria-hidden="true">{inner}</svg>'
    )


def highlight(text: str, words: list[str]) -> Markup:
    """메모에서 근거가 된 키워드를 강조"""
    out, rest = Markup(""), text
    ordered = sorted(words, key=len, reverse=True)
    while rest:
        hits = [(rest.find(w), w) for w in ordered if w in rest]
        if not hits:
            out += escape(rest)
            break
        idx, word = min(hits, key=lambda h: h[0])
        out += escape(rest[:idx]) + Markup('<mark class="rounded bg-butter-200 px-0.5 text-ink">') + escape(word) + Markup("</mark>")
        rest = rest[idx + len(word) :]
    return out


BTN = {
    "primary": "inline-flex items-center justify-center gap-2 rounded-2xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-[0_8px_20px_-8px_rgba(109,89,214,0.6)] transition hover:-translate-y-0.5 hover:bg-brand-600 active:translate-y-0",
    "soft": "inline-flex items-center justify-center gap-2 rounded-2xl bg-brand-50 px-4 py-2.5 text-sm font-semibold text-brand-700 transition hover:bg-brand-100",
    "ghost": "inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-ink-soft transition hover:bg-stone-100 hover:text-ink",
    "outline": "inline-flex items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-brand-300 hover:text-brand-700",
}
CARD = "rounded-3xl border border-white/80 bg-white/90 p-5 shadow-[0_10px_30px_-12px_rgba(110,90,200,0.18)] sm:p-6"
CHIP = "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
FIELD = "w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-ink placeholder:text-stone-400 transition focus:border-brand-300 focus:outline-none focus:ring-4 focus:ring-brand-100"

NAV = {
    "student": {
        "label": "학생",
        "tone": "bg-peach-100 text-peach-500",
        "switch": {"href": "/teacher", "label": "상담교사 화면"},
        "items": [
            {"href": "/student", "label": "홈", "icon": "house"},
            {"href": "/student/insights", "label": "마음 분석", "icon": "chart-line"},
            {"href": "/student/support", "label": "도움 요청", "icon": "heart-handshake"},
        ],
    },
    "teacher": {
        "label": "상담교사",
        "tone": "bg-mint-100 text-mint-700",
        "switch": {"href": "/student", "label": "학생 화면"},
        "items": [
            {"href": "/teacher", "label": "요청 현황", "icon": "clipboard-list"},
            {"href": "/teacher/agencies", "label": "지원기관", "icon": "building-2"},
        ],
    },
}

TOASTS = {
    "referred": "연결 요청을 기록했어요 (시연용)",
    "memo": "상담 메모를 저장했어요",
    "reset": "시연 데이터를 처음 상태로 되돌렸어요",
}

templates.env.globals.update(
    icon=icon,
    E=EMOTIONS,
    INTENSITY=INTENSITY_LABELS,
    STATUS=STATUS,
    STATUS_ORDER=STATUS_ORDER,
    SCHOOL=data.SCHOOL,
    btn=BTN,
    card=CARD,
    chip=CHIP,
    field=FIELD,
    rel=relative_label,
    topic_label=data.topic_label,
    agency_type_label=data.agency_type_label,
    get_agency=data.get_agency,
)
templates.env.filters.update(
    day_label=day_label, full_label=full_label, weekday=weekday, num=fmt, highlight=highlight, topic_label=data.topic_label
)


def render(request: Request, name: str, mode: str | None = None, status_code: int = 200, **ctx):
    path = request.url.path
    nav = None
    if mode in NAV:
        home = NAV[mode]["items"][0]["href"]

        def is_active(href: str) -> bool:
            if href == home:
                return path == home or path.startswith("/teacher/students")
            return path.startswith(href)

        nav = {**NAV[mode], "items": [{**item, "active": is_active(item["href"])} for item in NAV[mode]["items"]]}
    css = BASE / "static" / "app.css"
    ctx.update(
        mode=mode,
        nav=nav,
        path=path,
        today=today_key(),
        # 같은 화면에서 폼을 보낸 뒤 돌아온 경우에는 등장 애니메이션을 생략
        animate=urlparse(request.headers.get("referer", "")).path != path,
        toast=TOASTS.get(request.query_params.get("msg", "")),
        css_version=int(css.stat().st_mtime) if css.exists() else 0,
    )
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def back(url: str) -> RedirectResponse:
    """폼 처리 후 화면으로 돌아가기 (POST → 303 → GET)"""
    return RedirectResponse(url, status_code=303)


# ── 랜딩 ─────────────────────────────────────────────────────────────────────


@app.get("/")
def landing(request: Request):
    return render(request, "landing.html")


@app.post("/reset")
def reset(next: Annotated[str, Form()] = "/"):
    store.reset()
    target = next if next.startswith("/") and not next.startswith("//") else "/"
    return back(f"{target}?msg=reset")


# ── 학생: 홈 ─────────────────────────────────────────────────────────────────

MOMENTS = ["수업", "친구", "급식", "동아리", "체육", "시험·과제", "쉬는 시간", "방과 후", "가족", "혼자만의 시간"]


@app.get("/student")
def student_home(request: Request, edit: str = ""):
    today, state = today_key(), store.load()
    logs = data.logs_for(ME_ID, state, today)
    by_date = {log.date: log for log in logs}
    recorded_today = today in by_date

    # 연속 기록 일수 (오늘 기록 전이면 어제까지 이어진 일수)
    streak, day = 0, today if recorded_today else add_days(today, -1)
    while day in by_date:
        streak, day = streak + 1, add_days(day, -1)

    todos = [t for t in state["todos"] if t["date"] == today or not t["done"]]  # 오늘 항목 + 끝내지 못한 항목
    done_count = sum(1 for t in todos if t["done"])
    earlier = [r for r in state["reflections"] if r["date"] < today and r["tomorrow_goal"]]
    my_log = next((raw for raw in state["my_logs"] if raw["date"] == today), None)

    return render(
        request,
        "student_home.html",
        mode="student",
        me=data.get_student(ME_ID),
        streak=streak,
        recorded_today=recorded_today,
        week=[{"date": d, "log": by_date.get(d)} for d in (add_days(today, i - 6) for i in range(7))],
        todos=todos,
        done_count=done_count,
        pct=round(done_count / len(todos) * 100) if todos else 0,
        prev_goal=max(earlier, key=lambda r: r["date"]) if earlier else None,
        saved=by_date.get(today) if my_log else None,
        skipped=today in state["skipped"],
        edit=edit,
        chart=charts.mood_chart(build_series(logs, today), today),
        reflection=next((r for r in state["reflections"] if r["date"] == today), None),
        done_todos=[t for t in state["todos"] if t["done"] and t["date"] == today],
        moments=MOMENTS,
    )


@app.post("/student/todos")
def add_todo(text: Annotated[str, Form()] = "", goal: Annotated[str, Form()] = ""):
    text = text.strip()[:80]
    if text:
        with store.editing() as state:
            state["todos"].append(
                {"id": store.new_id("todo"), "text": text, "done": False, "date": today_key(), "kind": "goal" if goal else "todo"}
            )
    return back("/student")


@app.post("/student/todos/{todo_id}/toggle")
def toggle_todo(todo_id: str):
    with store.editing() as state:
        for todo in state["todos"]:
            if todo["id"] == todo_id:
                todo.update(done=not todo["done"], date=today_key())
    return back("/student")


@app.post("/student/todos/{todo_id}/delete")
def delete_todo(todo_id: str):
    with store.editing() as state:
        state["todos"] = [t for t in state["todos"] if t["id"] != todo_id]
    return back("/student")


@app.post("/student/goal-result")
def goal_result(date: Annotated[str, Form()], result: Annotated[str, Form()]):
    """지난 회고에서 남긴 목표를 '해냈어요' 또는 '오늘 할 일에 추가'로 처리"""
    if result not in ("done", "carried"):
        raise HTTPException(400, "알 수 없는 처리 방식입니다.")
    with store.editing() as state:
        for reflection in state["reflections"]:
            if reflection["date"] == date and not reflection.get("goal_result"):
                reflection["goal_result"] = result
                if result == "carried":
                    state["todos"].append(
                        {"id": store.new_id("todo"), "text": reflection["tomorrow_goal"], "done": False, "date": today_key(), "kind": "goal"}
                    )
    return back("/student")


@app.post("/student/checkin")
def checkin(
    emotion: Annotated[str, Form()],
    intensity: Annotated[int, Form()] = 3,
    note: Annotated[str, Form()] = "",
    shared: Annotated[str, Form()] = "",
):
    if emotion not in EMOTIONS:
        raise HTTPException(400, "알 수 없는 감정입니다.")
    today = today_key()
    log_id = f"{ME_ID}:{today}"
    with store.editing() as state:
        state["share_overrides"].pop(log_id, None)
        state["skipped"] = [d for d in state["skipped"] if d != today]
        state["my_logs"] = [raw for raw in state["my_logs"] if raw["date"] != today] + [
            {
                "id": log_id,
                "student_id": ME_ID,
                "date": today,
                "emotion": emotion,
                "intensity": min(5, max(1, intensity)),
                "note": note.strip()[:200] or None,
                "shared": bool(shared),
            }
        ]
    return back("/student")


@app.post("/student/checkin/skip")
def skip_checkin():
    today = today_key()
    with store.editing() as state:
        if today not in state["skipped"]:
            state["skipped"].append(today)
    return back("/student")


@app.post("/student/reflection")
def save_reflection(moments: Annotated[list[str], Form()] = [], tomorrow_goal: Annotated[str, Form()] = ""):
    today = today_key()
    with store.editing() as state:
        state["reflections"] = [r for r in state["reflections"] if r["date"] != today] + [
            {
                "date": today,
                "moments": [m for m in moments if m in MOMENTS],
                "tomorrow_goal": tomorrow_goal.strip()[:60],
                "goal_result": None,
            }
        ]
    return back("/student")


# ── 학생: 마음 분석 ───────────────────────────────────────────────────────────


@app.get("/student/insights")
def student_insights(request: Request):
    today, state = today_key(), store.load()
    logs = data.logs_for(ME_ID, state, today)
    insight = analyze(logs, today)
    return render(
        request,
        "student_insights.html",
        mode="student",
        insight=insight,
        summary=summarize(insight, "student"),
        chart=charts.mood_chart(insight.series, today),
        donut=charts.donut(insight.ratio),
        recent=sorted(logs, key=lambda log: log.date, reverse=True)[:6],
    )


@app.post("/student/logs/share")
def share_log(log_id: Annotated[str, Form()], shared: Annotated[str, Form()] = ""):
    """기록 한 건의 공유 여부를 학생이 직접 바꿈"""
    with store.editing() as state:
        state["share_overrides"][log_id] = shared == "1"
    return back("/student/insights")


# ── 학생: 도움 요청 ───────────────────────────────────────────────────────────

SUPPORT_TOPICS = ["친구 관계", "학업", "가족", "진로", "몸과 마음", "말하기 어려워요"]
PREFERRED = ["직접 만나서 이야기하기", "쪽지·메신저로 먼저", "선생님이 먼저 불러주세요"]
SUPPORT_STEPS = ["요청 보냄", "선생님 확인", "상담 진행", "필요하면 기관 연결"]
STEP_OF = {"none": -1, "requested": 0, "review": 1, "in_progress": 2, "referred": 3, "closed": 3}
STATUS_TEXT = {
    "none": "진행 중인 요청이 없어요.",
    "requested": "요청이 전달됐어요. 상담 선생님이 확인하면 알려 드릴게요.",
    "review": "상담 선생님이 내용을 살펴보고 있어요.",
    "in_progress": "상담 선생님과의 상담이 진행되고 있어요.",
    "referred": "선생님이 도움이 될 전문기관과 연결하고 있어요.",
    "closed": "지원이 마무리됐어요. 언제든 다시 요청할 수 있어요.",
}


@app.get("/student/support")
def student_support(request: Request, sent: str = ""):
    today, state = today_key(), store.load()
    status = data.status_for(data.get_student(ME_ID), state)
    return render(
        request,
        "student_support.html",
        mode="student",
        consent=state["consent"],
        requests=data.requests_for(ME_ID, state, today),
        step=STEP_OF[status],
        status_text=STATUS_TEXT[status],
        steps=SUPPORT_STEPS,
        topics=SUPPORT_TOPICS,
        preferred=PREFERRED,
        just_sent=bool(sent),
    )


@app.post("/student/support")
def request_support(
    topic: Annotated[str, Form()] = "",
    message: Annotated[str, Form()] = "",
    preferred: Annotated[str, Form()] = PREFERRED[0],
):
    """상담 지원 요청. 감정 기록이 없어도, 모든 항목을 비워도 보낼 수 있습니다."""
    with store.editing() as state:
        state["requests"].append(
            {
                "id": store.new_id("REQ"),
                "student_id": ME_ID,
                "date": today_key(),
                "topic": topic if topic in SUPPORT_TOPICS else "주제를 고르지 않음",
                "message": message.strip()[:500],
                "preferred": preferred if preferred in PREFERRED else PREFERRED[0],
            }
        )
        state["case_status"][ME_ID] = "requested"
    return back("/student/support?sent=1")


@app.post("/student/consent")
def set_consent(key: Annotated[str, Form()], on: Annotated[str, Form()] = ""):
    if key not in ("trend", "all_notes"):
        raise HTTPException(400, "알 수 없는 공유 항목입니다.")
    with store.editing() as state:
        state["consent"][key] = bool(on)
    return back("/student/support")


# ── 상담교사 ─────────────────────────────────────────────────────────────────


def teacher_bundle(student: dict, state: dict, today: str) -> dict:
    """교사 화면에 필요한 한 학생의 정보. 기록은 공유 동의 범위를 거친 것만 사용합니다."""
    view = teacher_view(data.logs_for(student["id"], state, today), data.consent_for(student, state))
    return {
        "student": student,
        "status": data.status_for(student, state),
        "consent": data.consent_for(student, state),
        "view": view,
        "insight": analyze(view.logs, today),
        "requests": data.requests_for(student["id"], state, today),
        "referrals": data.referrals_for(student["id"], state, today),
    }


@app.get("/teacher")
def teacher_home(request: Request, status: str = "all"):
    today, state = today_key(), store.load()
    rows = [teacher_bundle(s, state, today) for s in data.STUDENTS]
    for row in rows:
        row["request"] = row["requests"][0] if row["requests"] else None
        row["spark"] = charts.sparkline(row["insight"].series) if row["view"].trend_visible else None
    rows.sort(key=lambda r: r["request"]["date"] if r["request"] else "", reverse=True)
    rows.sort(key=lambda r: STATUS_ORDER.index(r["status"]))
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUS_ORDER}
    selected = status if status in STATUS else "all"
    return render(
        request,
        "teacher_home.html",
        mode="teacher",
        rows=[r for r in rows if selected == "all" or r["status"] == selected],
        total=len(rows),
        counts=counts,
        selected=selected,
        tiles=["requested", "review", "in_progress", "referred"],
    )


@app.get("/teacher/students/{student_id}")
def teacher_student(request: Request, student_id: str):
    today, state = today_key(), store.load()
    student = data.get_student(student_id)
    if not student:
        return render(request, "teacher_student.html", mode="teacher", status_code=404, b=None)
    b = teacher_bundle(student, state, today)
    timeline = (
        [{"date": r["date"], "text": f"학생이 상담 지원을 요청함 ({r['topic']})"} for r in b["requests"]]
        + [{"date": r["date"], "text": f"{(data.get_agency(r['agency_id']) or {}).get('name', '지원기관')} 연결 요청"} for r in b["referrals"]]
        + state["events"].get(student_id, [])
    )
    return render(
        request,
        "teacher_student.html",
        mode="teacher",
        b=b,
        summary=summarize(b["insight"], "teacher"),
        chart=charts.mood_chart(b["insight"].series, today),
        records=sorted(b["view"].logs, key=lambda log: log.date, reverse=True),
        timeline=sorted(timeline, key=lambda e: e["date"], reverse=True),
        memo=state["memos"].get(student_id, ""),
    )


def _set_status(state: dict, student_id: str, status: str) -> None:
    state["case_status"][student_id] = status
    state["events"].setdefault(student_id, []).append(
        {"date": today_key(), "text": f"진행 상태를 ‘{STATUS[status]['label']}’(으)로 변경"}
    )


@app.post("/teacher/students/{student_id}/status")
def set_status(student_id: str, status: Annotated[str, Form()]):
    student = data.get_student(student_id)
    if not student or status not in STATUS:
        raise HTTPException(400, "학생 또는 상태 값이 올바르지 않습니다.")
    with store.editing() as state:
        if data.status_for(student, state) != status:
            _set_status(state, student_id, status)
    return back(f"/teacher/students/{student_id}")


@app.post("/teacher/students/{student_id}/memo")
def save_memo(student_id: str, memo: Annotated[str, Form()] = ""):
    if not data.get_student(student_id):
        raise HTTPException(404, "학생 정보를 찾을 수 없습니다.")
    with store.editing() as state:
        state["memos"][student_id] = memo[:2000]
    return back(f"/teacher/students/{student_id}?msg=memo")


# ── 지원기관 추천 ─────────────────────────────────────────────────────────────

# 학생이 요청할 때 고른 주제 → 분석 주제 id
REQUEST_TOPIC = {"친구 관계": "peer", "학업": "study", "가족": "family", "진로": "career", "몸과 마음": "health"}
TYPE_TONE = {
    "wee-class": "bg-peach-100 text-peach-500",
    "wee-center": "bg-brand-100 text-brand-700",
    "youth-center": "bg-mint-100 text-mint-700",
    "etc": "bg-sky-100 text-sky-800",
}


def _agency_url(**params: str) -> str:
    query = {k: v for k, v in params.items() if v and v != "all"}
    return "/teacher/agencies" + (f"?{urlencode(query)}" if query else "")


@app.get("/teacher/agencies")
def agency_finder(request: Request, student: str = "", type: str = "all", region: str = "all", refer: str = ""):
    today, state = today_key(), store.load()
    selected = data.get_student(student)

    # 학생이 공유한 기록과 요청 주제에서 추천 근거가 되는 주제를 모읍니다.
    student_topics: list[str] = []
    linked: set[str] = set()
    if selected:
        b = teacher_bundle(selected, state, today)
        student_topics = [t.id for t in b["insight"].topics[:2]]
        for r in b["requests"]:
            topic = REQUEST_TOPIC.get(r["topic"])
            if topic and topic not in student_topics:
                student_topics.append(topic)
        linked = {r["agency_id"] for r in b["referrals"]}

    current = {"student": selected["id"] if selected else "", "type": type, "region": region}
    return render(
        request,
        "agencies.html",
        mode="teacher",
        selected=selected,
        students=[{"s": s, "status": data.status_for(s, state)} for s in data.STUDENTS],
        student_topics=student_topics,
        linked=linked,
        results=data.match_agencies(data.AGENCIES, type, region, student_topics),
        types=[{"id": "all", "label": "전체"}] + data.AGENCY_TYPES,
        type_desc=next((t["desc"] for t in data.AGENCY_TYPES if t["id"] == type), None),
        regions=data.REGIONS,
        current=current,
        target=data.get_agency(refer),
        type_tone=TYPE_TONE,
        url=lambda **kw: _agency_url(**{**current, **kw}),
    )


@app.post("/teacher/agencies/refer")
def refer_agency(
    student_id: Annotated[str, Form()] = "",
    agency_id: Annotated[str, Form()] = "",
    note: Annotated[str, Form()] = "",
    type: Annotated[str, Form()] = "all",
    region: Annotated[str, Form()] = "all",
):
    """지원기관 연결 요청을 기록 (시연용: 실제 기관으로 전송되지 않음)"""
    student, agency = data.get_student(student_id), data.get_agency(agency_id)
    if not student or not agency:
        return back(_agency_url(student=student_id, type=type, region=region, refer=agency_id))
    today = today_key()
    with store.editing() as state:
        if agency_id not in {r["agency_id"] for r in data.referrals_for(student_id, state, today)}:
            state["referrals"].append(
                {"id": store.new_id("REF"), "student_id": student_id, "agency_id": agency_id, "date": today, "note": note.strip()[:300]}
            )
            if data.status_for(student, state) != "referred":
                _set_status(state, student_id, "referred")
    return back(_agency_url(student=student_id, type=type, region=region, msg="referred"))
