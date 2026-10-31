/* Žilina Bears – spoločné skripty: menu, noviny, článok */
(function () {
  "use strict";

  // ---------- hlavička: po odscrollovaní zmenšiť logo
  const top = document.querySelector("header.top");
  if (top) {
    const mini = () => top.classList.toggle("mini", window.scrollY > 40);
    window.addEventListener("scroll", mini, { passive: true });
    mini();
  }

  // ---------- mobilné menu
  const burger = document.querySelector(".burger");
  const menu = document.getElementById("menu");
  if (burger && menu) {
    const set = (open) => {
      menu.classList.toggle("open", open);
      burger.setAttribute("aria-expanded", String(open));
      burger.setAttribute("aria-label", open ? "Zavrieť menu" : "Otvoriť menu");
      burger.querySelector("svg").innerHTML = open
        ? '<path d="M6 6l12 12M18 6 6 18"/>'
        : '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>';
    };
    burger.addEventListener("click", () => set(!menu.classList.contains("open")));
    menu.addEventListener("click", (e) => { if (e.target.closest("a")) set(false); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && menu.classList.contains("open")) { set(false); burger.focus(); }
    });
  }

  // ---------- chýbajúce obrázky: bez ikonky rozbitého obrázka
  document.addEventListener("error", (e) => {
    const t = e.target;
    if (t.tagName !== "IMG") return;
    if (t.classList.contains("thumb")) { t.removeAttribute("src"); }
    else if (t.classList.contains("cover")) { t.remove(); }
  }, true);

  // ---------- pomocné funkcie
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const SRC = { facebook: "Facebook", instagram: "Instagram", archiv: "Archív", web: "Článok" };
  const fmtDate = (iso) => {
    const d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleDateString("sk-SK", { day: "numeric", month: "numeric", year: "numeric" });
  };
  const badge = (p) => p.source === "ragby"
    ? `<span class="badge ragby">${esc(p.category || "Článok")}</span>`
    : `<span class="badge ${esc(p.source)}">${esc(SRC[p.source] || p.source)}</span>`;
  const href = (p) => p.source === "ragby" ? `clanok.html?r=${encodeURIComponent(p.id)}` : `clanok.html?id=${encodeURIComponent(p.id)}`;
  const card = (p) => `
    <a class="post" href="${href(p)}">
      ${p.thumb
        ? `<img class="thumb" src="${esc(p.thumb)}" alt="" loading="lazy">`
        : `<span class="thumb none" aria-hidden="true"><svg width="48" height="48" viewBox="0 0 44 44"><path d="M22 2 L40 9 V22 C40 32 32 39 22 42 C12 39 4 32 4 22 V9 Z" fill="none" stroke="currentColor" stroke-width="3"/></svg></span>`}
      <span class="body">
        <span class="meta">${badge(p)}<span class="d">${fmtDate(p.date)}</span>${p.files ? `<span class="d">· ${p.files === 1 ? "1 súbor" : p.files + " súbory"} na stiahnutie</span>` : ""}</span>
        <h3>${esc(p.title)}</h3>
        ${p.excerpt ? `<p>${esc(p.excerpt)}</p>` : ""}
      </span>
    </a>`;

  async function loadIndex(file = "data/posts.json") {
    const r = await fetch(file, { cache: "no-cache" });
    if (!r.ok) throw new Error(file);
    const list = await r.json();
    return list.sort((a, b) => (a.date < b.date ? 1 : -1));
  }
  const fail = (el) => { el.innerHTML = '<div class="empty">Novinky sa nepodarilo načítať. Pozri náš <a href="https://www.facebook.com/Zilina.Bears/">Facebook</a>.</div>'; };


  // ---------- rozvrh tréningov z data/treningy.json
  const hs = document.getElementById("hero-sched");
  if (hs) {
    const PIN = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1E5B3A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.5-7-12a7 7 0 0 1 14 0c0 5.5-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>';
    const DAY = 864e5;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const toDate = (s) => { const [y, m, d] = String(s).split("-").map(Number); return new Date(y, m - 1, d); };
    const sk = (dt) => `${dt.getDate()}. ${dt.getMonth() + 1}.`;
    const MES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const en = (dt) => `${dt.getDate()} ${MES[dt.getMonth()]}`;
    const VOPRED = 7, PO = 7;   // koľko dní pred zmenou a po nej ju web hlási

    // Zmena v treningy.json: blok "zmena" s dátumom "od" (a voliteľne "do") a len tými údajmi, ktoré sa menia.
    const apply = (x) => {
      const z = x.zmena;
      if (!z || !z.od) return x;
      const od = toDate(z.od), dok = z.do ? toDate(z.do) : null;
      const nove = Object.assign({}, x, z); delete nove.zmena;
      const kym = Math.round((od - today) / DAY);
      const info = { od, dok, nove };
      if (dok && today > dok) return x;                                    // dočasná zmena skončila
      if (kym > VOPRED) return x;                                          // ešte priskoro hlásiť
      if (kym > 0) return Object.assign({}, x, { _pripravuje: info });     // o pár dní
      return Object.assign(nove, { _zmena: (dok || -kym < PO) ? info : null }); // už platí
    };
    const cas = (x) => `${x.den} ${x.cas}, ${x.miesto}`;
    const obdobie = (i) => i.dok ? `od ${sk(i.od)} do ${sk(i.dok)}` : `od ${sk(i.od)}`;
    const mapa = (x) => x.mapa ? ` <a href="${esc(x.mapa)}">Mapa →</a>` : "";

    fetch("data/treningy.json", { cache: "no-cache" }).then((r) => r.json()).then((d) => {
      const t = (d.treningy || []).filter((x) => x.den && x.cas).map(apply);
      if (!t.length) return;
      const pozn = (x) => x._pripravuje ? `<span class="hs-z">Od ${sk(x._pripravuje.od)}: ${esc(x._pripravuje.nove.den)} <b>${esc(x._pripravuje.nove.cas)}</b> · ${esc(x._pripravuje.nove.miesto)}</span>`
        : x._zmena ? `<span class="hs-z">Zmena ${esc(obdobie(x._zmena))}</span>` : "";
      hs.innerHTML = t.map((x) => `<li${x._pripravuje || x._zmena ? ' class="zmena"' : ""}><span class="hs-g">${esc(x.skupina)}</span><span class="hs-t">${esc(x.den)} <b>${esc(x.cas)}</b></span><span class="hs-p">${esc(x.miesto)}</span>${pozn(x)}</li>`).join("");
      const grid = document.getElementById("train-grid");
      if (grid) grid.innerHTML = t.map((x) => {
        const p = x._pripravuje, z = x._zmena;
        const box = p ? `<div class="zmena-box"><strong>Zmena ${esc(obdobie(p))}</strong>${esc(cas(p.nove))}${mapa(p.nove)}</div>`
          : z ? `<div class="zmena-box"><strong>Nové ${esc(obdobie(z))}</strong>Pozor na zmenený čas alebo miesto.</div>` : "";
        return `<article class="card"><div class="kicker" style="letter-spacing:1px">${esc(x.skupina)}</div><h3>${esc(x.den)} ${esc(x.cas)}</h3><div class="row">${PIN}<span>${esc(x.miesto)}</span></div>${box}${x.mapa ? `<a class="more" href="${esc(x.mapa)}">Otvoriť v mape →</a>` : ""}</article>`;
      }).join("");
      const ens = document.getElementById("en-sched");
      if (ens) ens.innerHTML = t.map((x) => {
        const p = x._pripravuje, n = p && p.nove;
        const zm = n ? ` <em>From ${en(p.od)}${p.dok ? ` to ${en(p.dok)}` : ""}: ${esc(n.en_den || n.den)} ${esc(n.cas)}, ${esc(n.en_miesto || n.miesto)}.</em>` : "";
        return `<strong>${esc(x.en_skupina || x.skupina)}:</strong> ${esc(x.en_den || x.den)} ${esc(x.cas)}, ${esc(x.en_miesto || x.miesto)}.${zm}`;
      }).join(" ");

      // oznamy nad rozvrhom: ručný oznam + automatické hlásenie zmien
      const msgs = [];
      if (d.oznam && d.oznam.trim()) msgs.push(esc(d.oznam));
      t.forEach((x) => {
        const p = x._pripravuje, z = x._zmena;
        if (p) msgs.push(`<b>Pozor, zmena!</b> ${esc(x.skupina)} ${esc(obdobie(p))}: ${esc(cas(p.nove))}.${mapa(p.nove)}`);
        else if (z) msgs.push(`${esc(x.skupina)} trénuje ${esc(obdobie(z))}: ${esc(cas(x))}.${mapa(x)}`);
      });
      const oz = document.getElementById("oznam");
      if (oz && msgs.length) { oz.innerHTML = msgs.map((m) => `<p>${m}</p>`).join(""); oz.hidden = false; }
    }).catch(() => { /* pri chybe ostane rozvrh zapísaný priamo v stránke */ });
  }

  // ---------- úvodná stránka: 3 najnovšie
  const home = document.getElementById("home-news");
  if (home) loadIndex().then((l) => { home.innerHTML = l.slice(0, 6).map(card).join(""); }).catch(() => fail(home));

  // ---------- stránka Noviny
  const list = document.getElementById("news-list");
  if (list) {
    const chipsEl = document.getElementById("chips");
    let all = [], filter = "all";
    const FILTERS = [["all", "Všetko"], ["facebook", "Facebook"], ["instagram", "Instagram"], ["archiv", "Archív"]];
    const render = () => {
      chipsEl.innerHTML = FILTERS.map(([id, l]) => {
        const n = id === "all" ? all.length : all.filter((p) => p.source === id).length;
        return n || id === "all" ? `<button type="button" class="chip" data-f="${id}" aria-pressed="${filter === id}">${l} <span style="opacity:.7">(${n})</span></button>` : "";
      }).join("");
      chipsEl.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => { filter = b.dataset.f; render(); }));
      const shown = filter === "all" ? all : all.filter((p) => p.source === filter);
      if (!shown.length) { list.innerHTML = '<div class="empty">Zatiaľ tu nič nie je.</div>'; return; }
      const years = {};
      shown.forEach((p) => (years[p.date.slice(0, 4)] ||= []).push(p));
      list.innerHTML = Object.keys(years).sort().reverse()
        .map((y) => `<h2 class="year">${y}</h2><div class="grid news">${years[y].map(card).join("")}</div>`).join("");
    };
    loadIndex().then((l) => { all = l; render(); }).catch(() => fail(list));
  }

  // ---------- O ragby: ukážka na úvode a zoznam s filtrom kategórií
  const hr = document.getElementById("home-ragby");
  if (hr) loadIndex("data/ragby.json").then((l) => {
    if (!l.length) { hr.closest("section").hidden = true; return; }
    hr.innerHTML = l.slice(0, 3).map(card).join("");
  }).catch(() => { hr.closest("section").hidden = true; });

  const rl = document.getElementById("ragby-list");
  if (rl) {
    const chipsEl = document.getElementById("chips");
    let all = [], filter = "all";
    const render = () => {
      const cats = [...new Set(all.map((p) => p.category))].sort((a, b) => a.localeCompare(b, "sk"));
      chipsEl.innerHTML = [["all", "Všetko"], ...cats.map((c) => [c, c])].map(([id, l]) =>
        `<button type="button" class="chip" data-f="${esc(id)}" aria-pressed="${filter === id}">${esc(l)} <span style="opacity:.7">(${id === "all" ? all.length : all.filter((p) => p.category === id).length})</span></button>`).join("");
      chipsEl.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => { filter = b.dataset.f; render(); }));
      const shown = filter === "all" ? all : all.filter((p) => p.category === filter);
      rl.innerHTML = shown.length ? `<div class="grid news">${shown.map(card).join("")}</div>` : '<div class="empty">Zatiaľ tu nič nie je.</div>';
    };
    loadIndex("data/ragby.json").then((l) => { all = l; render(); })
      .catch(() => { rl.innerHTML = '<div class="empty">Články sa nepodarilo načítať.</div>'; });
  }

  // ---------- detail článku
  const art = document.getElementById("article");
  if (art) {
    const qs = new URLSearchParams(location.search);
    const rid = qs.get("r");
    const id = rid || qs.get("id");
    const back = rid ? '<a class="back" href="ragby.html">← Späť na O ragby</a>' : '<a class="back" href="noviny.html">← Späť na noviny</a>';
    const linkify = (t) => esc(t).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" rel="noopener">$1</a>');
    const paras = (t) => String(t || "").split(/\n{2,}/).map((p) => `<p>${linkify(p.trim())}</p>`).join("");
    fetch(`data/${rid ? "ragby" : "posts"}/${encodeURIComponent(id || "")}.json`, { cache: "no-cache" })
      .then((r) => { if (!r.ok) throw 0; return r.json(); })
      .then((p) => {
        document.title = `${p.title} – Žilina Bears`;
        const imgs = p.images || [];
        const gallery = imgs.length > 1
          ? `<div class="gal">${imgs.map((src) => `<a href="${esc(src)}"><img src="${esc(src)}" alt="" loading="lazy"></a>`).join("")}</div>` : "";
        const cover = imgs.length === 1 ? `<img class="cover" src="${esc(imgs[0])}" alt="">` : (p.html && p.thumb ? `<img class="cover" src="${esc(p.thumb)}" alt="">` : "");
        const links = [p.link ? { source: p.source, link: p.link } : null, ...(p.also_on || [])].filter(Boolean)
          .filter((x) => x.source !== "archiv")
          .map((x) => `<a class="btn btn-d" href="${esc(x.link)}" rel="noopener">Pozri na ${esc(SRC[x.source] || x.source)} →</a>`).join(" ");
        const files = (p.files || []).length ? `<div class="files"><h2>Na stiahnutie</h2>${p.files.map((f) =>
          `<a class="file" href="${esc(f.href)}" download><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg><span>${esc(f.label)}</span></a>`).join("")}</div>` : "";
        art.innerHTML = `
          ${back}
          <div class="meta">${badge(p)}${(p.also_on || []).map(badge).join("")}<span class="d">${fmtDate(p.date)}</span></div>
          <h1>${esc(p.title)}</h1>
          ${p.excerpt && p.html ? `<p class="lead">${esc(p.excerpt)}</p>` : ""}
          ${cover}
          <div class="content ${p.html ? "" : "text"}">${p.html || paras(p.text)}</div>
          ${gallery}
          ${files}
          <div style="display:flex;flex-wrap:wrap;gap:12px;padding-top:16px;border-top:2px solid var(--line)">
            ${links}<a class="btn btn-y" href="https://wa.me/421911913244">Chcem sa pridať</a>
          </div>`;
        // lightbox
        const lb = document.querySelector(".lb");
        art.querySelectorAll(".gal img, .content img").forEach((img) => {
          img.style.cursor = "zoom-in";
          img.addEventListener("click", (e) => {
            e.preventDefault(); lb.querySelector("img").src = img.currentSrc || img.src;
            lb.classList.add("open"); lb.querySelector("button").focus();
          });
        });
      })
      .catch(() => { art.innerHTML = back + '<div class="empty">Tento článok sme nenašli.</div>'; });
    const lb = document.querySelector(".lb");
    const close = () => lb.classList.remove("open");
    lb.addEventListener("click", (e) => { if (e.target === lb || e.target.tagName === "BUTTON") close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  }
})();
