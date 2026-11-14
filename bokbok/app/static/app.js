// 복복복 화면 보조 스크립트

for (const chart of document.querySelectorAll("[data-mood-chart]")) {
  const controls = chart.querySelector("[data-chart-controls]");
  const toggles = [...controls.querySelectorAll("[data-chart-toggle]")];
  const layers = chart.querySelectorAll("[data-chart-layer]");
  const empty = chart.querySelector("[data-chart-empty]");
  const update = () => {
    const shown = new Set(toggles.filter(toggle => toggle.checked).map(toggle => toggle.dataset.chartToggle));
    for (const layer of layers) {
      const visible = layer.dataset.chartLayer.split(" ").some(name => shown.has(name));
      layer.toggleAttribute("hidden", !visible);
    }
    empty.hidden = shown.size > 0;
  };
  controls.addEventListener("change", update);
  controls.hidden = false;
  update();
}

// 1) 같은 화면에서 폼을 보내거나 조건을 바꾼 뒤에는 보던 위치로 되돌아오기
const SCROLL_KEY = "bokbok:scroll";
const rememberScroll = () => sessionStorage.setItem(SCROLL_KEY, JSON.stringify({ path: location.pathname, y: scrollY }));
document.addEventListener("submit", (e) => {
  if (!e.target.hasAttribute("data-scroll-top") && !e.target.hasAttribute("data-chat")) rememberScroll();
});
document.addEventListener("click", (e) => {
  if (e.target.closest("a[data-keep-scroll]")) rememberScroll();
});
try {
  const saved = JSON.parse(sessionStorage.getItem(SCROLL_KEY) || "null");
  sessionStorage.removeItem(SCROLL_KEY);
  if (saved && saved.path === location.pathname && !location.hash) scrollTo({ top: saved.y, behavior: "instant" });
} catch {
  // 저장소를 쓸 수 없는 환경에서는 생략
}

// 2) 스위치·선택 상자를 바꾸면 바로 저장/조회
document.addEventListener("change", (e) => {
  const el = e.target.closest("[data-autosubmit]");
  if (el && el.form) el.form.requestSubmit();
});

// 3) 안내 메시지는 잠시 뒤 사라지고, 주소의 ?msg= 표시도 지움
const toast = document.querySelector("[data-toast]");
if (toast) {
  setTimeout(() => toast.remove(), 2800);
  const url = new URL(location.href);
  url.searchParams.delete("msg");
  history.replaceState(null, "", url);
}

// 4) 전화 걸기 전 확인 창 (기획서 (4)-1: 1388 전화 연결 팝업)
const callDialog = document.getElementById("call-dialog");
document.addEventListener("click", (e) => {
  const link = e.target.closest("a[data-call]");
  if (!link || !callDialog) return;
  e.preventDefault();
  callDialog.querySelector("[data-call-number]").textContent = link.dataset.call;
  callDialog.querySelector("[data-call-name]").textContent = link.dataset.callName || "";
  callDialog.querySelector("[data-call-go]").href = `tel:${link.dataset.call}`;
  callDialog.showModal();
});
callDialog?.addEventListener("click", (e) => {
  if (e.target === callDialog || e.target.closest("[data-call-close]")) callDialog.close();
});

// 5) 오버레이 닫기 (기록 완료·복복이 권유 창)
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const close = document.querySelector("[data-overlay-close]");
  if (close) close.click();
});

// 6) 복복이 대화: 새로고침 없이 주고받기
const chatForm = document.querySelector("form[data-chat]");
const chatLog = document.getElementById("chat-log");
const scrollChat = () => chatLog?.lastElementChild?.scrollIntoView({ block: "end", behavior: "smooth" });
if (chatLog) scrollChat();

async function sendChat(text) {
  const mine = document.getElementById("tpl-me").content.cloneNode(true);
  const mineText = mine.querySelector("[data-text]");
  mineText.textContent = text;
  chatLog.append(mine);
  const typing = document.getElementById("tpl-typing").content.cloneNode(true).firstElementChild;
  chatLog.append(typing);
  scrollChat();
  try {
    const res = await fetch("/api/chat", { method: "POST", body: new URLSearchParams({ text }) });
    const { html } = await res.json();
    typing.remove();
    const holder = document.createElement("div");
    holder.innerHTML = html;
    // 서버가 욕설을 * 로 가린 말로 내 말풍선을 바꿈
    const shown = holder.querySelector("[data-role='me'] p");
    if (shown) mineText.textContent = shown.textContent;
    // 서버가 돌려준 조각에는 학생의 말도 들어 있으므로 복복이의 대답만 붙임
    holder.querySelectorAll("[data-role='bot']").forEach((el) => chatLog.append(el));
  } catch {
    typing.remove();
    chatForm.submit(); // 연결이 불안정하면 일반 폼 전송으로
  }
  scrollChat();
}

if (chatForm) {
  const input = chatForm.querySelector("[name=text]");
  chatForm.addEventListener("submit", (e) => {
    const text = input.value.trim();
    e.preventDefault();
    if (!text) return;
    input.value = "";
    sendChat(text);
  });
  document.querySelectorAll("[data-suggest]").forEach((b) =>
    b.addEventListener("click", () => {
      input.value = b.dataset.suggest;
      chatForm.requestSubmit();
    }),
  );
}

// 7) 감정 휠: 강도 고리. 값은 슬라이더(name=intensity)가 갖고, 스크립트가 없으면 슬라이더로 고릅니다
const wheelForm = document.querySelector("form[data-wheel]");
if (wheelForm) {
  const range = wheelForm.querySelector("[name=intensity]");
  const dial = wheelForm.querySelector("[data-dial]");
  const arc = dial.querySelector("[data-dial-arc]");
  const handle = dial.querySelector("[data-dial-handle]");
  const text = wheelForm.querySelector("[data-dial-text]");
  const labels = JSON.parse(dial.dataset.labels);

  const setLevel = (value) => {
    const level = Math.min(5, Math.max(1, Math.round(Number(value)) || 3));
    range.name = "intensity";
    range.value = level;
    delete dial.dataset.unset;
    dial.style.setProperty("--level", level);
    arc.setAttribute("stroke-dasharray", `${level} 5`);
    handle.textContent = level;
    text.textContent = `강도 ${level} · ${labels[level]}`;
    range.setAttribute("aria-valuetext", text.textContent);
  };

  // 아직 정하지 않은 상태: 값을 보내지 않아 '강도 없음'으로 저장됨 (건드리지 않은 3이 일부러 고른 3처럼 보이지 않게)
  const unsetText = "고리를 돌려 정해 보세요";
  const clearLevel = () => {
    range.removeAttribute("name");
    range.value = 3;
    dial.dataset.unset = "";
    arc.setAttribute("stroke-dasharray", "0 5");
    handle.textContent = "?";
    text.textContent = unsetText;
    range.setAttribute("aria-valuetext", "아직 정하지 않음");
  };

  // 고리 위의 위치 → 1~5 (시계 방향으로 72°마다 한 칸, 한 바퀴를 다 채운 맨 위가 5). 한가운데는 방향을 알 수 없어 무시
  const levelAt = (e) => {
    const box = dial.getBoundingClientRect();
    const dx = e.clientX - (box.left + box.width / 2);
    const dy = e.clientY - (box.top + box.height / 2);
    if (Math.hypot(dx, dy) < box.width * 0.1) return null;
    const deg = ((Math.atan2(dx, -dy) * 180) / Math.PI + 360) % 360;
    return Math.round(deg / 72) % 5 || 5;
  };

  dial.addEventListener("pointerdown", (e) => {
    const level = levelAt(e);
    if (level === null) return;
    e.preventDefault();
    e.target.setPointerCapture(e.pointerId);
    dial.dataset.dragging = "";
    setLevel(level);
  });
  dial.addEventListener("pointermove", (e) => {
    if (!("dragging" in dial.dataset)) return;
    const level = levelAt(e);
    // 끄는 중에 맨 위를 살짝 넘어가도 '아주 많이'(5)와 '아주 조금'(1)이 서로 뒤바뀌지 않게 함
    if (level === null || Math.abs(level - Number(range.value)) === 4) return;
    setLevel(level);
  });
  const stopDrag = () => delete dial.dataset.dragging;
  dial.addEventListener("pointerup", stopDrag);
  dial.addEventListener("pointercancel", stopDrag);
  range.addEventListener("input", () => setLevel(range.value));

  // 다시 고르기: 스티커·단어·강도 선택을 풀고, 키보드로 이어서 고를 수 있게 첫 스티커로 초점을 옮김
  wheelForm.querySelector("[data-wheel-reset]").addEventListener("click", (e) => {
    e.preventDefault();
    wheelForm.querySelectorAll("[name=emotion], [name=words]").forEach((el) => (el.checked = false));
    clearLevel();
    wheelForm.querySelector("[name=emotion]").focus();
  });

  if ("unset" in dial.dataset) clearLevel();
  else setLevel(range.value);
  wheelForm.dataset.dialReady = "";
}
