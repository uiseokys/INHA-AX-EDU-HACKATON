import type { EmotionId } from "./types";

export interface EmotionMeta {
  id: EmotionId;
  emoji: string;
  label: string;
  /** 마음 점수 계산용 방향값: +1(가벼움) ~ -1(무거움) */
  valence: number;
  /** 그래프 색 (파스텔) */
  color: string;
}

export const EMOTIONS: Record<EmotionId, EmotionMeta> = {
  happy: { id: "happy", emoji: "😊", label: "기뻐요", valence: 1, color: "#FFD46B" },
  calm: { id: "calm", emoji: "😌", label: "편안해요", valence: 0.6, color: "#8FD9C4" },
  soso: { id: "soso", emoji: "😐", label: "그저 그래요", valence: 0, color: "#CFCBDB" },
  tired: { id: "tired", emoji: "😮‍💨", label: "지쳤어요", valence: -0.5, color: "#A9CCF2" },
  anxious: { id: "anxious", emoji: "😟", label: "불안해요", valence: -0.8, color: "#B9ABFB" },
  sad: { id: "sad", emoji: "😢", label: "슬퍼요", valence: -1, color: "#8FB0E8" },
  angry: { id: "angry", emoji: "😠", label: "화나요", valence: -0.9, color: "#F7B08F" },
};

export const EMOTION_LIST: EmotionMeta[] = Object.values(EMOTIONS);

export const INTENSITY_LABELS = ["", "아주 약하게", "약하게", "보통", "강하게", "아주 강하게"];
