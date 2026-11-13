// 쓰담 화면 보조 스크립트 (없어도 모든 기능은 폼 전송으로 동작합니다)

// 1) 같은 화면에서 폼을 보내거나 조건을 바꾼 뒤에는 보던 위치로 되돌아오기
const SCROLL_KEY = "ssudam:scroll";
const rememberScroll = () => sessionStorage.setItem(SCROLL_KEY, JSON.stringify({ path: location.pathname, y: scrollY }));

document.addEventListener("submit", (e) => {
  if (!e.target.hasAttribute("data-scroll-top")) rememberScroll();
});
document.addEventListener("click", (e) => {
  if (e.target.closest("a[data-keep-scroll]")) rememberScroll();
});
try {
  const saved = JSON.parse(sessionStorage.getItem(SCROLL_KEY) || "null");
  sessionStorage.removeItem(SCROLL_KEY);
  if (saved && saved.path === location.pathname) scrollTo({ top: saved.y, behavior: "instant" });
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
  setTimeout(() => toast.remove(), 2600);
  const url = new URL(location.href);
  url.searchParams.delete("msg");
  history.replaceState(null, "", url);
}

// 4) Esc 로 연결 요청 창 닫기
document.addEventListener("keydown", (e) => {
  const close = document.querySelector("a[data-modal-close]");
  if (e.key === "Escape" && close) close.click();
});
