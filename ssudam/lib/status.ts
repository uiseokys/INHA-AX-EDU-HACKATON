import type { CaseStatus } from "./types";

// 상태는 '위험도'가 아니라 '지원 절차의 어느 단계인지'를 나타냅니다.
export const STATUS: Record<
  CaseStatus,
  { label: string; desc: string; chip: string; dot: string; tile: string }
> = {
  requested: {
    label: "상담 요청",
    desc: "학생이 직접 상담을 요청함",
    chip: "bg-brand-100 text-brand-700",
    dot: "bg-brand-400",
    tile: "bg-brand-50 text-brand-700",
  },
  review: {
    label: "변화 검토 필요",
    desc: "공유된 기록에 변화가 있어 확인 필요",
    chip: "bg-butter-100 text-amber-800",
    dot: "bg-amber-400",
    tile: "bg-butter-50 text-amber-800",
  },
  in_progress: {
    label: "지원 진행 중",
    desc: "교내 상담 진행 중",
    chip: "bg-sky-100 text-sky-800",
    dot: "bg-sky-400",
    tile: "bg-sky-50 text-sky-800",
  },
  referred: {
    label: "기관 연계 중",
    desc: "외부 지원기관과 연결함",
    chip: "bg-mint-100 text-mint-700",
    dot: "bg-mint-400",
    tile: "bg-mint-50 text-mint-700",
  },
  closed: {
    label: "지원 마무리",
    desc: "지원을 마치고 일상 기록을 이어감",
    chip: "bg-stone-100 text-stone-600",
    dot: "bg-stone-400",
    tile: "bg-stone-50 text-stone-600",
  },
  none: {
    label: "일상 기록 중",
    desc: "진행 중인 지원 절차 없음",
    chip: "bg-stone-100 text-stone-500",
    dot: "bg-stone-300",
    tile: "bg-stone-50 text-stone-600",
  },
};

export const STATUS_ORDER: CaseStatus[] = ["requested", "review", "in_progress", "referred", "closed", "none"];
