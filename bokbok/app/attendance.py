"""출결 원본을 수업일 기준으로 집계합니다."""

from dataclasses import dataclass
from typing import Literal

WINDOW = 10
AttendanceStatus = Literal["present", "late", "absent", "excused"]
STATUS_LABELS: dict[AttendanceStatus, str] = {
    "present": "출석",
    "late": "지각",
    "absent": "결석",
    "excused": "사유 확인 결석",
}


@dataclass(frozen=True)
class AttendanceDay:
    date: str
    status: AttendanceStatus


@dataclass(frozen=True)
class AttendancePeriod:
    days: tuple[AttendanceDay, ...]

    @property
    def late(self) -> int:
        return sum(day.status == "late" for day in self.days)

    @property
    def absent(self) -> int:
        return sum(day.status == "absent" for day in self.days)

    @property
    def excused(self) -> int:
        return sum(day.status == "excused" for day in self.days)

    @property
    def attended(self) -> int:
        return len(self.days) - self.absent - self.excused

    @property
    def rate(self) -> int | None:
        return round(self.attended * 100 / WINDOW) if len(self.days) == WINDOW else None


@dataclass(frozen=True)
class AttendanceSummary:
    recent: AttendancePeriod
    previous: AttendancePeriod

    def rolling_rates(self) -> dict[str, int]:
        days = self.previous.days + self.recent.days
        rates = {}
        for end in range(WINDOW, len(days) + 1):
            period = AttendancePeriod(days[end - WINDOW:end])
            rates[days[end - 1].date] = period.attended * 100 // WINDOW
        return rates

    @property
    def drop(self) -> int | None:
        recent, previous = self.recent.rate, self.previous.rate
        return previous - recent if recent is not None and previous is not None else None

    @property
    def declining(self) -> bool:
        # 사유가 확인된 결석과 지각만으로는 출결 변화 신호를 만들지 않습니다.
        return (self.drop or 0) >= 20 and self.recent.absent - self.previous.absent >= 2


def attendance_summary(days: list[AttendanceDay], today: str) -> AttendanceSummary:
    completed = sorted((day for day in days if day.date <= today), key=lambda day: day.date)
    return AttendanceSummary(AttendancePeriod(tuple(completed[-WINDOW:])),
                             AttendancePeriod(tuple(completed[-2 * WINDOW:-WINDOW])))
