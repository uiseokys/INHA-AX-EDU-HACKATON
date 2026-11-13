"""복복복 시연용 합성 감정 기록 생성 스크립트

실행: python scripts/generate_data.py
결과: data/records.json (앱에서 사용), data/records.csv (열람·분석용)

⚠️ 모든 기록은 시연을 위해 지어낸 합성 데이터이며, 실제 학생 정보가 아닙니다.
day_offset 은 "오늘"을 0으로 한 상대 날짜입니다(-1 = 어제). 앱이 실행되는 날짜 기준으로 변환됩니다.
같은 결과가 나오도록 난수 시드를 고정했습니다.
"""

import csv
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DAYS = 35  # 오늘 포함 최근 35일

WORDS = {
    "joy": ["행복한", "신나는", "뿌듯한", "설레는", "즐거운", "고마운", "활기찬", "자랑스러운"],
    "calm": ["편안한", "차분한", "여유로운", "안심되는", "만족스러운", "포근한", "느긋한", "홀가분한"],
    "sad": ["속상한", "외로운", "서운한", "우울한", "허전한", "그리운", "실망한", "눈물 나는"],
    "anxious": ["걱정되는", "긴장되는", "두려운", "초조한", "막막한", "눈치 보이는", "불편한", "조마조마한"],
    "angry": ["짜증나는", "억울한", "답답한", "화나는", "분한", "미운", "질투 나는", "귀찮은"],
}

NOTES = {
    "daily": ["급식에 좋아하는 메뉴가 나왔다", "체육 시간에 피구를 했다", "동아리에서 새 활동을 시작했다", "친구랑 매점에 갔다",
              "주말에 가족이랑 산책했다", "발표를 무사히 끝냈다", "좋아하는 노래를 들으며 등교했다", "", "", ""],
    "study": ["수학 쪽지시험을 망쳤다", "학원 숙제가 너무 많다", "시험 범위가 너무 넓다", "성적 얘기만 들으면 숨이 막힌다",
              "수행평가가 한꺼번에 몰렸다", "공부해도 점수가 안 오른다", ""],
    "peer": ["단톡에서 나만 빼고 약속을 잡은 것 같다", "점심시간에 혼자 있었다", "친구가 내 말을 무시했다",
             "모둠 활동 때 내 의견은 그냥 넘어갔다", "쉬는 시간에 애들이 내 얘기를 하는 것 같아 눈치 보였다", ""],
    "home": ["엄마랑 핸드폰 때문에 다퉜다", "집에서 말이 안 통하는 느낌", "아빠가 성적 얘기를 또 꺼냈다", "동생이랑 싸워서 혼났다", ""],
    "sleep": ["잠을 잘 못 잤다", "아침에 일어나기 너무 힘들었다", ""],
}


def pick(rng, items, k=None):
    k = k or rng.choice([1, 1, 2, 2, 3])
    return rng.sample(items, k=min(k, len(items)))


def record(rng, emotion, topic="daily", share_rate=0.3):
    note = rng.choice(NOTES[topic])
    return {"emotion": emotion, "words": pick(rng, WORDS[emotion]), "note": note, "shared": bool(note) and rng.random() < share_rate}


def mix(rng, weights):
    """{감정: 가중치} 에서 하나 고르기"""
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def scenario(sid, rng):
    """학생별 시나리오: day_offset → 기록 (없으면 None)"""
    out = {}
    for off in range(-(DAYS - 1), 1):
        recent = off >= -6  # 최근 7일
        skip = 0.12
        rec = None

        if sid == "S01":  # 시연용 학생: 평소 무난 → 최근 또래 관계로 불안·슬픔 증가. 오늘은 비워 둠
            if off == 0:
                continue
            if recent:
                e = mix(rng, {"anxious": 3, "sad": 2, "calm": 2, "joy": 1})
                rec = record(rng, e, "peer" if e != "calm" else "daily", share_rate=0.0)
            else:
                rec = record(rng, mix(rng, {"joy": 4, "calm": 4, "anxious": 1}), share_rate=0.0)
        elif sid == "S02":  # 대체로 안정적이고 밝음
            rec = record(rng, mix(rng, {"joy": 5, "calm": 4, "angry": 1}), share_rate=0.5)
        elif sid == "S03":  # 학업 스트레스로 불안이 반복
            e = mix(rng, {"anxious": 5, "calm": 2, "angry": 1, "joy": 1})
            rec = record(rng, e, "study" if e in ("anxious", "angry") else "daily", share_rate=0.6)
        elif sid == "S04":  # 또래 관계 어려움이 길게 이어지고 최근 더 무거워짐
            if off >= -9:
                e = mix(rng, {"sad": 6, "anxious": 3})
                rec = record(rng, e, "peer", share_rate=0.4)
                if off == -2:
                    rec["note"] = "쉬는 시간마다 애들이 툭툭 치고 간다. 학교 가기 싫다"
                    rec["shared"] = False
            else:
                rec = record(rng, mix(rng, {"calm": 3, "sad": 2, "joy": 1}), "peer", share_rate=0.4)
        elif sid == "S05":  # 기록이 드문드문
            skip = 0.8
            rec = record(rng, mix(rng, {"calm": 3, "joy": 1, "sad": 1}))
        elif sid == "S06":  # 평소 밝다가 최근 갑자기 달라짐 (챗봇 위험 신호도 있음)
            if recent:
                rec = record(rng, mix(rng, {"sad": 5, "anxious": 2}), "sleep", share_rate=0.0)
            else:
                rec = record(rng, mix(rng, {"joy": 5, "calm": 4}), share_rate=0.3)
        elif sid == "S07":  # 가족 갈등으로 분노가 반복
            e = mix(rng, {"angry": 4, "calm": 3, "sad": 1, "joy": 1})
            rec = record(rng, e, "home" if e in ("angry", "sad") else "daily", share_rate=0.5)
        elif sid == "S08":  # 차분하고 안정적
            rec = record(rng, mix(rng, {"calm": 6, "joy": 2, "anxious": 1}), share_rate=0.2)
        elif sid == "S09":  # 힘들었다가 점점 회복 중
            if off < -17:
                rec = record(rng, mix(rng, {"sad": 4, "anxious": 2, "calm": 1}), "peer", share_rate=0.5)
            else:
                rec = record(rng, mix(rng, {"calm": 4, "joy": 3, "sad": 1}), share_rate=0.5)
        elif sid == "S10":  # 밝고 활기참
            rec = record(rng, mix(rng, {"joy": 6, "calm": 3}), share_rate=0.4)
        elif sid == "S11":  # 감정 기복이 있지만 큰 변화는 없음
            e = mix(rng, {"joy": 3, "calm": 2, "anxious": 2, "angry": 1, "sad": 1})
            rec = record(rng, e, "study" if e == "anxious" else "daily", share_rate=0.3)
        elif sid == "S12":  # 무난함, 시험 기간에만 살짝 긴장
            e = mix(rng, {"calm": 4, "joy": 3, "anxious": 2 if -14 <= off <= -8 else 0})
            rec = record(rng, e, "study" if e == "anxious" else "daily", share_rate=0.3)

        forced = (off == 0 and sid != "S05") or (sid == "S04" and off == -2)  # 시연에 꼭 필요한 기록
        if rec and (rng.random() >= skip or forced):
            out[off] = rec
    return out


def main() -> None:
    logs = []
    for i in range(1, 13):
        sid = f"S{i:02d}"
        rng = random.Random(f"bokbok-{sid}")
        for off, rec in sorted(scenario(sid, rng).items()):
            logs.append({"student_id": sid, "day_offset": off, **rec})

    (DATA_DIR / "records.json").write_text(
        json.dumps(
            {"_notice": "시연용 합성 데이터입니다. 실제 학생 정보가 아닙니다. scripts/generate_data.py 로 생성됩니다.", "records": logs},
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    with (DATA_DIR / "records.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["student_id", "day_offset", "emotion", "words", "note", "shared_with_teacher"])
        for r in logs:
            w.writerow([r["student_id"], r["day_offset"], r["emotion"], "|".join(r["words"]), r["note"], int(r["shared"])])
    print(f"합성 감정 기록 {len(logs)}건 생성 → data/records.json, data/records.csv")


if __name__ == "__main__":
    main()
