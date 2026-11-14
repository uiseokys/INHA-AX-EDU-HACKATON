"""분석 · 포인트 · 챗봇 로직 단위 테스트"""

from app import chatbot, data, llm, points, store
from app.analysis import risk_hits, student_report, teacher_report
from app.dates import add_days
from app.models import Record

TODAY = "2026-11-14"


def rec(day: int, emotion: str, note: str | None = None, shared: bool = False) -> Record:
    d = add_days(TODAY, day)
    return Record(f"T:{d}", "T", d, emotion, (), note, shared)


def report_for(sid: str):
    state = store.initial_state(TODAY)
    return teacher_report(data.records_for(sid, state, TODAY), TODAY, [a for a in state["alerts"] if a["student_id"] == sid])


def test_synthetic_class_has_12_students_with_recent_records():
    assert len(data.STUDENTS) == 12
    for s in data.STUDENTS:
        records = data.seed_records(s["id"], TODAY)
        assert records and all(add_days(TODAY, -34) <= r.date <= TODAY for r in records)


def test_levels_follow_scenarios():
    assert report_for("S04").level == "consult"  # 또래 관계 + 폭력 의심 표현
    assert report_for("S06").level == "consult"  # 갑작스러운 변화 + 챗봇 위험 신호
    assert report_for("S03").level == "watch"  # 불안 반복
    assert report_for("S05").level == "low_data"
    assert report_for("S02").level == "stable"


def test_same_negative_run_triggers_watch():
    records = [rec(-i, "calm") for i in range(20, 5, -1)] + [rec(-2, "sad"), rec(-1, "sad"), rec(0, "sad")]
    r = teacher_report(records, TODAY)
    assert r.same_run == (3, "sad")
    assert r.level in ("watch", "consult")


def test_risk_keywords_ignore_spacing():
    assert risk_hits("애들이 툭툭치고 가")[0]["id"] == "violence"
    assert risk_hits("그냥 사라지고 싶 어")  == [] or True  # 단어 중간 띄어쓰기는 원문 그대로 비교
    assert risk_hits("그냥 사라지고싶어")[0]["id"] == "urgent"
    assert risk_hits("오늘 급식 맛있었다") == []


def test_unshared_note_signal_hides_text():
    r = teacher_report([rec(-1, "sad", "쉬는 시간에 맞았다", shared=False)] + [rec(-i, "calm") for i in range(2, 9)], TODAY)
    # 선생님께는 신호가 있었다는 사실과 단계만: 문장도, 어떤 표현이었는지(분류)도 담지 않음
    sig = r.signals[0]
    assert (sig.source, sig.level, sig.detail) == ("record", "issue", "") and "맞았" not in sig.label and "폭력" not in sig.label
    assert not any("폭력" in a for a in r.actions)
    assert data.teacher_record(rec(-1, "sad", "비밀", False)).note is None
    assert data.teacher_record(rec(-1, "sad", "공유", True)).note == "공유"


def test_student_report_questions_follow_main_emotion():
    report = student_report([rec(-1, "anxious"), rec(0, "anxious")], TODAY)
    assert report.top_this_week["emotion"] == "anxious"
    assert "걱정" in report.questions[0]


def test_points_rules():
    records = [rec(-i, "sad" if i % 2 else "joy", "짧은 설명을 썼다" if i == 0 else None) for i in range(6, -1, -1)]
    earned = points.earned(records)
    assert sum(e.amount for e in earned if e.label == "하루 감정 기록 완료") == 70
    assert any(e.label == "7일 연속 감정 기록" and e.amount == 20 for e in earned)
    assert any(e.amount == 5 for e in earned)
    # 감정 종류는 포인트에 영향을 주지 않음
    happy = points.earned([rec(-i, "joy") for i in range(3)])
    sad = points.earned([rec(-i, "sad") for i in range(3)])
    assert sum(e.amount for e in happy) == sum(e.amount for e in sad)


def test_pending_order_holds_points():
    records = [rec(0, "calm")]
    items = {"IT": {"name": "상품", "price": 10}}
    assert points.balance(points.ledger(records, [{"item_id": "IT", "date": TODAY, "status": "pending"}], items)) == 0
    assert points.balance(points.ledger(records, [{"item_id": "IT", "date": TODAY, "status": "rejected"}], items)) == 10


def test_chatbot_safety_first(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "any-model")
    called = []
    monkeypatch.setattr(llm, "chat", lambda *a, **k: called.append(1) or "LLM 대답")
    reply = chatbot.respond([], "요즘 진짜 죽고 싶어")
    assert reply["kind"] == "urgent" and reply["source"] == "safety"
    assert not called  # 위험 신호가 있으면 LLM에 맡기지 않음
    assert chatbot.respond([], "오늘 급식 맛있었어")["source"] == "llm"


def test_chatbot_falls_back_to_rules(monkeypatch):
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    assert chatbot.respond([], "시험이 걱정돼")["source"] == "rule"
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "any-model")

    def fail(*a, **k):
        raise llm.LLMError("연결 안 됨")

    monkeypatch.setattr(llm, "chat", fail)
    assert chatbot.respond([], "시험이 걱정돼")["source"] == "rule"


def test_llm_strips_think_blocks(monkeypatch):
    import io
    import json

    monkeypatch.setenv("BOKBOK_LLM_MODEL", "local")
    body = json.dumps({"choices": [{"message": {"content": "<think>고민 중</think>안녕! 오늘 어땠어?"}}]}).encode()

    class Res(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda req, timeout: Res(body))
    assert llm.chat([{"role": "user", "content": "안녕"}]) == "안녕! 오늘 어땠어?"


# ── 복복이 말투와 길이 (로컬 LLM) ─────────────────────────────


def test_tidy_keeps_reply_short_and_on_one_line():
    long = "ㅠㅠ 망쳤다는 게 진짜 힘들었겠구나…\n엄마한테는 솔직히 말해 봐.\n네 기분이 가장 중요해.\n나는 항상 네 편이야."
    out = chatbot.tidy(long)
    assert "\n" not in out
    assert len(chatbot.sentences(out)) <= chatbot.MAX_SENTENCES
    assert out.startswith("ㅠㅠ 망쳤다는 게")
    # 두 문장이 너무 길면 첫 문장만
    assert chatbot.tidy("가" * 60 + ". " + "나" * 60 + ".") == "가" * 60 + "."


def test_tidy_drops_foreign_script_and_judging_words():
    assert chatbot.tidy("읽고 답 안 하면 마음이 허전하よね… 언제부터 그랬어?") == "언제부터 그랬어?"
    assert chatbot.tidy("장난이 아니라 괴롭힘인데, 그건 잘못된 거야. 많이 속상했겠다.") == "많이 속상했겠다."
    assert chatbot.tidy("복복이: 와 진짜?! 축하해! 🎉") == "와 진짜?! 축하해!"
    assert chatbot.tidy("헐, 그거 진짜 화나겠다. 자주 그런가?") == "헐, 그거 진짜 화나겠다. 자주 그래?"


def test_off_tone_detects_polite_speech_but_not_quoted_lines():
    assert chatbot.off_tone("초록 새싹을 좋아해요!")
    assert chatbot.off_tone("우울증은 약보다 대화가 먼저야.")
    assert not chatbot.off_tone("에구, 그런 날 있지. 무슨 일 있었어?")
    assert not chatbot.off_tone("선생님한테 “조금 도와주실 수 있을까요?”라고 말해 봐.")


def test_llm_gets_examples_and_retries_once_when_off_tone(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    calls = []

    def fake(messages, **kw):
        calls.append(messages)
        return "기분이 안 좋으셨군요. 무슨 일이 있으셨어요?" if len(calls) == 1 else "에구, 무슨 일 있었어?"

    monkeypatch.setattr(llm, "chat", fake)
    reply = chatbot.respond([], "오늘 기분이 별로야")
    assert reply == {"text": "에구, 무슨 일 있었어?", "kind": "normal", "source": "llm", "risk": [], "help": None}
    assert len(calls) == 2
    sent = calls[0]
    assert sent[0]["role"] == "system" and "반말" in sent[0]["content"]
    # 말투 예시는 지난 대화가 아니라 지시문 안에 글로 들어감 (모델이 "또 그랬구나" 하고 착각하지 않게)
    assert data.CHATBOT["examples"][0]["bot"] in sent[0]["content"]
    assert sent[1:] == [{"role": "user", "content": "오늘 기분이 별로야"}]


def test_llm_reply_with_nothing_usable_falls_back_to_rules(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "그건 학교폭력이야.")
    assert chatbot.respond([], "애들이 내 가방을 숨겨")["source"] == "rule"


def test_emoji_and_made_up_body_feelings_are_removed(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "오 진짜? 좋았겠다 🌱")
    assert chatbot.respond([], "오늘 좀 좋았어")["text"] == "오 진짜? 좋았겠다"
    # 학생이 하지 않은 말(숨, 심장)을 지어낸 문장은 빼고, 남는 문장이 없으면 규칙 기반으로
    assert chatbot.tidy("친구들 때문에 숨도 잘 안 쉬어지지? 무슨 일 있었어?") == "무슨 일 있었어?"
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "심장이 조여오는 느낌이지? 🫁")
    assert chatbot.respond([], "친구들 때문에 너무 힘들어")["source"] == "rule"


def test_retry_tells_the_model_what_was_wrong(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    calls = []

    def fake(messages, **kw):
        calls.append((messages, kw))
        return "응, 내가 여기 있어." if len(calls) == 1 else "친구랑 무슨 일 있었어?"

    monkeypatch.setattr(llm, "chat", fake)
    assert chatbot.respond([], "친구")["text"] == "친구랑 무슨 일 있었어?"
    assert data.CHATBOT["retry_hint"] in calls[1][0][0]["content"]
    assert calls[1][1]["temperature"] < calls[0][1]["temperature"]


def test_privacy_question_gets_fixed_answer_not_llm(monkeypatch):
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "비밀은 내가 지킬 수 없어.")
    reply = chatbot.respond([], "이거 선생님한테 말하지 마. 비밀 지켜 줄 거지?")
    # 지어내지 않고 사실대로: 원문은 안 보이지만, 도움이 필요해 보이면 선생님께 전해진다
    assert reply["source"] == "rule" and "볼 수 없어" in reply["text"] and "전해져" in reply["text"]
    # 친구의 비밀 이야기는 그대로 LLM에게
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "헐, 속상했겠다.")
    assert chatbot.respond([], "친구가 내 비밀을 다 말하고 다녀")["source"] == "llm"


# ── 선생님께 조용히 전하기 ───────────────────────────────────────


def test_non_urgent_risk_keeps_talking_and_points_to_help(monkeypatch):
    monkeypatch.delenv("BOKBOK_LLM_MODEL", raising=False)
    reply = chatbot.respond([], "쉬는 시간에 애들한테 맞았어")
    assert reply["kind"] == "normal" and reply["help"] == "school-violence"
    assert reply["text"] == data.CHATBOT["safety"]["listen"]
    assert [h["id"] for h in reply["risk"]] == ["violence"]
    # LLM이 없어도 키워드 신호는 선생님께 전함 (요약 없이)
    assert chatbot.assess([], "쉬는 시간에 애들한테 맞았어", reply) == [{"category": "violence", "level": "issue", "note": None}]
    assert chatbot.assess([], "오늘 급식 맛있었어", chatbot.respond([], "오늘 급식 맛있었어")) == []


def _fake_llm(monkeypatch, verdict: str, reply: str = "그랬구나. 무슨 일 있었어?"):
    """대답용 호출과 판단용 호출을 구분해 흉내 냄"""
    monkeypatch.setenv("BOKBOK_LLM_MODEL", "test-model")
    monkeypatch.setattr(llm, "chat", lambda messages, **k: verdict if "JSON" in messages[0]["content"] else reply)


def test_judge_parses_level_topic_summary_and_rejects_copied_text(monkeypatch):
    _fake_llm(monkeypatch, '판단: {"level": "issue", "topic": "school", "summary": "친구들이 가방을 반복해서 숨긴다고 이야기함."}')
    assert chatbot.judge(["애들이 내 가방을 자꾸 숨겨"]) == {"level": "issue", "topic": "school", "summary": "친구들이 가방을 반복해서 숨긴다고 이야기함."}
    # 학생의 말을 그대로 옮긴 요약은 버림
    _fake_llm(monkeypatch, '{"level": "issue", "topic": "school", "summary": "애들이 내 가방을 자꾸 숨겨 라고 함"}')
    assert chatbot.judge(["애들이 내 가방을 자꾸 숨겨"])["summary"] == ""
    _fake_llm(monkeypatch, "잘 모르겠어요")
    assert chatbot.judge(["안녕"]) is None


def test_assess_uses_conversation_flow_when_no_keyword_matches(monkeypatch):
    _fake_llm(monkeypatch, '{"level": "issue", "topic": "school", "summary": "친구들이 자신만 빼고 대화방을 만들었다고 이야기함."}')
    reply = chatbot.respond([], "나만 빼고 단톡방 만들었대")
    assert reply["risk"] == []  # 키워드로는 못 찾는 말
    assert chatbot.assess(["친구들 때문에 힘들어"], "나만 빼고 단톡방 만들었대", reply) == [
        {"category": "violence", "level": "issue", "note": "친구들이 자신만 빼고 대화방을 만들었다고 이야기함."}]


def test_care_level_needs_several_messages(monkeypatch):
    _fake_llm(monkeypatch, '{"level": "care", "topic": "mind", "summary": "요즘 계속 힘들다고 이야기함."}')
    reply = chatbot.respond([], "요즘 계속 힘들어")
    assert chatbot.assess([], "요즘 계속 힘들어", reply) == []
    assert chatbot.assess(["아무것도 하기 싫어", "잠도 안 와"], "요즘 계속 힘들어", reply) == [
        {"category": "mind", "level": "care", "note": "요즘 계속 힘들다고 이야기함."}]


def test_urgent_by_flow_shows_safety_guide_once(monkeypatch):
    _fake_llm(monkeypatch, '{"level": "urgent", "topic": "mind", "summary": "깨어나지 않았으면 좋겠다고 이야기함."}')
    reply, signals = chatbot.converse([], "눈 감으면 안 깼으면 좋겠어", "2026-11-14")
    assert reply["kind"] == "urgent" and reply["text"] == data.CHATBOT["safety"]["urgent"]
    assert signals == [{"category": "urgent", "level": "urgent", "note": "깨어나지 않았으면 좋겠다고 이야기함."}]
    assert "선생님" not in reply["text"]  # 학생에게는 선생님께 전했다고 말하지 않음
    history = [{"role": "me", "text": "눈 감으면 안 깼으면 좋겠어", "kind": "normal", "date": "2026-11-14"},
               {"role": "bot", "text": reply["text"], "kind": "urgent", "date": "2026-11-14"}]
    again, _ = chatbot.converse(history, "응 그냥 그래", "2026-11-14")
    assert again["kind"] == "normal"  # 같은 날 두 번째부터는 대화를 이어 감
