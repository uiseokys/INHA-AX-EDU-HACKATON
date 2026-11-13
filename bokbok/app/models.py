"""앱 전체에서 쓰는 자료형과 상수"""

from __future__ import annotations

from dataclasses import dataclass, field

SERVICE_NAME = "복복복"  # 서비스 이름 (기획서 표지 기준). 바꾸려면 여기만 고치면 됩니다.
BOT_NAME = "복복이"  # AI 마음 돌봄 챗봇 이름


@dataclass(frozen=True)
class Record:
    """감정 기록 한 건. date 는 'YYYY-MM-DD'"""

    id: str
    student_id: str
    date: str
    emotion: str
    words: tuple[str, ...] = ()
    note: str | None = None
    shared: bool = False  # 학생이 이 문장을 선생님께 보여 주기로 했는지


@dataclass(frozen=True)
class Emotion:
    id: str
    label: str  # 기쁨, 평온 …
    feeling: str  # 오늘은 ○○ (화면 문장용)
    color: str  # 기획서 색상
    deep: str  # 글자·테두리용 진한 색
    score: float  # 마음 점수 1(무거움)~5(가벼움)
    negative: bool
    words: tuple[str, ...] = field(default_factory=tuple)  # 스티커를 고르면 보여 줄 감정 단어


# 기획서 15쪽의 감정 색상을 그대로 사용
EMOTIONS: dict[str, Emotion] = {
    e.id: e
    for e in [
        Emotion("joy", "기쁨", "기뻐요", "#FFD66B", "#a07a10", 4.6, False,
                ("행복한", "신나는", "뿌듯한", "설레는", "즐거운", "고마운", "활기찬", "자랑스러운")),
        Emotion("calm", "평온", "편안해요", "#A9DCC5", "#2f7a5b", 4.0, False,
                ("편안한", "차분한", "여유로운", "안심되는", "만족스러운", "포근한", "느긋한", "홀가분한")),
        Emotion("sad", "슬픔", "슬퍼요", "#AFC9EE", "#3b649e", 1.8, True,
                ("속상한", "외로운", "서운한", "우울한", "허전한", "그리운", "실망한", "눈물 나는")),
        Emotion("anxious", "불안", "불안해요", "#C8B5E8", "#6a4fa3", 2.0, True,
                ("걱정되는", "긴장되는", "두려운", "초조한", "막막한", "눈치 보이는", "불편한", "조마조마한")),
        Emotion("angry", "분노", "화나요", "#F2A49B", "#a5463a", 1.6, True,
                ("짜증나는", "억울한", "답답한", "화나는", "분한", "미운", "질투 나는", "귀찮은")),
    ]
}

# 교사 화면의 학생 상태. 위험도 판정이 아니라 '선생님이 무엇을 하면 좋을지'를 나타냅니다.
LEVELS: dict[str, dict[str, str]] = {
    "consult": {"label": "상담 권장", "chip": "bg-rose-100 text-rose-800", "dot": "bg-rose-400", "tile": "bg-rose-50 text-rose-800"},
    "watch": {"label": "관찰 필요", "chip": "bg-amber-100 text-amber-800", "dot": "bg-amber-400", "tile": "bg-amber-50 text-amber-800"},
    "low_data": {"label": "기록 부족", "chip": "bg-stone-100 text-stone-600", "dot": "bg-stone-300", "tile": "bg-stone-50 text-stone-600"},
    "stable": {"label": "안정", "chip": "bg-leaf-100 text-leaf-700", "dot": "bg-leaf-400", "tile": "bg-leaf-50 text-leaf-700"},
}
LEVEL_ORDER = ["consult", "watch", "low_data", "stable"]

# 선생님이 기록하는 사후 관리 단계 (기획서 ⑥ 지속적인 사후 관리)
FOLLOWUP: dict[str, str] = {
    "none": "확인 전",
    "checked": "확인함",
    "talking": "상담 진행 중",
    "linked": "외부 기관 연계",
    "done": "관리 종료",
}
