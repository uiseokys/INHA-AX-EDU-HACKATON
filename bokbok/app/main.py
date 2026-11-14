"""복복복 FastAPI 앱: 라우트와 화면 렌더링

실행: uvicorn app.main:app --reload
화면은 Jinja 템플릿(app/templates)으로 서버에서 그리고, 버튼은 대부분 폼 전송(POST → 리다이렉트)으로 동작합니다.
챗봇만 자바스크립트로 새로고침 없이 대화하고, 자바스크립트가 꺼져 있으면 폼 전송으로 동작합니다.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from . import chatbot, charts, data, ledger, points, store
from . import profanity
from .analysis import describe_change, fmt, risk_hits, student_report, teacher_report
from .assessments import compare_results
from .attendance import attendance_summary
from .data import ME_ID
from .dates import add_days, day_label, full_label, month_days, relative_label, today_key, weekday
from .models import BOT_NAME, EMOTIONS, FOLLOWUP, INTENSITY_LABELS, LEVEL_ORDER, LEVELS, SERVICE_NAME

BASE = Path(__file__).resolve().parent

app = FastAPI(
    title=f"{SERVICE_NAME} 학생 마음 돌봄 플랫폼",
    description="시연용 프로토타입 · 합성 데이터",
    # 공개 테스트 모드에서는 API 문서 화면을 열지 않음
    docs_url=None if store.multi_mode() else "/docs",
    redoc_url=None,
    openapi_url=None if store.multi_mode() else "/openapi.json",
)


@app.middleware("http")
async def sandbox(request: Request, call_next):
    """공개 테스트 모드: 브라우저마다 따로 체험 공간을 씀 (쿠키로 구분)"""
    if not store.multi_mode():
        return await call_next(request)
    sid = request.cookies.get(store.SESSION_COOKIE)
    fresh = not store.valid_sid(sid)
    if fresh:
        sid = store.new_sid()
    token = store.use_session(sid)
    try:
        response = await call_next(request)
    finally:
        store._session.reset(token)
    if fresh:
        response.set_cookie(store.SESSION_COOKIE, sid, max_age=store.SESSION_MAX_AGE, httponly=True, samesite="lax",
                            secure=request.url.scheme == "https")
    return response

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


def keep(state: dict, kind: str, student_id: str | None, ref: str | None, payload: dict) -> None:
    """보존 기록(app/ledger.py)에 원본을 한 줄 덧붙임. 서버 시각과 해시는 ledger 가 붙입니다.

    마지막 순번·해시를 상태에도 적어 두어, 보존 기록의 뒤쪽이 잘려 나갔는지 확인할 수 있게 합니다.
    """
    e = ledger.append(kind, student_id, ref, payload)
    state["ledger_head"] = {"seq": e["seq"], "hash": e["hash"]}


ALERT_LEVELS = {"care": 1, "issue": 2, "urgent": 3}  # 알림 단계: 살펴보기 < 확인 필요 < 긴급
ALERT_LEVEL_CHIP = {  # 선생님 화면에 보이는 단계 표시
    "urgent": {"label": "긴급", "chip": "bg-rose-100 text-rose-800"},
    "issue": {"label": "확인 필요", "chip": "bg-amber-100 text-amber-800"},
    "care": {"label": "살펴보기", "chip": "bg-leaf-100 text-leaf-700"},
}

BTN = {
    "primary": "inline-flex items-center justify-center gap-2 rounded-2xl bg-leaf-600 px-5 py-3 text-sm font-bold text-white shadow-[0_8px_20px_-10px_rgba(47,107,63,0.7)] transition hover:-translate-y-0.5 hover:bg-leaf-700 active:translate-y-0 disabled:translate-y-0 disabled:bg-stone-200 disabled:text-stone-400 disabled:shadow-none",
    "dark": "inline-flex items-center justify-center gap-2 rounded-2xl bg-ink px-5 py-3 text-sm font-bold text-white transition hover:bg-black",
    "soft": "inline-flex items-center justify-center gap-2 rounded-2xl bg-leaf-50 px-4 py-2.5 text-sm font-semibold text-leaf-700 transition hover:bg-leaf-100",
    "ghost": "inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-ink-soft transition hover:bg-stone-100 hover:text-ink",
    "outline": "inline-flex items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-leaf-300 hover:text-leaf-700",
    "danger": "inline-flex items-center justify-center gap-2 rounded-2xl bg-rose-50 px-4 py-2.5 text-sm font-semibold text-rose-700 transition hover:bg-rose-100",
}
CARD = "rounded-3xl border border-white bg-white p-5 shadow-[0_8px_28px_-14px_rgba(46,84,56,0.22)] sm:p-6"
CHIP = "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
FIELD = "w-full rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-ink placeholder:text-stone-400 transition focus:border-leaf-400 focus:outline-none focus:ring-4 focus:ring-leaf-100"

NAV = {
    "student": {
        "label": "학생",
        "tone": "bg-leaf-100 text-leaf-700",
        "switch": {"href": "/teacher", "label": "선생님 화면"},
        "items": [
            {"href": "/student", "label": "홈", "icon": "house"},
            {"href": "/student/report", "label": "리포트", "icon": "chart-column"},
            {"href": "/student/chat", "label": BOT_NAME, "icon": "message-circle-more"},
            {"href": "/student/counsel", "label": "상담", "icon": "hand-heart"},  # 어느 화면에서든 상담 신청으로
            {"href": "/student/shop", "label": "상점", "icon": "store"},
            {"href": "/student/help", "label": "도움", "icon": "life-buoy"},
        ],
    },
    "teacher": {
        "label": "선생님",
        "tone": "bg-sky-100 text-sky-800",
        "switch": {"href": "/student", "label": "학생 화면"},
        "items": [
            {"href": "/teacher", "label": "정서 현황", "icon": "users"},
            {"href": "/teacher/alerts", "label": "알림", "icon": "bell"},
            {"href": "/teacher/counsel", "label": "상담 일정", "icon": "calendar-clock"},
            {"href": "/teacher/shares", "label": "공유 메모", "icon": "message-square-text"},
            {"href": "/teacher/shop", "label": "상점 관리", "icon": "store"},
            {"href": "/teacher/ledger", "label": "기록 보존", "icon": "shield-check"},
        ],
    },
}

TOASTS = {
    "reset": "시연 데이터를 처음 상태로 되돌렸어요",
    "profile": "기본 정보를 저장했어요",
    "promise": "약속을 저장했어요",
    "need_basic": "‘감정을 기록할 때’의 세 가지를 모두 눌러 주세요",
    "booked": "상담을 신청했어요. 선생님이 확인하면 알려 드릴게요",
    "booking_cancelled": "상담 신청을 취소했어요",
    "conversation_sent": "대화 요청을 보냈어요",
    "conversation_cancelled": "대화 요청을 취소했어요",
    "conversation_confirmed": "제안받은 시간으로 상담이 확정됐어요",
    "conversation_retry": "선생님께 다른 시간을 부탁했어요",
    "conversation_taken": "학생이나 선생님에게 일정이 있는 시간이에요. 다른 시간을 골라 주세요",
    "ordered": "교환을 신청했어요. 선생님이 승인하면 사용할 수 있어요",
    "order_cancelled": "교환 신청을 취소했어요",
    "not_enough": "포인트가 부족하거나 더 교환할 수 없는 상품이에요",
    "slot_taken": "방금 다른 친구가 신청한 시간이에요. 다른 시간을 골라 주세요",
    "followup": "사후 관리 내용을 저장했어요",
    "alert_task_saved": "다음 행동을 저장했어요",
    "alert_task_done": "조치를 완료했어요",
    "support_shared": "지원 메모를 공유했어요",
    "slot_added": "상담 가능 시간을 추가했어요",
    "item_saved": "상품을 저장했어요",
    "item_deleted": "상품을 삭제했어요",
    "bad_image": "이미지는 PNG·JPG·WEBP·GIF 2MB 이하만 올릴 수 있어요",
}

templates.env.globals.update(
    icon=icon,
    E=EMOTIONS,
    LEVELS=LEVELS,
    LEVEL_ORDER=LEVEL_ORDER,
    ALERT_LEVEL_CHIP=ALERT_LEVEL_CHIP,
    RESPONSE_GUIDE=data.SIGNALS["response_guide"],
    FOLLOWUP=FOLLOWUP,
    SERVICE=SERVICE_NAME,
    BOT=BOT_NAME,
    SCHOOL=data.SCHOOL,
    CLASS_NAME=data.CLASS_NAME,
    TEACHERS=data.TEACHERS,
    CONTACTS=data.CONTACTS,
    btn=BTN,
    card=CARD,
    chip=CHIP,
    field=FIELD,
    rel=relative_label,
    get_student=data.get_student,
)
templates.env.filters.update(day_label=day_label, full_label=full_label, weekday=weekday, num=fmt)


def unread_alerts(state: dict) -> list[dict]:
    return sorted((a for a in state["alerts"] if not a["read"]), key=lambda a: (a["date"], a["time"]), reverse=True)


def render(request: Request, name: str, mode: str | None = None, status_code: int = 200, state: dict | None = None, **ctx):
    path = request.url.path
    nav = None
    if mode in NAV:
        home = NAV[mode]["items"][0]["href"]

        def is_active(href: str) -> bool:
            if href == home:
                return path == home or (mode == "teacher" and path.startswith("/teacher/students"))
            return path.startswith(href)

        nav = {**NAV[mode], "items": [{**item, "active": is_active(item["href"])} for item in NAV[mode]["items"]]}
    state = state or store.load()
    today = today_key()
    if mode == "student":
        ctx.setdefault("my_points", points.balance(_ledger(ME_ID, state, today)))
    if mode == "teacher":
        ctx.setdefault("pinned", unread_alerts(state))
    css = BASE / "static" / "app.css"
    js = BASE / "static" / "app.js"
    ctx.update(
        MULTI=store.multi_mode(),
        mode=mode,
        nav=nav,
        path=path,
        today=today,
        animate=urlparse(request.headers.get("referer", "")).path != path,
        toast=TOASTS.get(request.query_params.get("msg", "")),
        css_version=int(css.stat().st_mtime) if css.exists() else 0,
        js_version=int(js.stat().st_mtime) if js.exists() else 0,
    )
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def back(url: str) -> RedirectResponse:
    """폼 처리 후 화면으로 돌아가기 (POST → 303 → GET)"""
    return RedirectResponse(url, status_code=303)


def now_time() -> str:
    return datetime.now().strftime("%H:%M")


def items_by_id(state: dict) -> dict[str, dict]:
    return {i["id"]: i for i in state["items"]}


def _ledger(student_id: str, state: dict, today: str) -> list[points.Entry]:
    return points.ledger(
        data.records_for(student_id, state, today),
        [o for o in state["orders"] if o["student_id"] == student_id],
        items_by_id(state),
    )


def add_alert(state: dict, student_id: str, source: str, category: str, summary: str,
              level: str = "issue", note: str | None = None) -> None:
    """교사 알림 남기기 (같은 날 같은 종류는 한 번만). 대화·문장 원문은 담지 않습니다.

    level: care(살펴보기) · issue(확인 필요) · urgent(긴급). note 는 지금 쓰지 않습니다 (대화 내용은 선생님께 전하지 않음).
    같은 날 같은 종류의 알림이 이미 있으면 새로 만들지 않고, 단계가 올라갔을 때만 고칩니다.
    """
    today = today_key()
    for a in state["alerts"]:
        if a["student_id"] == student_id and a["date"] == today and a["source"] == source and a["category"] == category:
            if note:
                a["note"] = note
            if ALERT_LEVELS[level] > ALERT_LEVELS.get(a.get("level", "issue"), 2):
                a.update(level=level, summary=summary, time=now_time(), read=False)
                a.pop("task", None)  # 높아진 단계에 맞춰 다음 행동을 다시 정합니다.
                keep(state, "alert_update", student_id, a["id"], {"source": source, "level": level, "summary": summary})
            return
    alert = {"id": store.new_id("AL"), "student_id": student_id, "date": today, "time": now_time(), "source": source,
             "category": category, "summary": summary, "level": level, "note": note, "read": False}
    state["alerts"].append(alert)
    keep(state, "alert", student_id, alert["id"], {"source": source, "level": level, "summary": summary})


# ── 업로드한 상품 이미지 ───────────────────────────────────────────────────────


@app.get("/uploads/{name}")
def uploaded(name: str):
    """선생님이 올린 상품 이미지 (저장 위치는 실행 중에 정해지므로 고정 마운트 대신 라우트로 제공)"""
    path = store.upload_dir() / name
    if "/" in name or name.startswith(".") or not path.is_file():
        raise HTTPException(404, "이미지를 찾을 수 없습니다.")
    return FileResponse(path)


# ── 랜딩 ─────────────────────────────────────────────────────────────────────


@app.get("/")
def landing(request: Request):
    return render(request, "landing.html")


@app.post("/reset")
def reset(next: Annotated[str, Form()] = "/"):
    store.reset()
    with store.editing() as state:  # 화면의 데이터는 처음으로 돌아가지만, 보존 기록은 지우지 않고 '초기화했다'는 줄만 덧붙임
        keep(state, "reset", None, None, {"what": "화면에 보이는 시연 데이터를 처음 상태로 되돌림"})
    target = next if next.startswith("/") and not next.startswith("//") else "/"
    return back(f"{target}?msg=reset")


# ── 학생: 기본 정보 (기획서 (1)) ──────────────────────────────────────────────

HOME_OPTIONS = ["부모님과 함께 지내요", "한 부모님과 지내요", "조부모님과 지내요", "기숙사·시설에서 지내요", "기타"]
HELPERS = ["담임 선생님", "상담 선생님", "부모님", "형제자매", "친구", "기타"]


@app.get("/student/welcome")
def welcome(request: Request, edit: str = ""):
    state = store.load()
    if not state.get("consent"):
        return back("/student/promise")  # 처음 접속: 기본 정보보다 약속(동의)이 먼저
    return render(request, "student_welcome.html", mode="student" if edit else None, state=state,
                  profile=state["profile"] or {}, me=data.get_student(ME_ID), editing=bool(edit),
                  home_options=HOME_OPTIONS, helpers=HELPERS)


@app.post("/student/welcome")
def save_profile(
    action: Annotated[str, Form()] = "save",
    family: Annotated[str, Form()] = "",
    home: Annotated[str, Form()] = "",
    home_note: Annotated[str, Form()] = "",
    friends: Annotated[str, Form()] = "",
    wish: Annotated[str, Form()] = "",
    satisfaction: Annotated[int, Form()] = 0,
    concern: Annotated[str, Form()] = "",
    helpers: Annotated[list[str], Form()] = [],
):
    with store.editing() as state:
        if action == "skip":
            state["profile_skipped"] = True
            return back("/student")
        state["profile"] = {
            "family": family.strip()[:100],
            "home": (home if home in HOME_OPTIONS else "") + (f" · {home_note.strip()[:100]}" if home_note.strip() else ""),
            "friends": friends.strip()[:100],
            "wish": wish.strip()[:200],
            "satisfaction": min(5, max(0, satisfaction)),
            "concern": concern.strip()[:200],
            "helpers": [h for h in helpers if h in HELPERS],
        }
    return back("/student?msg=profile")


# ── 학생: 약속(동의) ──────────────────────────────────────────────────────────


def chat_allowed(state: dict) -> bool:
    """복복이 대화는 '선생님이 볼 수 없다'와 '힘들어 보이면 신호만 전해진다'를 약속한 학생만 씁니다."""
    return bool((state.get("consent") or {}).get("chat"))


@app.get("/student/promise")
def promise_page(request: Request, locked: str = "", today_emotion: str = ""):
    """내 기록과 대화가 누구에게 어떻게 보이는지 알려 주고 확인받는 화면 (처음 접속할 때, 그리고 언제든 다시 보기)"""
    state = store.load()
    consent = state.get("consent") or {}
    return render(request, "student_promise.html", mode="student" if consent else None, state=state, consent=consent,
                  promise=data.CHATBOT["promise"], locked=bool(locked) and not consent.get("chat"),
                  today_emotion=today_emotion == "1")


@app.post("/student/promise")
def save_promise(basic: Annotated[list[str], Form()] = [], chat: Annotated[list[str], Form()] = [],
                 today_emotion: Annotated[str, Form()] = ""):
    need = data.CHATBOT["promise"]
    if len(set(basic)) < len(need["basic"]):
        resume = "&locked=1&today_emotion=1" if today_emotion == "1" else ""
        return back(f"/student/promise?msg=need_basic{resume}")
    with store.editing() as state:
        consent = {"basic": True, "chat": len(set(chat)) >= len(need["chat"]), "date": today_key(), "time": now_time()}
        state["consent"] = consent
        keep(state, "consent", ME_ID, None, {"basic": True, "chat": consent["chat"]})  # 무엇을 약속했는지도 원본 그대로 보존
    return back("/student?saved=1&msg=promise" if today_emotion == "1" and consent["chat"] else "/student?msg=promise")


# ── 학생: 홈 ─────────────────────────────────────────────────────────────────


@app.get("/student")
def student_home(request: Request, saved: str = ""):
    state, today = store.load(), today_key()
    if state["profile"] is None and not state["profile_skipped"]:
        return back("/student/welcome")
    if not state.get("consent"):
        return back("/student/promise")
    records = data.records_for(ME_ID, state, today)
    by_date = {r.date: r for r in records}
    today_record = by_date.get(today)
    if today_record is None and state["record_later"] != today:
        return back("/student/record")  # 오늘 기록이 없으면 홈보다 감정 휠을 먼저 보여 줌
    report = student_report(records, today)
    chatted_today = any(m["date"] == today and m["role"] == "me" for m in state["chats"])
    return render(
        request,
        "student_home.html",
        mode="student",
        state=state,
        me=data.get_student(ME_ID),
        today_record=today_record,
        week=[{"date": d, "record": by_date.get(d)} for d in (add_days(today, i - 6) for i in range(7))],
        streak=points.streak(records, today),
        report=report,
        saved=bool(saved) and today_record is not None,
        earned=points.earned_on(records, today) if saved else [],
        suggest_chat=bool(today_record and EMOTIONS[today_record.emotion].negative and not chatted_today),
        bookings=[b for b in state["bookings"] if b["student_id"] == ME_ID and b["status"] in ("requested", "confirmed")],
        conversation_pending=any(r["student_id"] == ME_ID and r["status"] in CONVERSATION_ACTIVE
                                 for r in state["conversation_requests"]),
    )


# ── 학생: 감정 기록 (기획서 (2)-1) ────────────────────────────────────────────


@app.get("/student/record")
def record_page(request: Request, e: str = ""):
    state, today = store.load(), today_key()
    existing = next((r for r in data.records_for(ME_ID, state, today) if r.date == today), None)
    return render(request, "student_record.html", mode="student", state=state, existing=existing,
                  preselect=e if e in EMOTIONS else "" if e == "none" else (existing.emotion if existing else ""))


@app.post("/student/record/later")
def record_later():
    """오늘 기록을 미룸: 오늘 하루는 홈에 들어올 때 감정 휠을 먼저 띄우지 않음"""
    with store.editing() as state:
        state["record_later"] = today_key()
    return back("/student")


def parse_intensity(raw: str) -> int | None:
    """폼에서 온 강도 값을 1~5로 맞춤. 숫자가 아니면 기록하지 않음"""
    try:
        return min(5, max(1, int(raw)))
    except ValueError:
        return None


@app.post("/student/record")
def save_record(
    emotion: Annotated[str, Form()],
    words: Annotated[list[str], Form()] = [],
    note: Annotated[str, Form()] = "",
    shared: Annotated[str, Form()] = "",
    intensity: Annotated[str, Form()] = "",
):
    if emotion not in EMOTIONS:
        raise HTTPException(400, "알 수 없는 감정입니다.")
    today = today_key()
    note = note.strip()[:300]
    with store.editing() as state:
        record = {"id": f"{ME_ID}:{today}", "student_id": ME_ID, "date": today, "emotion": emotion,
                  "words": [w for w in words if w in EMOTIONS[emotion].words][:5], "note": note or None, "shared": bool(shared),
                  "intensity": parse_intensity(intensity)}
        state["my_records"] = [r for r in state["my_records"] if r["date"] != today] + [record]
        state["share_overrides"].pop(f"{ME_ID}:{today}", None)
        # 같은 날 다시 고쳐 써도 앞서 쓴 기록은 보존 기록에 그대로 남고, 고친 내용이 새 줄로 덧붙음
        keep(state, "record", ME_ID, record["id"], {k: v for k, v in record.items() if k not in ("id", "student_id")})
        hits = risk_hits(note)
        if hits:  # 어떤 표현이었는지는 알림에 담지 않고, 신호가 있었다는 사실과 단계만 남김
            urgent = any(h["id"] == "urgent" for h in hits)
            add_alert(state, ME_ID, "record", "signal",
                      "감정 기록에서 긴급한 위험 신호가 감지되었어요. 오늘 안에 학생의 안전을 확인해 주세요." if urgent
                      else "감정 기록에서 위험 신호가 감지되었어요.", level="urgent" if urgent else "issue")
    return back("/student?saved=1")


@app.post("/student/records/share")
def share_record(record_id: Annotated[str, Form()], shared: Annotated[str, Form()] = ""):
    with store.editing() as state:
        state["share_overrides"][record_id] = shared == "1"
        keep(state, "share", ME_ID, record_id, {"shared": shared == "1"})
    return back("/student/report#records")


# ── 학생: 감정 리포트 (기획서 (2)-2) ──────────────────────────────────────────


@app.get("/student/report")
def student_report_page(request: Request):
    state, today = store.load(), today_key()
    records = data.records_for(ME_ID, state, today)
    report = student_report(records, today)
    by_date = {r.date: r for r in records}
    events_by_date = data.school_schedule_for(ME_ID, today)
    return render(
        request,
        "student_report.html",
        mode="student",
        state=state,
        report=report,
        chart=charts.mood_chart(report.series, today),
        donut=charts.donut(report.ratio),
        calendar=[{"date": d, "record": by_date.get(d), "events": events_by_date.get(d, [])} for d in month_days(today)],
        month=int(today[5:7]),
        recent=sorted(records, key=lambda r: r.date, reverse=True)[:7],
    )


# ── 학생: 복복이 (기획서 (3)) ─────────────────────────────────────────────────


def _chat_view(state: dict, today: str) -> list[dict]:
    """오늘 대화가 없으면 복복이가 먼저 인사"""
    messages = [m for m in state["chats"] if m["date"] == today]
    if not messages:
        greeting = {"id": store.new_id("M"), "role": "bot", "date": today, "time": now_time(),
                    "text": chatbot.greeting(today), "kind": "normal", "source": "rule"}
        state["chats"].append(greeting)
        messages.append(greeting)
    return messages


def _said(messages: list[dict]) -> list[str]:
    """학생이 직접 쓴 말만 (버튼으로 고른 대답 제외)"""
    return [m["text"] for m in messages if m["role"] == "me" and m.get("kind") in ("normal", None)]


def chat_days(state: dict, today: str) -> list[dict]:
    """복복이 대화를 날짜별로 묶고 하루 요약을 붙임 (최근 날짜부터). 학생 본인만 보는 기록입니다.

    요약은 처음 볼 때 만들어 저장해 두고, 그날 학생이 한 말이 늘어났을 때만 다시 만듭니다.
    """
    saved = state.setdefault("chat_days", {})
    days = []
    for date in sorted({m["date"] for m in state["chats"]}, reverse=True):
        messages = [m for m in state["chats"] if m["date"] == date]
        said = _said(messages)
        if not said:
            saved.pop(date, None)
            if date != today:
                continue  # 복복이 인사만 있고 학생이 말하지 않은 날은 기록에 넣지 않음
        elif saved.get(date, {}).get("count") != len(said):
            summary, source = chatbot.day_summary(said)
            saved[date] = {"summary": summary, "count": len(said), "source": source}
        days.append({"date": date, "messages": messages, "said": len(said), **saved.get(date, {"summary": None})})
    return days


def _append_turn(state: dict, text: str) -> list[dict]:
    """학생의 말과 복복이의 대답을 대화에 추가하고, 추가된 메시지를 돌려줌"""
    today = today_key()
    history = [m for m in state["chats"] if m["role"] in ("me", "bot") and m["date"] == today]  # 하루 단위로 새 대화
    me = {"id": store.new_id("M"), "role": "me", "date": today, "time": now_time(),
          "text": profanity.mask(text), "kind": "normal"}  # 욕설은 * 로 가려 저장·표시. 대답과 신호 판단은 원래 말로
    reply, signals = chatbot.converse(history, text, today)
    bot = {"id": store.new_id("M"), "role": "bot", "date": today, "time": now_time(), "text": reply["text"],
           "kind": reply["kind"], "source": reply["source"], "help": reply.get("help"),
           "emotions": reply.get("emotions", [])}
    state["chats"] += [me, bot]
    for m in (me, bot):
        keep(state, "chat", ME_ID, m["id"], {"role": m["role"], "date": m["date"], "text": m["text"], "kind": m["kind"]})
    # 선생님께는 조용히 전함: 학생 화면에는 아무 표시도 하지 않음.
    # 무슨 이야기였는지(분류·AI 요약)는 저장하지도 전하지도 않고, '신호가 있었다'는 사실과 단계만 하루에 하나 남김
    for sig in signals:
        add_alert(state, ME_ID, "chat", "signal", data.CHATBOT["judge"]["alert_text"][sig["level"]], level=sig["level"])
    return [me, bot]


@app.get("/student/chat")
def chat_page(request: Request):
    today = today_key()
    if not chat_allowed(store.load()):
        return back("/student/promise?locked=1")
    with store.editing() as state:
        messages = _chat_view(state, today)
    return render(request, "student_chat.html", mode="student", state=state, messages=messages,
                  status=chatbot.status(), suggestions=data.CHATBOT["suggestions"],
                  notice=data.CHATBOT["privacy_notice"], safety=data.CHATBOT["safety"])


@app.post("/student/chat")
def chat_send(text: Annotated[str, Form()] = ""):
    text = text.strip()[:500]
    if not chat_allowed(store.load()):
        return back("/student/promise?locked=1")
    if text:
        with store.editing() as state:
            _append_turn(state, text)
    return back("/student/chat#end")


@app.post("/student/chat/today-emotion")
def chat_about_today_emotion():
    today = today_key()
    with store.editing() as state:
        if not chat_allowed(state):
            return back("/student/promise?locked=1&today_emotion=1")
        record = next((r for r in data.records_for(ME_ID, state, today) if r.date == today), None)
        if record is None:
            return back("/student/chat")

        text = chatbot.emotion_question(record.emotion, record.intensity)
        messages = [m for m in state["chats"] if m["date"] == today]
        if (len(messages) == 1 and messages[0]["role"] == "bot"
                and messages[0].get("kind") == "normal" and messages[0].get("source") == "rule"):
            messages[0]["text"] = text
        elif not messages or messages[-1]["role"] != "bot" or messages[-1]["text"] != text:
            state["chats"].append({"id": store.new_id("M"), "role": "bot", "date": today, "time": now_time(),
                                   "text": text, "kind": "normal", "source": "rule"})
    return back("/student/chat#end")


@app.post("/api/chat")
def chat_api(request: Request, text: Annotated[str, Form()] = ""):
    """자바스크립트용: 새로 추가된 말풍선을 HTML 조각으로 돌려줌"""
    text = text.strip()[:500]
    if not text:
        return JSONResponse({"html": ""})
    if not chat_allowed(store.load()):
        return JSONResponse({"html": "", "error": "promise_needed"}, status_code=403)
    with store.editing() as state:
        added = _append_turn(state, text)
    html = templates.get_template("_chat_messages.html").render(
        messages=added, safety=data.CHATBOT["safety"], icon=icon, BOT=BOT_NAME, CONTACTS=data.CONTACTS, btn=BTN
    )
    return JSONResponse({"html": html})


@app.post("/student/chat/safety")
def chat_safety(answer: Annotated[str, Form()]):
    """'지금 안전한 곳에 있나요?' 대답"""
    opt = next(o for o in data.CHATBOT["safety"]["options"] if o["id"] == "safe")
    today = today_key()
    with store.editing() as state:
        added = [{"id": store.new_id("M"), "role": "me", "date": today, "time": now_time(),
                  "text": "응, 안전한 곳에 있어" if answer == "yes" else "아니, 안전하지 않아", "kind": "choice"},
                 {"id": store.new_id("M"), "role": "bot", "date": today, "time": now_time(),
                  "text": opt["reply_yes"] if answer == "yes" else opt["reply_no"],
                  "kind": "normal" if answer == "yes" else "urgent", "source": "safety"}]
        state["chats"] += added
        for m in added:
            keep(state, "chat", ME_ID, m["id"], {"role": m["role"], "date": m["date"], "text": m["text"], "kind": m["kind"]})
        if answer != "yes":
            add_alert(state, ME_ID, "chat", "unsafe", f"학생이 {BOT_NAME}에게 ‘지금 안전하지 않다’고 답했어요. 즉시 확인이 필요해요.", level="urgent")
    return back("/student/chat#end")


@app.get("/student/chat/history")
def chat_history(request: Request):
    """날짜별 대화 기록: 하루 요약 + 그날 대화 원문. 학생 본인만 봅니다 (선생님 화면에는 없음)."""
    today = today_key()
    with store.editing() as state:
        days = chat_days(state, today)
    return render(request, "student_chat_history.html", mode="student", state=state, days=days, status=chatbot.status(),
                  safety=data.CHATBOT["safety"])


def _forget_day(state: dict, date: str) -> None:
    """그날의 대화를 학생의 화면에서 지움. 보존 기록에 남은 원본은 지워지지 않고, '지웠다'는 줄이 덧붙습니다."""
    gone = [m for m in state["chats"] if m["date"] == date]
    state["chats"] = [m for m in state["chats"] if m["date"] != date]
    state.setdefault("chat_days", {}).pop(date, None)
    if gone:
        keep(state, "chat_hide", ME_ID, date, {"date": date, "messages": len(gone)})


@app.post("/student/chat/clear")
def chat_clear():
    """오늘 대화 지우기 (지난 날의 기록은 '대화 기록' 화면에서 하루씩 지움)"""
    with store.editing() as state:
        _forget_day(state, today_key())
    return back("/student/chat")


@app.post("/student/chat/history/delete")
def chat_history_delete(date: Annotated[str, Form()]):
    """학생이 자기 대화 기록을 하루 단위로 지움"""
    with store.editing() as state:
        _forget_day(state, date)
    return back("/student/chat/history?msg=deleted")


# ── 학생: 도움이 필요할 때 (기획서 (4)) ───────────────────────────────────────


@app.get("/student/help")
def help_page(request: Request):
    return render(request, "student_help.html", mode="student", categories=data.HELP_CATEGORIES, links=data.HELP_LINKS)


@app.get("/student/help/{slug}")
def help_detail(request: Request, slug: str):
    category = data.get_help(slug)
    if not category:
        raise HTTPException(404, "도움 페이지를 찾을 수 없습니다.")
    return render(request, "student_help_detail.html", mode="student", c=category, links=data.HELP_LINKS)


# ── 학생: 상담 신청 (기획서 (4)-1) ────────────────────────────────────────────


CONVERSATION_ACTIVE = ("requested", "acknowledged", "proposed")


def _reserved_times(state: dict) -> dict[tuple[str, str, str], dict]:
    reserved = {(b["teacher"], b["date"], b["time"]): b for b in state["bookings"]
                if b["status"] in ("requested", "confirmed")}
    for request in state["conversation_requests"]:
        if request["status"] == "proposed":
            day, time = request["slot"].split("T")
            reserved[request["teacher"], day, time] = request
    return reserved


def _open_slots(state: dict, teacher: str, today: str) -> list[dict]:
    reserved = _reserved_times(state)
    student_times = {(day, time) for (_, day, time), reservation in reserved.items() if reservation["student_id"] == ME_ID}
    slots = [s for s in state["slots"].get(teacher, [])
             if s["date"] >= today and (teacher, s["date"], s["time"]) not in reserved
             and (s["date"], s["time"]) not in student_times]
    return sorted(slots, key=lambda s: (s["date"], s["time"]))


@app.get("/student/counsel")
def counsel_page(request: Request, teacher: str = ""):
    state, today = store.load(), today_key()
    report = teacher_report(data.records_for(ME_ID, state, today), today,
                            [a for a in state["alerts"] if a["student_id"] == ME_ID])
    return render(
        request,
        "student_counsel.html",
        mode="student",
        state=state,
        open_slots={t: _open_slots(state, t, today) for t in data.TEACHERS},
        selected=teacher if teacher in data.TEACHERS else "",
        mine=sorted((b for b in state["bookings"] if b["student_id"] == ME_ID), key=lambda b: (b["date"], b["time"]), reverse=True),
        conversations=[r for r in reversed(state["conversation_requests"])
                       if r["student_id"] == ME_ID and r["status"] in CONVERSATION_ACTIVE],
        recommend=report.level in ("consult", "watch"),
        links=data.HELP_LINKS,
    )


@app.post("/student/counsel")
def book_counsel(slot_id: Annotated[str, Form()], topic: Annotated[str, Form()] = ""):
    today = today_key()
    with store.editing() as state:
        slot = teacher = None
        for t, slots in state["slots"].items():
            for s in slots:
                if s["id"] == slot_id:
                    slot, teacher = s, t
        if not slot or slot not in _open_slots(state, teacher, today):
            return back("/student/counsel?msg=slot_taken")
        state["bookings"].append(
            {"id": store.new_id("BK"), "student_id": ME_ID, "teacher": teacher, "slot_id": slot_id, "date": slot["date"],
             "time": slot["time"], "topic": topic.strip()[:60] or "주제를 정하지 않음", "status": "requested", "created": today}
        )
    return back("/student/counsel?msg=booked")


@app.post("/student/counsel/{booking_id}/cancel")
def cancel_booking(booking_id: str):
    with store.editing() as state:
        for b in state["bookings"]:
            if b["id"] == booking_id and b["student_id"] == ME_ID and b["status"] in ("requested", "confirmed"):
                b["status"] = "cancelled"
    return back("/student/counsel?msg=booking_cancelled")


def _conversation_by_id(state: dict, request_id: str, student_id: str | None = None) -> dict:
    item = next((r for r in state["conversation_requests"] if r["id"] == request_id), None)
    if item is None or (student_id is not None and item["student_id"] != student_id):
        raise HTTPException(404, "대화 요청을 찾을 수 없어요.")
    return item


@app.post("/student/counsel/requests")
def request_conversation(teacher: Annotated[str, Form()]):
    if teacher not in data.TEACHERS:
        raise HTTPException(400, "이야기하고 싶은 선생님을 골라 주세요.")
    with store.editing() as state:
        active = any(r["student_id"] == ME_ID and r["teacher"] == teacher and r["status"] in CONVERSATION_ACTIVE
                     for r in state["conversation_requests"])
        if not active:
            state["conversation_requests"].append({
                "id": store.new_id("CR"), "student_id": ME_ID, "teacher": teacher,
                "status": "requested", "created": today_key(),
            })
    return back(f"/student/counsel?msg=conversation_sent#{teacher}-conversation")


@app.post("/student/counsel/requests/{request_id}/cancel")
def cancel_conversation(request_id: str):
    with store.editing() as state:
        item = _conversation_by_id(state, request_id, ME_ID)
        if item["status"] == "booked":
            raise HTTPException(409, "이미 확정된 시간이에요. 내 상담 신청에서 취소할 수 있어요.")
        item["status"] = "cancelled"
        item.pop("slot", None)
    return back("/student/counsel?msg=conversation_cancelled#conversation")


@app.post("/student/counsel/requests/{request_id}/another-time")
def request_another_time(request_id: str, slot: Annotated[str, Form()]):
    with store.editing() as state:
        item = _conversation_by_id(state, request_id, ME_ID)
        if item["status"] == "proposed" and item["slot"] == slot:
            item["status"] = "acknowledged"
            item.pop("slot")
        elif item["status"] != "acknowledged":
            raise HTTPException(409, "제안이 바뀌었어요. 최신 시간을 확인해 주세요.")
    return back("/student/counsel?msg=conversation_retry#conversation")


@app.post("/student/counsel/requests/{request_id}/accept")
def accept_conversation(request_id: str, slot: Annotated[str, Form()]):
    with store.editing() as state:
        item = _conversation_by_id(state, request_id, ME_ID)
        if item["status"] == "booked" and item["slot"] == slot:
            return back("/student/counsel?msg=conversation_confirmed")
        if item["status"] != "proposed" or item["slot"] != slot:
            raise HTTPException(409, "제안이 바뀌었어요. 최신 시간을 확인해 주세요.")
        day, time = slot.split("T")
        if day < today_key():
            raise HTTPException(409, "제안한 날짜가 지났어요. 다른 시간을 부탁해 주세요.")
        state["bookings"].append({
            "id": store.new_id("BK"), "student_id": ME_ID, "teacher": item["teacher"],
            "date": day, "time": time, "topic": "잠깐 대화 요청", "status": "confirmed", "created": today_key(),
        })
        item["status"] = "booked"
    return back("/student/counsel?msg=conversation_confirmed")


# ── 학생: 포인트 · 상점 (기획서 (5)) ──────────────────────────────────────────


def _on_sale(item: dict, today: str) -> bool:
    return item["on_sale"] and (not item.get("start") or item["start"] <= today) and (not item.get("end") or today <= item["end"])


def _used_count(state: dict, student_id: str, item_id: str) -> int:
    return sum(1 for o in state["orders"] if o["student_id"] == student_id and o["item_id"] == item_id and o["status"] in ("pending", "approved"))


@app.get("/student/shop")
def shop_page(request: Request):
    state, today = store.load(), today_key()
    balance = points.balance(_ledger(ME_ID, state, today))
    items = [
        {**i, "available": _on_sale(i, today), "left": max(0, i["limit"] - _used_count(state, ME_ID, i["id"])),
         "affordable": balance >= i["price"]}
        for i in state["items"]
    ]
    items.sort(key=lambda i: (not i["available"], i["price"]))
    orders = sorted((o for o in state["orders"] if o["student_id"] == ME_ID), key=lambda o: o["date"], reverse=True)
    return render(request, "student_shop.html", mode="student", state=state, items=items, balance=balance,
                  orders=orders, item_map=items_by_id(state))


@app.post("/student/shop/{item_id}")
def order_item(item_id: str):
    today = today_key()
    with store.editing() as state:
        item = items_by_id(state).get(item_id)
        balance = points.balance(_ledger(ME_ID, state, today))
        if not item or not _on_sale(item, today) or balance < item["price"] or _used_count(state, ME_ID, item_id) >= item["limit"]:
            return back("/student/shop?msg=not_enough")
        state["orders"].append({"id": store.new_id("OR"), "student_id": ME_ID, "item_id": item_id, "date": today, "status": "pending"})
    return back("/student/shop?msg=ordered")


@app.post("/student/shop/orders/{order_id}/cancel")
def cancel_order(order_id: str):
    with store.editing() as state:
        for o in state["orders"]:
            if o["id"] == order_id and o["student_id"] == ME_ID and o["status"] == "pending":
                o["status"] = "cancelled"
    return back("/student/shop?msg=order_cancelled")


@app.get("/student/points")
def points_page(request: Request):
    state, today = store.load(), today_key()
    entries = _ledger(ME_ID, state, today)
    records = data.records_for(ME_ID, state, today)
    return render(request, "student_points.html", mode="student", state=state, entries=entries,
                  balance=points.balance(entries), total=points.total_earned(entries), streak=points.streak(records, today),
                  month_count=sum(1 for r in records if r.date[:7] == today[:7]), rules=points)


# ── 선생님: 정서 현황 ─────────────────────────────────────────────────────────


def student_bundle(student: dict, state: dict, today: str) -> dict:
    records = data.records_for(student["id"], state, today)
    alerts = [a for a in state["alerts"] if a["student_id"] == student["id"]]
    attendance = attendance_summary(data.attendance_for(student["id"], today), today)
    return {
        "student": student,
        "records": records,
        "report": teacher_report(records, today, alerts, attendance=attendance),
        "attendance": attendance,
        "followup": state["followups"].get(student["id"], "none"),
        "today": next((r for r in records if r.date == today), None),
        "unread": sum(1 for a in alerts if not a["read"]),
        "alerts": sorted(alerts, key=lambda a: (a["date"], a["time"]), reverse=True),
    }


@app.get("/teacher")
def teacher_home(request: Request, level: str = "all"):
    state, today = store.load(), today_key()
    rows = [student_bundle(s, state, today) for s in data.STUDENTS]
    for r in rows:
        r["spark"] = charts.sparkline(r["report"].series)
    rows.sort(key=lambda r: (LEVEL_ORDER.index(r["report"].level), -r["unread"], r["student"]["no"]))
    counts = Counter(r["report"].level for r in rows)
    month_records = [rec for r in rows for rec in r["records"] if rec.date[:7] == today[:7]]
    month_ratio = Counter(rec.emotion for rec in month_records)
    selected = level if level in LEVELS else "all"
    alert_tasks = sorted(
        (a for a in state["alerts"] if not a.get("task", {}).get("completed_at")),
        key=lambda a: (-ALERT_LEVELS.get(a.get("level"), 2), a.get("task", {}).get("due", today), a["date"]),
    )
    return render(
        request,
        "teacher_home.html",
        mode="teacher",
        state=state,
        rows=[r for r in rows if selected == "all" or r["report"].level == selected],
        total=len(rows),
        counts=counts,
        recorded_today=sum(1 for r in rows if r["today"]),
        selected=selected,
        alert_tasks=alert_tasks,
        conversations=[r for r in state["conversation_requests"] if r["status"] in ("requested", "acknowledged")
                       or (r["status"] == "proposed" and r["slot"][:10] < today)],
        month=int(today[5:7]),
        month_ratio=[{"emotion": e, "count": month_ratio[e], "pct": round(month_ratio[e] / max(1, len(month_records)) * 100)}
                     for e in EMOTIONS],
    )


@app.get("/teacher/students/{student_id}")
def teacher_student(request: Request, student_id: str):
    state, today = store.load(), today_key()
    student = data.get_student(student_id)
    if not student:
        raise HTTPException(404, "학생 정보를 찾을 수 없습니다.")
    b = student_bundle(student, state, today)
    assessments = data.assessments_for(student_id, today)
    series = b["report"].series
    chart_start = series[0].date
    entries = _ledger(student_id, state, today)
    return render(
        request,
        "teacher_student.html",
        mode="teacher",
        state=state,
        b=b,
        r=b["report"],
        change=describe_change(b["report"]),
        chart=charts.mood_chart(series, today, attendance=b["attendance"], assessments=assessments),
        assessment_results=[result for result in compare_results(assessments, b["records"], today)
                            if result.assessment.result_date >= chart_start],
        profile=data.profile_for(student, state),
        records=[data.teacher_record(r) for r in sorted(b["records"], key=lambda r: r.date, reverse=True)[:14]],
        notes=state["followup_notes"].get(student_id, []),
        shares=[share for share in reversed(state["support_shares"]) if share["student_id"] == student_id],
        bookings=sorted((x for x in state["bookings"] if x["student_id"] == student_id), key=lambda x: x["date"], reverse=True),
        balance=points.balance(entries),
        earned_total=points.total_earned(entries),
        orders=[o for o in state["orders"] if o["student_id"] == student_id],
        item_map=items_by_id(state),
    )


@app.post("/teacher/students/{student_id}/followup")
def save_followup(student_id: str, status: Annotated[str, Form()] = "", note: Annotated[str, Form()] = ""):
    if not data.get_student(student_id):
        raise HTTPException(404, "학생 정보를 찾을 수 없습니다.")
    with store.editing() as state:
        text = note.strip()[:500]
        if status in FOLLOWUP and status != state["followups"].get(student_id, "none"):
            state["followups"][student_id] = status
            text = f"[{FOLLOWUP[status]}] {text}".strip()
        if text:
            state["followup_notes"].setdefault(student_id, []).append({"date": today_key(), "time": now_time(), "text": text})
            keep(state, "followup", student_id, None, {"status": state["followups"].get(student_id, "none"), "text": text})
        for a in state["alerts"]:
            if a["student_id"] == student_id and not a["read"]:
                a["read"] = True
                keep(state, "alert_read", student_id, a["id"], {"by": "사후 관리 기록"})
    return back(f"/teacher/students/{student_id}?msg=followup#followup")


@app.get("/teacher/shares")
def teacher_shares(request: Request, teacher: str = "homeroom"):
    if teacher not in data.TEACHERS:
        raise HTTPException(404, "선생님을 찾을 수 없습니다.")
    state = store.load()
    shares = list(reversed(state["support_shares"]))
    return render(request, "teacher_shares.html", mode="teacher", state=state, teacher=teacher,
                  received=[s for s in shares if s["recipient"] == teacher],
                  sent=[s for s in shares if s["sender"] == teacher])


@app.post("/teacher/students/{student_id}/shares")
def share_student_support(student_id: str, sender: Annotated[str, Form()], recipient: Annotated[str, Form()],
                          note: Annotated[str, Form()]):
    if not data.get_student(student_id):
        raise HTTPException(404, "학생 정보를 찾을 수 없습니다.")
    if sender not in data.TEACHERS or recipient not in data.TEACHERS or sender == recipient:
        raise HTTPException(400, "보내는 선생님과 받는 선생님을 다르게 선택해 주세요.")
    note = note.strip()
    if not 1 <= len(note) <= 500:
        raise HTTPException(400, "지원 메모를 1~500자로 적어 주세요.")
    with store.editing() as state:
        share = {"id": store.new_id("SH"), "student_id": student_id, "sender": sender, "recipient": recipient,
                 "note": note, "date": today_key(), "time": now_time()}
        state["support_shares"].append(share)
        keep(state, "support_share", student_id, share["id"], {"sender": sender, "recipient": recipient})
    return back(f"/teacher/students/{student_id}?msg=support_shared#shares")


# ── 선생님: 알림 (카톡 공지처럼) ───────────────────────────────────────────────


@app.get("/teacher/alerts")
def alerts_page(request: Request):
    state = store.load()
    alerts = sorted(state["alerts"], key=lambda a: (a["date"], a["time"]), reverse=True)
    return render(request, "teacher_alerts.html", mode="teacher", state=state, alerts=alerts)


# ── 선생님: 기록 보존 (무결성·위변조 방지) ─────────────────────────────────────


@app.get("/teacher/ledger")
def ledger_page(request: Request):
    """보존 기록의 위변조 여부를 다시 계산해 보여 주고, 최근 내역을 해시와 함께 보여 줌 (원본 내용은 보여 주지 않음)"""
    state = store.load()
    rows = [e for e in ledger.entries() if "hash" in e]
    return render(request, "teacher_ledger.html", mode="teacher", state=state, check=ledger.verify(state.get("ledger_head")),
                  rows=rows[::-1][:60], total=len(rows), head=ledger.head(), KINDS=ledger.KINDS, checked_at=ledger.server_now())


@app.post("/teacher/alerts/{alert_id}/read")
def read_alert(alert_id: str, next: Annotated[str, Form()] = "/teacher/alerts"):
    with store.editing() as state:
        for a in state["alerts"]:
            if a["id"] == alert_id and not a["read"]:
                a["read"] = True
                keep(state, "alert_read", a["student_id"], a["id"], {"by": "알림 확인"})
    return back(next if next.startswith("/") and not next.startswith("//") else "/teacher/alerts")


def _alert_by_id(state: dict, alert_id: str) -> dict:
    alert = next((a for a in state["alerts"] if a["id"] == alert_id), None)
    if alert is None:
        raise HTTPException(404, "알림을 찾을 수 없어요.")
    return alert


@app.post("/teacher/alerts/{alert_id}/task")
def plan_alert_task(alert_id: str, teacher: Annotated[str, Form()], due: Annotated[str, Form()],
                    action: Annotated[str, Form()]):
    action = action.strip()
    try:
        due_date = date.fromisoformat(due).isoformat()
    except ValueError:
        raise HTTPException(400, "올바른 예정일을 골라 주세요.")
    if teacher not in data.TEACHERS or due_date != due or not 1 <= len(action) <= 120:
        raise HTTPException(400, "담당 선생님, 예정일, 다음 행동을 입력해 주세요.")
    with store.editing() as state:
        alert = _alert_by_id(state, alert_id)
        current = alert.get("task") or {}
        if current.get("completed_at"):
            raise HTTPException(409, "이미 완료한 조치예요.")
        plan = {"teacher": teacher, "due": due, "action": action}
        if any(current.get(key) != value for key, value in plan.items()):
            alert["task"] = {"id": store.new_id("AT"), **plan}
            keep(state, "alert_task_planned", alert["student_id"], alert_id, alert["task"])
    return back(f"/teacher/alerts?msg=alert_task_saved#{alert_id}")


@app.post("/teacher/alerts/{alert_id}/task/complete")
def complete_alert_task(alert_id: str, task_id: Annotated[str, Form()] = ""):
    with store.editing() as state:
        alert = _alert_by_id(state, alert_id)
        task = alert.get("task")
        if not task or task["id"] != task_id:
            raise HTTPException(409, "조치 계획이 바뀌었어요. 알림에서 최신 계획을 확인해 주세요.")
        if not task.get("completed_at"):
            task["completed_at"] = ledger.server_now()
            alert["read"] = True
            keep(state, "alert_task_completed", alert["student_id"], alert_id, task)
    return back(f"/teacher/alerts?msg=alert_task_done#{alert_id}")


# ── 선생님: 상담 일정 ─────────────────────────────────────────────────────────

BOOKING_STATUS = {"requested": "신청됨", "confirmed": "확정", "done": "상담 완료", "declined": "다른 시간 요청", "cancelled": "학생 취소"}
templates.env.globals["BOOKING_STATUS"] = BOOKING_STATUS


@app.get("/teacher/counsel")
def teacher_counsel(request: Request):
    state, today = store.load(), today_key()
    taken = _reserved_times(state)
    slots = {
        t: [{**s, "booking": taken.get((t, s["date"], s["time"]))}
            for s in sorted(state["slots"].get(t, []), key=lambda s: (s["date"], s["time"])) if s["date"] >= today]
        for t in data.TEACHERS
    }
    bookings = sorted(state["bookings"], key=lambda b: (b["status"] != "requested", b["date"], b["time"]))
    conversations = [r for r in state["conversation_requests"] if r["status"] in CONVERSATION_ACTIVE]
    return render(request, "teacher_counsel.html", mode="teacher", state=state, slots=slots, bookings=bookings,
                  conversations=conversations,
                  times=["08:20", "12:50", "15:40", "16:20", "17:00"])


@app.post("/teacher/counsel/requests/{request_id}/acknowledge")
def acknowledge_conversation(request_id: str):
    with store.editing() as state:
        item = _conversation_by_id(state, request_id)
        if item["status"] == "requested":
            item["status"] = "acknowledged"
    return back(f"/teacher/counsel#{request_id}")


@app.post("/teacher/counsel/requests/{request_id}/propose")
def propose_conversation(request_id: str, day: Annotated[str, Form(alias="date")], time: Annotated[str, Form()]):
    slot = f"{day}T{time}"
    try:
        parsed = datetime.fromisoformat(slot)
    except ValueError:
        raise HTTPException(400, "올바른 날짜와 시간을 골라 주세요.")
    today = today_key()
    if parsed.isoformat(timespec="minutes") != slot or day < today:
        raise HTTPException(400, "오늘 이후의 날짜와 시간을 골라 주세요.")
    with store.editing() as state:
        item = _conversation_by_id(state, request_id)
        if item["status"] == "proposed" and item["slot"] == slot:
            return back(f"/teacher/counsel#{request_id}")
        expired = item["status"] == "proposed" and item["slot"][:10] < today
        if item["status"] != "acknowledged" and not expired:
            raise HTTPException(409, "현재 대화 요청 상태에서는 시간을 제안할 수 없어요.")
        reservations = _reserved_times(state)
        if any((reserved_day, reserved_time) == (day, time)
               and (teacher == item["teacher"] or reservation["student_id"] == item["student_id"])
               for (teacher, reserved_day, reserved_time), reservation in reservations.items()):
            return back(f"/teacher/counsel?msg=conversation_taken#{request_id}")
        item.update(status="proposed", slot=slot)
    return back(f"/teacher/counsel#{request_id}")


@app.post("/teacher/counsel/slots")
def add_slot(teacher: Annotated[str, Form()], date: Annotated[str, Form()], time: Annotated[str, Form()]):
    if teacher not in data.TEACHERS or not date or not time:
        raise HTTPException(400, "선생님·날짜·시간을 모두 골라 주세요.")
    with store.editing() as state:
        if not any(s["date"] == date and s["time"] == time for s in state["slots"].setdefault(teacher, [])):
            state["slots"][teacher].append({"id": store.new_id("SL"), "date": date, "time": time})
    return back("/teacher/counsel?msg=slot_added")


@app.post("/teacher/counsel/slots/{slot_id}/delete")
def delete_slot(slot_id: str):
    with store.editing() as state:
        for t in state["slots"]:
            state["slots"][t] = [s for s in state["slots"][t] if s["id"] != slot_id]
    return back("/teacher/counsel")


@app.post("/teacher/counsel/bookings/{booking_id}")
def update_booking(booking_id: str, status: Annotated[str, Form()]):
    if status not in BOOKING_STATUS:
        raise HTTPException(400, "알 수 없는 상태입니다.")
    with store.editing() as state:
        for b in state["bookings"]:
            if b["id"] == booking_id:
                b["status"] = status
                if status in ("confirmed", "done") and state["followups"].get(b["student_id"], "none") in ("none", "checked"):
                    state["followups"][b["student_id"]] = "talking"
    return back("/teacher/counsel")


# ── 선생님: 상점 관리 ─────────────────────────────────────────────────────────

IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}


@app.get("/teacher/shop")
def teacher_shop(request: Request, edit: str = ""):
    state, today = store.load(), today_key()
    pending = [o for o in state["orders"] if o["status"] == "pending"]
    history = sorted((o for o in state["orders"] if o["status"] != "pending"), key=lambda o: o["date"], reverse=True)
    ledgers = [
        {"student": s, "entries": (e := _ledger(s["id"], state, today)), "balance": points.balance(e), "earned": points.total_earned(e),
         "spent": -sum(x.amount for x in e if x.kind == "spend")}
        for s in data.STUDENTS
    ]
    editing = items_by_id(state).get(edit) if edit and edit != "new" else ({} if edit == "new" else None)
    return render(request, "teacher_shop.html", mode="teacher", state=state, items=state["items"], pending=pending,
                  history=history, ledgers=ledgers, item_map=items_by_id(state), editing=editing,
                  sold={i["id"]: sum(1 for o in state["orders"] if o["item_id"] == i["id"] and o["status"] == "approved") for i in state["items"]})


@app.post("/teacher/shop/items")
async def save_item(
    item_id: Annotated[str, Form()] = "",
    name: Annotated[str, Form()] = "",
    desc: Annotated[str, Form()] = "",
    emoji: Annotated[str, Form()] = "🎁",
    price: Annotated[int, Form()] = 100,
    limit: Annotated[int, Form()] = 1,
    on_sale: Annotated[str, Form()] = "",
    start: Annotated[str, Form()] = "",
    end: Annotated[str, Form()] = "",
    remove_image: Annotated[str, Form()] = "",
    image: Annotated[UploadFile | None, File()] = None,
):
    if not name.strip():
        raise HTTPException(400, "상품 이름을 입력해 주세요.")
    image_name = None
    if image is not None and image.filename:
        content = await image.read()
        ext = IMAGE_TYPES.get(image.content_type or "")
        if not ext or len(content) > 2 * 1024 * 1024:
            return back("/teacher/shop?msg=bad_image")
        image_name = f"{store.new_id('IMG')}.{ext}"
        (store.upload_dir() / image_name).write_bytes(content)
    with store.editing() as state:
        item = items_by_id(state).get(item_id)
        if item is None:
            item = {"id": store.new_id("IT"), "image": None}
            state["items"].append(item)
        item.update(
            name=name.strip()[:30], desc=desc.strip()[:60], emoji=(emoji.strip() or "🎁")[:4],
            price=max(0, min(10000, price)), limit=max(1, min(99, limit)), on_sale=bool(on_sale),
            start=start or None, end=end or None,
        )
        if image_name:
            item["image"] = image_name
        elif remove_image:
            item["image"] = None
    return back("/teacher/shop?msg=item_saved")


@app.post("/teacher/shop/items/{item_id}/delete")
def delete_item(item_id: str):
    with store.editing() as state:
        state["items"] = [i for i in state["items"] if i["id"] != item_id]
        for o in state["orders"]:
            if o["item_id"] == item_id and o["status"] == "pending":
                o["status"] = "rejected"
    return back("/teacher/shop?msg=item_deleted")


@app.post("/teacher/shop/orders/{order_id}")
def decide_order(order_id: str, decision: Annotated[str, Form()]):
    if decision not in ("approved", "rejected"):
        raise HTTPException(400, "알 수 없는 처리입니다.")
    with store.editing() as state:
        for o in state["orders"]:
            if o["id"] == order_id and o["status"] == "pending":
                o["status"] = decision
                o["decided"] = today_key()
    return back("/teacher/shop#orders")


templates.env.globals["INTENSITY"] = INTENSITY_LABELS

# 복복이 캐릭터의 몽글몽글한 테두리 (원 16개를 둘레에 배치)
templates.env.globals["FLUFF"] = [
    (round(60 + 36 * math.cos(math.radians(i * 22.5)), 2), round(66 + 34 * math.sin(math.radians(i * 22.5)), 2))
    for i in range(16)
]
