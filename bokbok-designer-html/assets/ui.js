// 서버 없이 화면을 확인하기 위한 시연 동작입니다.
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

// 2) 스위치·선택 상자를 바꾸면 바로 저장/조회
document.addEventListener("change", (e) => {
  const el = e.target.closest("[data-autosubmit]");
  if (el && el.form) el.form.requestSubmit();
});

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

// HTML 시연은 실제 서버에 데이터를 보내지 않습니다.
const previewPage = document.body.dataset.previewPage;
const previewStatus = document.createElement("div");
previewStatus.className = "fixed inset-x-0 bottom-24 z-50 mx-auto w-fit max-w-[90vw] animate-pop rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white shadow-xl md:bottom-10";
previewStatus.setAttribute("role", "status");
let statusTimer;

function showPreviewStatus(message) {
  previewStatus.textContent = message;
  document.body.append(previewStatus);
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => previewStatus.remove(), 2800);
}

const toast = document.querySelector("[data-toast]");
if (toast) setTimeout(() => toast.remove(), 2800);

const callButton = document.querySelector("[data-call-go]");
callButton?.addEventListener("click", (event) => {
  event.preventDefault();
  callDialog.close();
  showPreviewStatus("미리보기에서는 실제 전화를 걸지 않아요.");
});

const chatForm = document.querySelector("[data-chat]");
const chatLog = document.getElementById("chat-log");
const chatInput = document.getElementById("chat-input");
const scrollToChatEnd = () => chatLog?.lastElementChild?.scrollIntoView({ block: "end", behavior: "smooth" });
if (chatLog) scrollToChatEnd();

function previewChat(text) {
  const mine = document.getElementById("tpl-me").content.cloneNode(true);
  mine.querySelector("[data-text]").textContent = text;
  chatLog.append(mine);
  const typing = document.getElementById("tpl-typing").content.firstElementChild.cloneNode(true);
  chatLog.append(typing);
  chatInput.value = "";
  scrollToChatEnd();
  setTimeout(() => {
    const reply = document.getElementById("tpl-preview-reply").content.cloneNode(true);
    typing.replaceWith(reply);
    scrollToChatEnd();
  }, 650);
}

document.querySelectorAll("[data-suggest]").forEach((button) => {
  button.addEventListener("click", () => {
    chatInput.value = button.dataset.suggest;
    chatForm.requestSubmit();
  });
});

const destinations = {
  "/reset": "landing-reset",
  "/student/record": "student-record-saved",
  "/student/record/later": "student-home-unrecorded",
  "/student/chat/clear": "student-chat",
  "/student/counsel": "student-counsel-booked",
  "/teacher/counsel/slots": "teacher-counsel-slot-added",
  "/teacher/shop/items": "teacher-shop-item-saved",
};

function targetFor(action, values) {
  switch (action) {
    case "/student/promise":
      if (previewPage === "student-promise-first" || previewPage === "student-promise-required") return "student-welcome";
      return values.get("today_emotion") ? "student-record-saved" : "student-home";
    case "/student/welcome":
      return previewPage === "student-welcome-edit" ? "student-home" : "student-record";
    case "/student/chat/today-emotion":
      return previewPage === "student-record-saved-locked" ? "student-promise-today-emotion" : "student-chat-today-emotion#end";
    case "/student/chat/safety":
      return (values.get("answer") === "yes" ? "student-chat-safe-answer" : "student-chat-unsafe-answer") + "#end";
    case "/student/records/share":
      return (values.get("shared") === "1" ? "student-report" : "student-report-private") + "#records";
    default:
      return destinations[action];
  }
}

const patterns = [
  [/^\/student\/counsel\/[^/]+\/cancel$/, "student-counsel-cancelled"],
  [/^\/student\/shop\/orders\/[^/]+\/cancel$/, "student-shop-cancelled"],
  [/^\/student\/shop\/[^/]+$/, "student-shop-ordered"],
  [/^\/teacher\/students\/[^/]+\/shares$/, "teacher-student-share-saved#shares"],
  [/^\/teacher\/students\/[^/]+\/followup$/, "teacher-student-followup-saved#followup"],
  [/^\/teacher\/shop\/items\/[^/]+\/delete$/, "teacher-shop-item-deleted"],
  [/^\/teacher\/alerts\/[^/]+\/read$/, "teacher-alerts-read"],
];

document.addEventListener("submit", (event) => {
  const form = event.target;
  const action = form.dataset.previewAction;
  if (!action) return;
  event.preventDefault();
  const values = new FormData(form);
  if (event.submitter?.name) values.set(event.submitter.name, event.submitter.value);
  if (action === "/student/chat") {
    const text = values.get("text").trim();
    if (text) previewChat(text);
    return;
  }
  let destination = targetFor(action, values) || patterns.find(([pattern]) => pattern.test(action))?.[1];
  if (action.startsWith("/teacher/counsel/bookings/")) {
    destination = "teacher-counsel-" + values.get("status");
  }
  if (action.startsWith("/teacher/shop/orders/")) {
    destination = "teacher-shop-" + values.get("decision") + "#orders";
  }
  if (action === "/student/chat/history/delete") {
    form.closest("details").remove();
    if (!document.querySelector("form[data-preview-action='/student/chat/history/delete']")) {
      location.href = "student-chat-history-empty.html";
    }
    return;
  }
  if (destination) {
    const [screen, anchor] = destination.split("#");
    location.href = screen + ".html" + (anchor ? "#" + anchor : "");
    return;
  }
  showPreviewStatus("시연용 화면이에요. 입력한 내용은 저장되지 않아요.");
});
