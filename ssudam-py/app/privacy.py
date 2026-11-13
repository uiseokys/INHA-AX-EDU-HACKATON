"""상담교사 화면에 전달할 기록을 공유 동의 범위로 거르는 모듈"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .models import Consent, EmotionLog


@dataclass
class TeacherView:
    logs: list[EmotionLog]  # 교사에게 보여도 되는 기록 (공유하지 않은 메모는 제거됨)
    trend_visible: bool  # 감정 변화 그래프 공유에 동의했는지
    shared_note_count: int  # 메모까지 볼 수 있는 기록 수


def teacher_view(logs: list[EmotionLog], consent: Consent) -> TeacherView:
    """교사 화면은 반드시 이 함수를 거친 기록만 사용해야 합니다.

    - 메모: 학생이 그 기록을 공유로 표시했거나, 전체 메모 공유에 동의한 경우에만 포함
    - 감정·강도: 그래프 공유에 동의한 경우 전체 포함, 아니면 공유된 기록만 포함
    """

    def note_visible(log: EmotionLog) -> bool:
        return log.shared or consent.all_notes

    visible = [
        replace(log, note=log.note if note_visible(log) else None)
        for log in logs
        if consent.trend or log.shared or (consent.all_notes and log.note)
    ]
    return TeacherView(
        logs=visible,
        trend_visible=consent.trend,
        shared_note_count=sum(1 for log in visible if log.note),
    )
