// 복복복 화면 보조 스크립트 (없어도 모든 기능은 폼 전송으로 동작합니다)

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
  mine.querySelector("[data-text]").textContent = text;
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
