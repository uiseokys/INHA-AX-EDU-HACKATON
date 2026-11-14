// 브라우저에 그려진 화면을 편집 가능한 SVG로 바꾸는 변환기 (Figma 가져오기용)
// 박스(배경·테두리·모서리·그림자) → <rect>, 글자 → <text>, 아이콘·캐릭터 → <svg>
// 화면 구조를 따라 <g id="이름"> 으로 묶어 Figma 레이어 이름이 되도록 합니다.
// export_figma_svg.py 가 화면 HTML에 붙여 실행하고, 결과를 부모 창으로 보냅니다.
(() => {
  const FONT = "Noto Sans KR"; // Figma에서 바로 편집할 수 있는 한글 글꼴 (웹은 Pretendard)
  const r1 = (n) => Math.round(n * 10) / 10;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  // 어떤 CSS 색이든(oklch 등) sRGB로 바꾸기: 1px 캔버스에 칠해 읽음
  const cvs = document.createElement("canvas");
  cvs.width = cvs.height = 1;
  const ctx = cvs.getContext("2d", { willReadFrequently: true });
  const cache = new Map();
  function color(c) {
    if (!c || c === "transparent" || c === "none") return null;
    if (cache.has(c)) return cache.get(c);
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = "#000";
    ctx.fillStyle = c;
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
    const out = a === 0 ? null : { hex: "#" + [r, g, b].map((x) => x.toString(16).padStart(2, "0")).join(""), a: r1(a / 255) };
    cache.set(c, out);
    return out;
  }
  const fillAttr = (c, name = "fill") => (c ? ` ${name}="${c.hex}"${c.a < 1 ? ` ${name}-opacity="${c.a}"` : ""}` : ` ${name}="none"`);

  const defs = [];
  let uid = 0;

  function gradient(bgImage) {
    if (!bgImage || !bgImage.startsWith("linear-gradient")) return null;
    const inner = bgImage.slice(bgImage.indexOf("(") + 1, bgImage.lastIndexOf(")"));
    const dir = (inner.match(/^to [a-z ]+/) || ["to bottom"])[0];
    const stops = inner.match(/(?:rgba?|oklch|oklab|hsla?|color|lab|lch)\([^()]*(?:\([^()]*\)[^()]*)*\)|#[0-9a-fA-F]{3,8}/g) || [];
    const cols = stops.map(color).filter(Boolean);
    if (cols.length < 2) return null;
    const v = { x1: 0, y1: 0, x2: 0, y2: 1 };
    if (dir.includes("right")) v.x2 = 1;
    if (dir.includes("left")) { v.x1 = 1; v.x2 = 0; }
    if (dir.includes("top")) { v.y1 = 1; v.y2 = 0; }
    if (!dir.includes("bottom") && !dir.includes("top")) v.y2 = 0;
    const id = "g" + uid++;
    defs.push(`<linearGradient id="${id}" x1="${v.x1}" y1="${v.y1}" x2="${v.x2}" y2="${v.y2}">` +
      cols.map((c, i) => `<stop offset="${r1(i / (cols.length - 1))}" stop-color="${c.hex}"${c.a < 1 ? ` stop-opacity="${c.a}"` : ""}/>`).join("") +
      "</linearGradient>");
    return id;
  }

  // box-shadow: 퍼짐만 있는 그림자(Tailwind ring)는 테두리로, 나머지 첫 그림자는 drop shadow 로
  function shadows(bs) {
    if (!bs || bs === "none") return { ring: null, drop: null };
    const parts = bs.split(/,(?![^()]*\))/).map((s) => s.trim());
    let ring = null, drop = null;
    for (const p of parts) {
      const col = (p.match(/(?:rgba?|oklch|oklab|color|lab|lch)\([^()]*(?:\([^()]*\)[^()]*)*\)|#[0-9a-fA-F]{3,8}/) || [])[0];
      const nums = p.replace(col || "", "").match(/-?[\d.]+px/g)?.map(parseFloat) || [];
      const [x = 0, y = 0, blur = 0, spread = 0] = nums;
      const c = color(col);
      if (!c || p.includes("inset")) continue;
      if (!x && !y && !blur && spread > 0) { if (!ring) ring = { c, w: spread }; }
      else if (!drop) drop = { c, x, y, blur, spread };
    }
    return { ring, drop };
  }
  function dropFilter(d) {
    const id = "s" + uid++;
    defs.push(`<filter id="${id}" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="${d.x}" dy="${d.y}" stdDeviation="${r1(d.blur / 2)}" flood-color="${d.c.hex}" flood-opacity="${d.c.a}"/></filter>`);
    return id;
  }

  const SKIP = new Set(["SCRIPT", "STYLE", "TEMPLATE", "NOSCRIPT", "DIALOG", "HEAD", "META", "LINK", "TITLE"]);
  const SEMANTIC = { HEADER: "헤더", NAV: "메뉴", MAIN: "본문", FOOTER: "하단", SECTION: "섹션", FORM: "입력 폼", UL: "목록", OL: "목록", LI: "항목", A: "링크", BUTTON: "버튼", LABEL: "선택지", ARTICLE: "카드", ASIDE: "곁가지", DL: "정보" };

  function nameOf(el) {
    const head = el.querySelector?.("h1,h2,h3");
    const txt = (el.getAttribute("aria-label") || (head && head.textContent) || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 24);
    const kind = SEMANTIC[el.tagName] || "박스";
    return txt ? `${kind} · ${txt}` : kind;
  }

  function boxSvg(el, cs, rect) {
    const bg = color(cs.backgroundColor);
    const grad = gradient(cs.backgroundImage);
    const bw = ["Top", "Right", "Bottom", "Left"].map((s) => parseFloat(cs[`border${s}Width`]) || 0);
    const bc = ["Top", "Right", "Bottom", "Left"].map((s) => color(cs[`border${s}Color`]));
    const { ring, drop } = shadows(cs.boxShadow);
    const hasBorder = bw.some((w, i) => w > 0 && bc[i]);
    if (!bg && !grad && !hasBorder && !ring && !drop) return "";
    let rad = parseFloat(cs.borderTopLeftRadius) || 0;
    rad = Math.min(rad, rect.width / 2, rect.height / 2);
    const x = r1(rect.left + scrollX), y = r1(rect.top + scrollY), w = r1(rect.width), h = r1(rect.height);
    let out = "";
    const allSame = bw.every((v) => v === bw[0]) && bw[0] > 0 && bc[0];
    const fill = grad ? ` fill="url(#${grad})"` : fillAttr(bg);
    const filt = drop ? ` filter="url(#${dropFilter(drop)})"` : "";
    if (bg || grad || drop) out += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r1(rad)}"${fill}${filt}/>`;
    if (allSame) {
      const s = bw[0];
      out += `<rect x="${r1(x + s / 2)}" y="${r1(y + s / 2)}" width="${r1(w - s)}" height="${r1(h - s)}" rx="${r1(Math.max(0, rad - s / 2))}" fill="none"${fillAttr(bc[0], "stroke")} stroke-width="${s}"/>`;
    } else if (hasBorder) {
      const lines = [[x, y, w, bw[0]], [x + w - bw[1], y, bw[1], h], [x, y + h - bw[2], w, bw[2]], [x, y, bw[3], h]];
      lines.forEach(([lx, ly, lw, lh], i) => { if (bw[i] > 0 && bc[i]) out += `<rect x="${r1(lx)}" y="${r1(ly)}" width="${r1(lw)}" height="${r1(lh)}"${fillAttr(bc[i])}/>`; });
    }
    if (ring) {
      const s = ring.w;
      out += `<rect x="${r1(x - s / 2)}" y="${r1(y - s / 2)}" width="${r1(w + s)}" height="${r1(h + s)}" rx="${r1(rad + s / 2)}" fill="none"${fillAttr(ring.c, "stroke")} stroke-width="${s}"/>`;
    }
    return out;
  }

  // 인라인 SVG(아이콘·캐릭터·스티커·그래프): 계산된 색을 속성으로 굳혀서 복사
  function svgCopy(el, rect) {
    const clone = el.cloneNode(true);
    const src = [el, ...el.querySelectorAll("*")];
    const dst = [clone, ...clone.querySelectorAll("*")];
    src.forEach((s, i) => {
      const d = dst[i];
      const cs = getComputedStyle(s);
      if (s !== el && ["path", "circle", "ellipse", "rect", "polyline", "polygon", "line"].includes(s.tagName)) {
        const gradFill = cs.fill.startsWith("url(");
        const f = cs.fill === "none" || gradFill ? null : color(cs.fill);
        const st = cs.stroke === "none" ? null : color(cs.stroke);
        if (!gradFill) d.setAttribute("fill", f ? f.hex : "none");
        if (f && f.a < 1) d.setAttribute("fill-opacity", f.a);
        d.setAttribute("stroke", st ? st.hex : "none");
        if (st) {
          d.setAttribute("stroke-width", parseFloat(cs.strokeWidth) || 1);
          if (st.a < 1) d.setAttribute("stroke-opacity", st.a);
        }
        if (parseFloat(cs.opacity) < 1) d.setAttribute("opacity", cs.opacity);
      }
      if (s.tagName === "stop") { const c = color(cs.stopColor); if (c) d.setAttribute("stop-color", c.hex); }
      d.removeAttribute("class");
      d.removeAttribute("style");
      d.removeAttribute("vector-effect");
    });
    // 늘어나는 그래프(viewBox 0~100, 비율 무시): 좌표를 실제 픽셀로 바꿔 선 굵기가 일그러지지 않게
    if (el.getAttribute("preserveAspectRatio") === "none") {
      const [, , vw, vh] = (el.getAttribute("viewBox") || "0 0 100 100").split(/[ ,]+/).map(Number);
      const sx = rect.width / vw, sy = rect.height / vh;
      clone.querySelectorAll("path").forEach((p) => {
        let k = 0;
        p.setAttribute("d", p.getAttribute("d").replace(/-?\d*\.?\d+(?:e-?\d+)?/g, (n) => r1(parseFloat(n) * (k++ % 2 ? sy : sx))));
      });
      clone.setAttribute("viewBox", `0 0 ${r1(rect.width)} ${r1(rect.height)}`);
      clone.removeAttribute("preserveAspectRatio");
    }
    clone.setAttribute("x", r1(rect.left + scrollX));
    clone.setAttribute("y", r1(rect.top + scrollY));
    clone.setAttribute("width", r1(rect.width));
    clone.setAttribute("height", r1(rect.height));
    clone.removeAttribute("aria-hidden");
    clone.removeAttribute("role");
    // 아이디 겹침 방지 (그라데이션 등)
    clone.querySelectorAll("[id]").forEach((n) => {
      const nid = n.id + "-" + uid++;
      clone.querySelectorAll("*").forEach((m) => {
        for (const at of ["fill", "stroke"]) if (m.getAttribute(at) === `url(#${n.id})`) m.setAttribute(at, `url(#${nid})`);
      });
      n.id = nid;
    });
    const label = el.getAttribute("aria-label");
    const wrap = `<g id="${esc(label || "아이콘")}">${new XMLSerializer().serializeToString(clone).replace(/ xmlns="[^"]*"/, "")}</g>`;
    return wrap;
  }

  // 글자: 줄마다 위치를 재서 <tspan> 으로
  const range = document.createRange();
  function textSvg(node) {
    const el = node.parentElement;
    const cs = getComputedStyle(el);
    if (parseFloat(cs.opacity) === 0) return "";
    const data = node.data;
    const lines = [];
    let cur = null;
    for (let i = 0; i < data.length; ) {
      const cp = data.codePointAt(i);
      const len = cp > 0xffff ? 2 : 1;
      range.setStart(node, i);
      range.setEnd(node, i + len);
      const r = range.getBoundingClientRect();
      const ch = data.slice(i, i + len);
      i += len;
      if (r.width === 0 && r.height === 0) continue;
      if (/\s/.test(ch) && r.width === 0) continue;
      if (!cur || Math.abs(r.top - cur.top) > r.height * 0.5) {
        cur = { top: r.top, left: r.left, h: r.height, text: "" };
        lines.push(cur);
      }
      cur.text += /\s/.test(ch) ? " " : ch;
      cur.h = Math.max(cur.h, r.height);
    }
    const fs = parseFloat(cs.fontSize);
    const c = color(cs.color) || { hex: "#000000", a: 1 };
    const ls = parseFloat(cs.letterSpacing) || 0;
    const deco = cs.textDecorationLine.includes("line-through") ? ' text-decoration="line-through"' : "";
    const out = lines
      .map((l) => ({ ...l, text: l.text.replace(/\s+/g, " ").trim() }))
      .filter((l) => l.text)
      .map((l) => `<tspan x="${r1(l.left + scrollX)}" y="${r1(l.top + scrollY + l.h * 0.8)}">${esc(l.text)}</tspan>`);
    if (!out.length) return "";
    const name = lines.map((l) => l.text).join(" ").replace(/\s+/g, " ").trim().slice(0, 40);
    return `<text id="${esc(name)}" font-family="${FONT}" font-size="${fs}" font-weight="${cs.fontWeight}"${ls ? ` letter-spacing="${ls}"` : ""}${fillAttr(c)}${deco} xml:space="preserve">${out.join("")}</text>`;
  }

  // 입력칸: 값 또는 안내 문구를 글자로
  function fieldText(el, cs, rect) {
    let txt = "", ph = false;
    if (el.tagName === "SELECT") txt = el.options[el.selectedIndex]?.text || "";
    else if (el.type === "date") txt = el.value || "연도. 월. 일.";
    else { txt = el.value; if (!txt) { txt = el.placeholder || ""; ph = true; } }
    if (!txt) return "";
    const fs = parseFloat(cs.fontSize);
    const c = ph ? { hex: "#a6a09b", a: 1 } : color(cs.color) || { hex: "#26332a", a: 1 };
    const x = rect.left + scrollX + (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.borderLeftWidth) || 0);
    const y = el.tagName === "TEXTAREA" ? rect.top + scrollY + (parseFloat(cs.paddingTop) || 0) + fs * 1.1 : rect.top + scrollY + rect.height / 2 + fs * 0.36;
    return `<text id="${esc((ph ? "안내 문구 · " : "입력값 · ") + txt.slice(0, 30))}" font-family="${FONT}" font-size="${fs}" font-weight="${cs.fontWeight}"${fillAttr(c)}><tspan x="${r1(x)}" y="${r1(y)}">${esc(txt.split("\n")[0])}</tspan></text>`;
  }

  function walk(el) {
    if (SKIP.has(el.tagName)) return "";
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity) === 0) return "";
    if (cs.filter && cs.filter.includes("blur")) return ""; // 흐린 장식 원은 생략
    const rect = el.getBoundingClientRect();
    if (el.tagName === "svg") {
      if (!rect.width || !rect.height) return "";
      const op = parseFloat(cs.opacity);
      return op < 1 ? `<g opacity="${op}">${svgCopy(el, rect)}</g>` : svgCopy(el, rect);
    }
    let inner = "";
    if (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)) {
      const t = el.type;
      if (["checkbox", "radio", "hidden", "file"].includes(t)) return "";
      if (rect.width === 0 || rect.height === 0) return "";
      return `<g id="${esc("입력칸")}">${boxSvg(el, cs, rect)}${fieldText(el, cs, rect)}</g>`;
    }
    // 닫힌 펼침 목록은 제목(summary)만 그림
    const kids = el.tagName === "DETAILS" && !el.open ? [...el.children].filter((c) => c.tagName === "SUMMARY") : el.childNodes;
    // 쌓임 순서(z-index)가 높은 요소를 나중에(위에) 그림
    const parts = [];
    [...kids].forEach((ch, i) => {
      if (ch.nodeType === Node.TEXT_NODE) { if (ch.data.trim()) parts.push({ z: 0, i, s: textSvg(ch) }); }
      else if (ch.nodeType === Node.ELEMENT_NODE) {
        const ccs = getComputedStyle(ch);
        const z = ccs.position !== "static" && ccs.zIndex !== "auto" ? parseInt(ccs.zIndex, 10) || 0 : 0;
        parts.push({ z, i, s: walk(ch) });
      }
    });
    parts.sort((a, b) => a.z - b.z || a.i - b.i);
    inner = parts.map((p) => p.s).join("");
    const box = rect.width > 0 && rect.height > 0 ? boxSvg(el, cs, rect) : "";
    if (!box && !inner) return "";
    const op = parseFloat(cs.opacity);
    // 넘치는 부분을 숨기는 상자(overflow: hidden)는 잘라내기 영역으로
    let clip = "";
    if (inner && rect.width > 0 && rect.height > 0 && /hidden|clip/.test(cs.overflowX + cs.overflowY) && el !== document.body) {
      const id = "c" + uid++;
      const rad = Math.min(parseFloat(cs.borderTopLeftRadius) || 0, rect.width / 2, rect.height / 2);
      defs.push(`<clipPath id="${id}"><rect x="${r1(rect.left + scrollX)}" y="${r1(rect.top + scrollY)}" width="${r1(rect.width)}" height="${r1(rect.height)}" rx="${r1(rad)}"/></clipPath>`);
      clip = ` clip-path="url(#${id})"`;
    }
    const grouped = box || SEMANTIC[el.tagName] || op < 1 || clip;
    if (!grouped) return inner;
    return `<g id="${esc(nameOf(el))}"${op < 1 ? ` opacity="${op}"` : ""}${clip}>${box}${inner}</g>`;
  }

  function run() {
    const W = Math.ceil(document.documentElement.scrollWidth);
    const H = Math.ceil(document.documentElement.scrollHeight);
    const pageBg = color(getComputedStyle(document.body).backgroundColor) || { hex: "#ffffff", a: 1 };
    const body = walk(document.body);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">` +
      `<defs>${defs.join("")}</defs><rect id="배경" x="0" y="0" width="${W}" height="${H}"${fillAttr(pageBg)}/>${body}</svg>`;
    parent.postMessage({ svg }, "*");
  }
  // 1) 전체 높이를 부모에게 알림 → 2) 부모가 그 높이로 늘린 뒤 'go' 를 보내면 변환 (고정 요소가 실제 위치에 오도록)
  addEventListener("message", (e) => { if (e.data === "go") setTimeout(run, 400); });
  addEventListener("load", () => (document.fonts ? document.fonts.ready : Promise.resolve()).then(() =>
    setTimeout(() => parent.postMessage({ h: Math.ceil(document.documentElement.scrollHeight) }, "*"), 600)));
})();
