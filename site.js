/* ============================================================
   Penluka — interactions
============================================================ */

// ---------- Categories ----------
const TAG = "penluka-22";
const CATEGORIES = [
  { num: "01", jp: "女性",        en: "Women",        url: `https://www.amazon.co.jp/b?node=5916190051&tag=${TAG}` },
  { num: "02", jp: "少年",        en: "Boys",         url: `https://www.amazon.co.jp/b?node=5916187051&tag=${TAG}` },
  { num: "03", jp: "青年",        en: "Young Men",    url: `https://www.amazon.co.jp/b?node=5916188051&tag=${TAG}` },
  { num: "04", jp: "おすすめ",    en: "Recommended",  url: `https://www.amazon.co.jp/b?node=10409694051&tag=${TAG}` },
  { num: "05", jp: "ランキング",  en: "Ranking",      url: `https://www.amazon.co.jp/b?node=10431890051&tag=${TAG}` },
  { num: "06", jp: "新着",        en: "New Arrivals", url: `https://www.amazon.co.jp/s?k=Kindle%E3%82%A4%E3%83%B3%E3%83%87%E3%82%A3%E3%83%BC%E3%82%BA%E6%BC%AB%E7%94%BB&i=digital-text&s=date-desc-rank&tag=${TAG}` },
];

// ペンルカの一言テンプレート（暫定。後でClaude APIで自動生成予定）
const REVIEW_TEMPLATES = [
  "今夜のおとも、ペンルカが見つけました。",
  "ぱらり、と一気に最後まで。",
  "ペンルカの夜更かしリスト入り。",
  "気になる、を一冊で。",
  "今日はこれで決まり。",
  "羽根ペンが指した、今夜の一冊。",
  "短い時間でぐっと引き込まれます。",
  "通勤の友に、寝る前のお供に。",
  "気がついたら最終話まで。",
];

function renderCards(cards) {
  const grid = document.getElementById("mangaGrid");
  if (!grid) return;
  grid.innerHTML = "";

  cards.forEach((m, i) => {
    const fromSide = i % 2 === 0 ? "from-left" : "from-right";
    const review = REVIEW_TEMPLATES[i % REVIEW_TEMPLATES.length];
    const ribbon = i === 0 ? "TODAY'S PICK" : `NO.${String(i + 1).padStart(2, "0")}`;
    const badgeOrange = i % 3 === 0;
    const el = document.createElement("article");
    el.className = `card ${fromSide}`;
    el.innerHTML = `
      <div class="thumb">
        <div class="art">
          ${m.image
            ? `<img class="cover" src="${m.image}" alt="${escapeHtml(m.title)}" loading="lazy" />`
            : `<div class="ph p1"><span class="ph-title">${escapeHtml(m.title.slice(0, 20))}</span><span class="ph-tag">COVER / ${escapeHtml(m.genre || "")}</span></div>`
          }
        </div>
        <span class="badge ${badgeOrange ? "orange" : ""}">${escapeHtml(m.genre || "インディーズ")}</span>
        <span class="ribbon">${ribbon}</span>
      </div>
      <div class="body">
        <h3>${escapeHtml(m.title)}</h3>
        <div class="author">${escapeHtml(m.author || "")}</div>
        <div class="review">
          <span class="avatar"><img src="assets/penluka.png" alt=""/></span>
          <q>${escapeHtml(review)}</q>
        </div>
        <div class="cta">
          <a class="read" href="${m.url || "#"}" target="_blank" rel="noopener">読む →</a>
          <span class="meta">¥0 で読める</span>
        </div>
      </div>
    `;
    grid.appendChild(el);
  });

  // カードに3D傾きを適用
  attachTilt();
  // スクロールリビールを再付与
  document.querySelectorAll(".card").forEach((el) => io.observe(el));
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// ---------- Load manga data from data.json ----------
fetch("data.json", { cache: "no-store" })
  .then((r) => r.ok ? r.json() : Promise.reject(r.status))
  .then((data) => {
    renderCards(data.cards || []);
  })
  .catch((err) => {
    console.warn("data.json読み込み失敗:", err);
    // フォールバック: data.jsonがまだ無い場合は空表示
    const grid = document.getElementById("mangaGrid");
    if (grid) grid.innerHTML = '<p style="opacity:.6;text-align:center;padding:40px;">作品データを読み込めませんでした。</p>';
  });

// ---------- Render categories ----------
const catGrid = document.getElementById("catGrid");
CATEGORIES.forEach((c, i) => {
  const a = document.createElement("a");
  a.className = "cat reveal d" + ((i % 5) + 1);
  a.href = c.url;
  a.target = "_blank";
  a.rel = "noopener";
  a.innerHTML = `
    <span class="cat-num">CAT ${c.num}</span>
    <span class="cat-jp">${c.jp}</span>
    <span class="cat-en">${c.en}</span>
    <span class="arrow">→</span>
  `;
  catGrid.appendChild(a);
});

// ---------- Reveal on scroll ----------
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (e.isIntersecting) {
      e.target.classList.add("is-in");
      io.unobserve(e.target);
    }
  });
}, { threshold: 0.14, rootMargin: "0px 0px -60px 0px" });

document.querySelectorAll(".reveal, .card").forEach((el) => io.observe(el));

// ---------- Rail progress + active dot + dark nav ----------
const railLine = document.getElementById("railLine");
const dots = [...document.querySelectorAll(".rail-dot")];
const targets = dots.map((d) => document.getElementById(d.dataset.target));
const nav = document.getElementById("nav");
const rail = document.getElementById("rail");

dots.forEach((d) => {
  d.addEventListener("click", () => {
    const t = document.getElementById(d.dataset.target);
    if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

const bgCanvas = document.getElementById("bgCanvas");
const blobA = document.getElementById("blobA");
const blobB = document.getElementById("blobB");
const blobC = document.getElementById("blobC");
const bgDots = document.getElementById("bgDots");

function onScroll() {
  const scrollY = window.scrollY;
  const h = document.documentElement.scrollHeight - window.innerHeight;
  const pct = Math.min(100, (scrollY / h) * 100);
  railLine.style.setProperty("--progress", pct + "%");

  // active section dot
  let activeIdx = 0;
  targets.forEach((t, i) => {
    if (!t) return;
    const rect = t.getBoundingClientRect();
    if (rect.top <= window.innerHeight * 0.45) activeIdx = i;
  });
  dots.forEach((d, i) => d.classList.toggle("active", i === activeIdx));

  // dark mode for follow section
  const followSec = document.getElementById("follow");
  const followRect = followSec.getBoundingClientRect();
  const onDark = followRect.top <= 80 && followRect.bottom > 140;
  nav.classList.toggle("on-dark", onDark);
  rail.classList.toggle("on-dark-rail", onDark);

  // background tone transitions
  // hero/concept -> cream (warm), new -> paper, cats -> warm, follow -> navy
  const sections = ["hero", "concept", "new", "category", "follow"];
  let current = "hero";
  sections.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const r = el.getBoundingClientRect();
    if (r.top <= window.innerHeight * 0.5) current = id;
  });
  bgCanvas.classList.remove("navy", "cream", "warm");
  if (current === "follow") bgCanvas.classList.add("navy");
  else if (current === "category") bgCanvas.classList.add("warm");
  else bgCanvas.classList.add("cream");

  // parallax on blobs + dots
  blobA.style.transform = `translate3d(0, ${scrollY * 0.12}px, 0)`;
  blobB.style.transform = `translate3d(0, ${scrollY * -0.08}px, 0)`;
  blobC.style.transform = `translate3d(0, ${scrollY * 0.15}px, 0)`;
  bgDots.style.transform = `translate3d(0, ${scrollY * 0.05}px, 0)`;
}
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

// ---------- 3D tilt on cards ----------
let tiltAmount = 8;

function attachTilt() {
  document.querySelectorAll(".card").forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = `perspective(900px) translateY(-10px) rotateX(${-y * tiltAmount}deg) rotateY(${x * tiltAmount}deg)`;
    });
    card.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
  });
}
attachTilt();

// ---------- Feather parallax follows mouse (hero) ----------
const hero = document.getElementById("hero");
hero.addEventListener("mousemove", (e) => {
  const r = hero.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width - 0.5;
  const y = (e.clientY - r.top) / r.height - 0.5;
  document.querySelectorAll(".feather").forEach((f, i) => {
    const m = (i + 1) * 10;
    f.style.transform = `translate(${x * m}px, ${y * m}px)`;
  });
  const mark = document.getElementById("heroMark");
  mark.style.transform = `translate(${x * 14}px, ${y * 8}px)`;
});
hero.addEventListener("mouseleave", () => {
  document.querySelectorAll(".feather").forEach((f) => (f.style.transform = ""));
  const mark = document.getElementById("heroMark");
  if (mark) mark.style.transform = "";
});

