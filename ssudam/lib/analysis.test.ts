import { describe, expect, it } from "vitest";
import { analyze, moodScore, summarize } from "./analysis";
import { agencies, logsFor, matchAgencies, seedLogs, students } from "./data";
import { addDays } from "./date";
import { teacherView } from "./privacy";
import { createInitialState } from "./store";
import type { EmotionLog } from "./types";

const TODAY = "2026-11-13";

describe("마음 점수", () => {
  it("가벼운 감정은 3점보다 높고, 무거운 감정은 3점보다 낮다", () => {
    expect(moodScore({ emotion: "happy", intensity: 5 })).toBe(5);
    expect(moodScore({ emotion: "soso", intensity: 4 })).toBe(3);
    expect(moodScore({ emotion: "sad", intensity: 5 })).toBe(1);
    expect(moodScore({ emotion: "tired", intensity: 3 })).toBeLessThan(3);
  });
});

describe("합성 데이터", () => {
  it("가상 학생 8명의 기록이 최근 14일 안에 있다", () => {
    expect(students).toHaveLength(8);
    for (const s of students) {
      const logs = seedLogs(s.id, TODAY);
      expect(logs.length).toBeGreaterThan(0);
      for (const l of logs) {
        expect(l.date >= addDays(TODAY, -13) && l.date <= TODAY).toBe(true);
      }
    }
  });
});

describe("규칙 기반 분석", () => {
  it("또래 관계 고민이 늘어난 사례(S01)에서 변화와 근거 기록을 찾는다", () => {
    const insight = analyze(seedLogs("S01", TODAY), TODAY);
    expect(insight.enough).toBe(true);
    expect(insight.change.direction).toBe("down");
    expect(insight.topics[0].id).toBe("peer");
    expect(insight.topics[0].evidence.length).toBeGreaterThanOrEqual(3);
    const shift = insight.changePoints.find((c) => c.kind === "shift");
    expect(shift?.log.note).toBeTruthy();
    expect(summarize(insight, "student").length).toBeGreaterThan(1);
  });

  it("학업 스트레스 사례(S03)의 대표 주제는 학업이다", () => {
    const insight = analyze(seedLogs("S03", TODAY), TODAY);
    expect(insight.topics[0].id).toBe("study");
  });

  it("안정적인 사례(S02)는 큰 변화가 없다고 본다", () => {
    const insight = analyze(seedLogs("S02", TODAY), TODAY);
    expect(insight.change.direction).toBe("steady");
  });

  it("기록이 적은 사례(S05)는 분석하지 않고 안내만 한다", () => {
    const insight = analyze(seedLogs("S05", TODAY), TODAY);
    expect(insight.enough).toBe(false);
    expect(summarize(insight, "student")).toHaveLength(1);
  });

  it("오늘 체크인한 기록이 그래프 마지막 점에 반영된다", () => {
    const state = createInitialState(TODAY);
    const mine: EmotionLog = {
      id: `S01:${TODAY}`,
      studentId: "S01",
      date: TODAY,
      emotion: "calm",
      intensity: 4,
      shared: false,
    };
    const before = analyze(logsFor("S01", state, TODAY), TODAY).series.at(-1);
    const after = analyze(logsFor("S01", { ...state, myLogs: [mine] }, TODAY), TODAY).series.at(-1);
    expect(before?.score).toBeNull();
    expect(after?.score).toBe(moodScore(mine));
  });
});

describe("공유 범위", () => {
  it("공유에 동의하지 않은 학생의 기록은 교사에게 전달되지 않는다", () => {
    const view = teacherView(seedLogs("S08", TODAY), { trend: false, allNotes: false });
    expect(view.logs).toHaveLength(0);
  });

  it("그래프만 공유한 경우, 공유로 표시하지 않은 메모는 제거된다", () => {
    const logs = seedLogs("S04", TODAY);
    const view = teacherView(logs, { trend: true, allNotes: false });
    expect(view.logs).toHaveLength(logs.length);
    const privateNotes = logs.filter((l) => !l.shared && l.note).map((l) => l.note);
    expect(privateNotes.length).toBeGreaterThan(0);
    for (const note of privateNotes) {
      expect(view.logs.some((l) => l.note === note)).toBe(false);
    }
  });

  it("그래프 공유에 동의하지 않으면 공유로 표시한 기록만 전달된다", () => {
    const logs = seedLogs("S06", TODAY);
    const view = teacherView(logs, { trend: false, allNotes: false });
    expect(view.trendVisible).toBe(false);
    expect(view.logs).toHaveLength(logs.filter((l) => l.shared).length);
  });
});

describe("지원기관 추천", () => {
  it("유형과 지역 조건으로 걸러지고, 학생 주제와 맞는 기관이 앞에 온다", () => {
    const result = matchAgencies(agencies, { type: "wee-center", region: "all" }, ["peer"]);
    expect(result.length).toBeGreaterThan(0);
    expect(result.every((r) => r.agency.type === "wee-center")).toBe(true);
    expect(result[0].matchedTopics).toContain("peer");
  });
});
