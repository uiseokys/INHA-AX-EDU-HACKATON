"""복복복 FastAPI 앱: 라우트와 화면 렌더링

실행: uvicorn app.main:app --reload
화면은 Jinja 템플릿(app/templates)으로 서버에서 그리고, 버튼은 대부분 폼 전송(POST → 리다이렉트)으로 동작합니다.
챗봇만 자바스크립트로 새로고침 없이 대화하고, 자바스크립트가 꺼져 있으면 폼 전송으로 동작합니다.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from . import chatbot, charts, data, points, store
from .analysis import describe_change, fmt, risk_hits, student_report, teacher_report
from .data import ME_ID
from .dates import add_days, day_label, full_label, month_days, relative_label, today_key, weekday
from .models import BOT_NAME, EMOTIONS, FOLLOWUP, LEVEL_ORDER, LEVELS, SERVICE_NAME

BASE = Path(__file__).resolve().parent

app = FastAPI(title=f"{SERVICE_NAME} 학생 마음 돌봄 플랫폼", description="시연용 프로토타입 · 합성 데이터")
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
            {"href": "/teacher/shop", "label": "상점 관리", "icon": "store"},
        ],
    },
}

TOASTS = {
    "reset": "시연 데이터를 처음 상태로 되돌렸어요",
    "profile": "기본 정보를 저장했어요",
    "booked": "상담을 신청했어요. 선생님이 확인하면 알려 드릴게요",
    "booking_cancelled": "상담 신청을 취소했어요",
    "ordered": "교환을 신청했어요. 선생님이 승인하면 사용할 수 있어요",
    "order_cancelled": "교환 신청을 취소했어요",
    "not_enough": "포인트가 부족하거나 더 교환할 수 없는 상품이에요",
    "slot_taken": "방금 다른 친구가 신청한 시간이에요. 다른 시간을 골라 주세요",
    "followup": "사후 관리 내용을 저장했어요",
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
    ctx.update(
        mode=mode,
        nav=nav,
        path=path,
        today=today,
        animate=urlparse(request.headers.get("referer", "")).path != path,
        toast=TOASTS.get(request.query_params.get("msg", "")),
        css_version=int(css.stat().st_mtime) if css.exists() else 0,
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


def add_alert(state: dict, student_id: str, source: str, category: str, summary: str) -> None:
    """교사 알림 남기기 (같은 날 같은 종류는 한 번만). 대화·문장 원문은 담지 않습니다."""
    today = today_key()
    if any(a["student_id"] == student_id and a["date"] == today and a["source"] == source and a["category"] == category
           for a in state["alerts"]):
        return
    state["alerts"].append(
        {"id": store.new_id("AL"), "student_id": student_id, "date": today, "time": now_time(), "source": source,
         "category": category, "summary": summary, "read": False}
    )


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
    target = next if next.startswith("/") and not next.startswith("//") else "/"
    return back(f"{target}?msg=reset")


# ── 학생: 기본 정보 (기획서 (1)) ──────────────────────────────────────────────

HOME_OPTIONS = ["부모님과 함께 지내요", "한 부모님과 지내요", "조부모님과 지내요", "기숙사·시설에서 지내요", "기타"]
HELPERS = ["담임 선생님", "상담 선생님", "부모님", "형제자매", "친구", "기타"]


@app.get("/student/welcome")
def welcome(request: Request, edit: str = ""):
    state = store.load()
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


# ── 학생: 홈 ─────────────────────────────────────────────────────────────────


@app.get("/student")
def student_home(request: Request, saved: str = ""):
    state, today = store.load(), today_key()
    if state["profile"] is None and not state["profile_skipped"]:
        return back("/student/welcome")
    records = data.records_for(ME_ID, state, today)
    by_date = {r.date: r for r in records}
    today_record = by_date.get(today)
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
    )


# ── 학생: 감정 기록 (기획서 (2)-1) ────────────────────────────────────────────


@app.get("/student/record")
def record_page(request: Request, e: str = ""):
    state, today = store.load(), today_key()
    existing = next((r for r in data.records_for(ME_ID, state, today) if r.date == today), None)
    return render(request, "student_record.html", mode="student", state=state, existing=existing,
                  preselect=e if e in EMOTIONS else (existing.emotion if existing else ""))


@app.post("/student/record")
def save_record(
    emotion: Annotated[str, Form()],
    words: Annotated[list[str], Form()] = [],
    note: Annotated[str, Form()] = "",
    shared: Annotated[str, Form()] = "",
):
    if emotion not in EMOTIONS:
        raise HTTPException(400, "알 수 없는 감정입니다.")
    today = today_key()
    note = note.strip()[:300]
    with store.editing() as state:
        state["my_records"] = [r for r in state["my_records"] if r["date"] != today] + [
            {"id": f"{ME_ID}:{today}", "student_id": ME_ID, "date": today, "emotion": emotion,
             "words": [w for w in words if w in EMOTIONS[emotion].words][:5], "note": note or None, "shared": bool(shared)}
        ]
        state["share_overrides"].pop(f"{ME_ID}:{today}", None)
        for hit in risk_hits(note):
            add_alert(state, ME_ID, "record", hit["id"],
                      f"감정 기록 문장에서 {hit['label']}이 감지되었어요." + ("" if shared else " 원문은 학생이 공유하지 않았습니다."))
    return back("/student?saved=1")


@app.post("/student/records/share")
def share_record(record_id: Annotated[str, Form()], shared: Annotated[str, Form()] = ""):
    with store.editing() as state:
        state["share_overrides"][record_id] = shared == "1"
    return back("/student/report#records")


# ── 학생: 감정 리포트 (기획서 (2)-2) ──────────────────────────────────────────


@app.get("/student/report")
def student_report_page(request: Request):
    state, today = store.load(), today_key()
    records = data.records_for(ME_ID, state, today)
    report = student_report(records, today)
    by_date = {r.date: r for r in records}
    return render(
        request,
        "student_report.html",
        mode="student",
        state=state,
        report=report,
        chart=charts.mood_chart(report.series, today),
        donut=charts.donut(report.ratio),
        calendar=[{"date": d, "record": by_date.get(d) if d else None} for d in month_days(today)],
        month=int(today[5:7]),
        recent=sorted(records, key=lambda r: r.date, reverse=True)[:7],
    )


# ── 학생: 복복이 (기획서 (3)) ─────────────────────────────────────────────────


def _chat_view(state: dict, today: str) -> list[dict]:
    """오늘 대화가 없으면 복복이가 먼저 인사"""
    if not any(m["date"] == today for m in state["chats"]):
        records = data.records_for(ME_ID, state, today)
        rec = next((r for r in records if r.date == today), None)
        after_negative = bool(rec and EMOTIONS[rec.emotion].negative)
        state["chats"].append({"id": store.new_id("M"), "role": "bot", "date": today, "time": now_time(),
                               "text": chatbot.greeting(after_negative, today),
                               "kind": "normal", "source": "rule"})
        return state["chats"]
    return state["chats"]


def _append_turn(state: dict, text: str) -> list[dict]:
    """학생의 말과 복복이의 대답을 대화에 추가하고, 추가된 메시지를 돌려줌"""
    today = today_key()
    history = [m for m in state["chats"] if m["role"] in ("me", "bot")]
    me = {"id": store.new_id("M"), "role": "me", "date": today, "time": now_time(), "text": text, "kind": "normal"}
    reply = chatbot.respond(history, text)
    bot = {"id": store.new_id("M"), "role": "bot", "date": today, "time": now_time(), "text": reply["text"],
           "kind": reply["kind"], "source": reply["source"]}
    state["chats"] += [me, bot]
    for hit in reply["risk"]:
        add_alert(state, ME_ID, "chat", hit["id"], f"{BOT_NAME} 대화에서 위험 신호가 감지되었어요. 대화 내용은 공개되지 않습니다.")
    return [me, bot]


@app.get("/student/chat")
def chat_page(request: Request):
    today = today_key()
    with store.editing() as state:
        messages = _chat_view(state, today)
    return render(request, "student_chat.html", mode="student", state=state, messages=messages,
                  status=chatbot.status(), suggestions=data.CHATBOT["suggestions"],
                  notice=data.CHATBOT["privacy_notice"], safety=data.CHATBOT["safety"])


@app.post("/student/chat")
def chat_send(text: Annotated[str, Form()] = ""):
    text = text.strip()[:500]
    if text:
        with store.editing() as state:
            _append_turn(state, text)
    return back("/student/chat#end")


@app.post("/api/chat")
def chat_api(request: Request, text: Annotated[str, Form()] = ""):
    """자바스크립트용: 새로 추가된 말풍선을 HTML 조각으로 돌려줌"""
    text = text.strip()[:500]
    if not text:
        return JSONResponse({"html": ""})
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
        state["chats"].append({"id": store.new_id("M"), "role": "me", "date": today, "time": now_time(),
                               "text": "응, 안전한 곳에 있어" if answer == "yes" else "아니, 안전하지 않아", "kind": "choice"})
        state["chats"].append({"id": store.new_id("M"), "role": "bot", "date": today, "time": now_time(),
                               "text": opt["reply_yes"] if answer == "yes" else opt["reply_no"],
                               "kind": "normal" if answer == "yes" else "urgent", "source": "safety"})
        if answer != "yes":
            add_alert(state, ME_ID, "chat", "unsafe", f"학생이 {BOT_NAME}에게 ‘지금 안전하지 않다’고 답했어요. 즉시 확인이 필요해요.")
    return back("/student/chat#end")


@app.post("/student/chat/clear")
def chat_clear():
    with store.editing() as state:
        state["chats"] = []
    return back("/student/chat")


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


def _taken(state: dict) -> set[str]:
    return {b["slot_id"] for b in state["bookings"] if b.get("slot_id") and b["status"] in ("requested", "confirmed")} | {
        f"{b['teacher']}|{b['date']}|{b['time']}" for b in state["bookings"] if b["status"] in ("requested", "confirmed")
    }


def _open_slots(state: dict, teacher: str, today: str) -> list[dict]:
    taken = _taken(state)
    slots = [s for s in state["slots"].get(teacher, [])
             if s["date"] >= today and s["id"] not in taken and f"{teacher}|{s['date']}|{s['time']}" not in taken]
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
    return {
        "student": student,
        "records": records,
        "report": teacher_report(records, today, alerts),
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
    entries = _ledger(student_id, state, today)
    return render(
        request,
        "teacher_student.html",
        mode="teacher",
        state=state,
        b=b,
        r=b["report"],
        change=describe_change(b["report"]),
        chart=charts.mood_chart(b["report"].series, today),
        profile=data.profile_for(student, state),
        records=[data.teacher_record(r) for r in sorted(b["records"], key=lambda r: r.date, reverse=True)[:14]],
        notes=state["followup_notes"].get(student_id, []),
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
        for a in state["alerts"]:
            if a["student_id"] == student_id:
                a["read"] = True
    return back(f"/teacher/students/{student_id}?msg=followup#followup")


# ── 선생님: 알림 (카톡 공지처럼) ───────────────────────────────────────────────


@app.get("/teacher/alerts")
def alerts_page(request: Request):
    state = store.load()
    alerts = sorted(state["alerts"], key=lambda a: (a["date"], a["time"]), reverse=True)
    return render(request, "teacher_alerts.html", mode="teacher", state=state, alerts=alerts)


@app.post("/teacher/alerts/{alert_id}/read")
def read_alert(alert_id: str, next: Annotated[str, Form()] = "/teacher/alerts"):
    with store.editing() as state:
        for a in state["alerts"]:
            if a["id"] == alert_id:
                a["read"] = True
    return back(next if next.startswith("/") and not next.startswith("//") else "/teacher/alerts")


# ── 선생님: 상담 일정 ─────────────────────────────────────────────────────────

BOOKING_STATUS = {"requested": "신청됨", "confirmed": "확정", "done": "상담 완료", "declined": "다른 시간 요청", "cancelled": "학생 취소"}
templates.env.globals["BOOKING_STATUS"] = BOOKING_STATUS


@app.get("/teacher/counsel")
def teacher_counsel(request: Request):
    state, today = store.load(), today_key()
    taken = {(b["teacher"], b["date"], b["time"]): b for b in state["bookings"] if b["status"] in ("requested", "confirmed")}
    slots = {
        t: [{**s, "booking": taken.get((t, s["date"], s["time"]))}
            for s in sorted(state["slots"].get(t, []), key=lambda s: (s["date"], s["time"])) if s["date"] >= today]
        for t in data.TEACHERS
    }
    bookings = sorted(state["bookings"], key=lambda b: (b["status"] != "requested", b["date"], b["time"]))
    return render(request, "teacher_counsel.html", mode="teacher", state=state, slots=slots, bookings=bookings,
                  times=["08:20", "12:50", "15:40", "16:20", "17:00"])


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


# 감정 기록 화면: 고른 스티커의 감정 단어만 보이게 하는 클래스
# (스타일 빌드 도구가 찾을 수 있도록 템플릿에서 조합하지 않고 그대로 적어 둠)
templates.env.globals["SHOW_WORDS"] = {
    "joy": "group-has-[#emo-joy:checked]:flex",
    "calm": "group-has-[#emo-calm:checked]:flex",
    "sad": "group-has-[#emo-sad:checked]:flex",
    "anxious": "group-has-[#emo-anxious:checked]:flex",
    "angry": "group-has-[#emo-angry:checked]:flex",
}

# 복복이 캐릭터의 몽글몽글한 테두리 (원 16개를 둘레에 배치)
templates.env.globals["FLUFF"] = [
    (round(60 + 36 * math.cos(math.radians(i * 22.5)), 2), round(66 + 34 * math.sin(math.radians(i * 22.5)), 2))
    for i in range(16)
]
