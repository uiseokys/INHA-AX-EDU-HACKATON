"""기록의 무결성 및 위변조 방지: 서버 기준 타임스탬프 · 수정/삭제 불가 로그 구조 · 원본 보존 및 해시 기록"""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import ledger, store
from app.main import app

TODAY = "2026-11-14"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKBOK_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("BOKBOK_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("BOKBOK_TODAY", TODAY)
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    c = TestClient(app)
    c.post("/student/welcome", data={"family": "엄마, 아빠", "satisfaction": "4", "helpers": ["담임 선생님"]})
    return c


def kinds() -> list[str]:
    return [e["kind"] for e in ledger.entries()]


def rewrite(change) -> None:
    """보존 기록 파일을 몰래 고치는 상황을 흉내 냄"""
    lines = [json.loads(line) for line in ledger.path().read_text(encoding="utf-8").splitlines()]
    lines = change(lines)
    ledger.path().write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in lines), encoding="utf-8")


# ── 서버 기준 타임스탬프 ──────────────────────────────────────────


def test_timestamp_comes_from_server_clock_not_from_the_request(client):
    # 브라우저가 시각을 보내도 쓰지 않고, 시연용 날짜 고정(BOKBOK_TODAY)과도 무관하게 실제 서버 시각을 찍음
    client.post("/student/record", data={"emotion": "sad", "ts": "1999-01-01T00:00:00+09:00", "created_at": "1999-01-01"})
    e = ledger.entries()[-1]
    stamped = datetime.fromisoformat(e["ts"])
    assert stamped.tzinfo is not None  # 시간대 포함
    assert abs(datetime.now().astimezone() - stamped) < timedelta(seconds=10)
    assert "1999" not in json.dumps(e)


# ── 수정/삭제 불가 로그 구조 ──────────────────────────────────────


def test_ledger_offers_no_way_to_change_or_remove_entries():
    public = [name for name in dir(ledger) if not name.startswith("_") and callable(getattr(ledger, name))]
    assert not [n for n in public if any(w in n for w in ("delete", "remove", "update", "edit", "clear", "truncate", "write"))]


def test_editing_a_record_keeps_the_earlier_version(client):
    client.post("/student/record", data={"emotion": "sad", "intensity": "4", "note": "처음 쓴 문장"})
    client.post("/student/record", data={"emotion": "calm", "intensity": "2", "note": "고쳐 쓴 문장"})
    assert [r["note"] for r in store.load()["my_records"]] == ["고쳐 쓴 문장"]  # 화면에는 고친 기록만
    versions = [e["payload"] for e in ledger.entries() if e["kind"] == "record"]
    assert [(v["emotion"], v["intensity"], v["note"]) for v in versions] == [("sad", 4, "처음 쓴 문장"), ("calm", 2, "고쳐 쓴 문장")]


def test_hiding_chat_from_the_screen_keeps_the_original(client):
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 급식에 떡볶이 나왔어"})
    client.post("/student/chat/clear", follow_redirects=False)
    assert not any(m["role"] == "me" for m in store.load()["chats"] if m["date"] == TODAY)  # 화면에서는 사라짐
    saved = [e["payload"]["text"] for e in ledger.entries() if e["kind"] == "chat"]
    assert "오늘 급식에 떡볶이 나왔어" in saved  # 원본은 남음
    assert kinds()[-1] == "chat_hide" and ledger.verify()["ok"]


def test_reset_does_not_erase_the_ledger(client):
    client.post("/student/record", data={"emotion": "sad", "note": "초기화 전 기록"})
    before = len(ledger.entries())
    client.post("/reset", data={"next": "/teacher"})
    assert store.load()["my_records"] == []
    after = ledger.entries()
    assert len(after) == before + 1 and after[-1]["kind"] == "reset"
    assert any(e["kind"] == "record" and e["payload"]["note"] == "초기화 전 기록" for e in after)


# ── 원본 보존 및 해시 기록 ────────────────────────────────────────


def test_every_kind_of_record_is_kept_in_a_hash_chain(client):
    client.post("/student/record", data={"emotion": "sad", "note": "쉬는 시간에 애들한테 맞았다"})  # 기록 + 알림
    client.post("/student/records/share", data={"record_id": f"S01:{TODAY}", "shared": "1"})
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 좀 힘들었어"})
    alert = [a for a in store.load()["alerts"] if a["student_id"] == "S01"][-1]
    client.post(f"/teacher/alerts/{alert['id']}/read")
    client.post("/teacher/students/S01/followup", data={"status": "checked", "note": "점심시간에 안부 확인"})
    assert kinds() == ["record", "alert", "share", "chat", "chat", "alert_read", "followup"]

    rows = ledger.entries()
    assert [e["seq"] for e in rows] == list(range(1, 8))
    assert rows[0]["prev"] == ledger.GENESIS
    assert all(rows[i]["prev"] == rows[i - 1]["hash"] for i in range(1, len(rows)))  # 앞줄의 해시를 이어 붙임
    assert all(e["payload_hash"] == ledger.payload_hash(e["payload"]) and e["hash"] == ledger.entry_hash(e) for e in rows)
    check = ledger.verify(store.load()["ledger_head"])
    assert check["ok"] and check["count"] == 7 and check["head"] == rows[-1]["hash"]


@pytest.mark.parametrize("tamper, problem", [
    (lambda rows: [{**rows[0], "payload": {**rows[0]["payload"], "intensity": 1}}] + rows[1:], "원본 내용"),
    (lambda rows: [{**rows[0], "ts": "2026-01-01T00:00:00+09:00"}] + rows[1:], "시각"),
    (lambda rows: [rows[0]] + rows[2:], "순번"),
    (lambda rows: [rows[1], rows[0]] + rows[2:], "순번"),
    (lambda rows: rows[:-1], "잘려 나감"),
])
def test_any_tampering_is_detected(client, tamper, problem):
    client.post("/student/record", data={"emotion": "angry", "intensity": "5", "note": "원본"})
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 좀 힘들었어"})
    assert ledger.verify(store.load()["ledger_head"])["ok"]
    rewrite(tamper)
    check = ledger.verify(store.load()["ledger_head"])
    assert not check["ok"] and problem in check["problem"]


def test_forged_entry_with_recomputed_own_hash_still_breaks_the_chain(client):
    """한 줄을 고치고 그 줄의 해시까지 다시 계산해 넣어도, 다음 줄이 기억하는 '앞줄 해시'와 어긋남"""
    client.post("/student/record", data={"emotion": "angry", "intensity": "5", "note": "원본"})
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "오늘 좀 힘들었어"})

    def forge(rows):
        first = {**rows[0], "payload": {**rows[0]["payload"], "note": "바꿔치기"}}
        first["payload_hash"] = ledger.payload_hash(first["payload"])
        first["hash"] = ledger.entry_hash(first)
        return [first] + rows[1:]

    rewrite(forge)
    check = ledger.verify()
    assert not check["ok"] and check["at"] == 2 and "연결" in check["problem"]


# ── 선생님 화면 ───────────────────────────────────────────────────


def test_teacher_page_shows_status_and_hashes_but_not_private_content(client):
    client.post("/student/record", data={"emotion": "sad", "note": "비공개 문장이야"})
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "선생님이 보면 안 되는 말"})
    page = client.get("/teacher/ledger").text
    assert "위변조 흔적이 없어요" in page and ledger.head()["hash"] in page
    assert "감정 기록" in page and "복복이 대화" in page
    assert "비공개 문장이야" not in page and "선생님이 보면 안 되는 말" not in page  # 원본은 보존하되 보여 주지 않음
    assert 'href="/teacher/ledger"' in client.get("/teacher").text

    rewrite(lambda rows: [{**rows[0], "payload": {**rows[0]["payload"], "emotion": "joy"}}] + rows[1:])
    page = client.get("/teacher/ledger").text
    assert "바뀐 흔적이 있어요" in page and "원본 내용이 기록 당시와 달라요" in page


def test_student_is_told_that_hiding_does_not_erase_the_original(client):
    client.get("/student/chat")
    client.post("/api/chat", data={"text": "안녕"})
    page = client.get("/student/chat/history").text
    assert "내 화면에서 지우기" in page and "원본은 서버에 안전하게 보존돼요" in page
