/* Seelenmut CMS – Admin UI logic */
(() => {
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  const state = {
    editingPageId: null,
    editingPostId: null,
    mediaPickerTarget: null,
  };

  // ---------- API ----------
  async function api(path, options = {}) {
    const opts = { credentials: "include", headers: {}, ...options };
    if (opts.body && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      if (typeof opts.body !== "string") opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, opts);
    if (res.status === 401) {
      window.location.href = "/login";
      throw new Error("unauthorized");
    }
    if (!res.ok) {
      let msg = `${res.status}`;
      try {
        const d = await res.json();
        msg = d.detail || JSON.stringify(d);
      } catch (_) { /* ignore */ }
      throw new Error(msg);
    }
    if (res.status === 204) return null;
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  // ---------- Toast ----------
  function toast(msg, kind = "") {
    const t = $("#toast");
    t.textContent = msg;
    t.className = `toast show ${kind}`;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("show"), 3500);
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatDate(iso) {
    if (!iso) return "–";
    const d = new Date(iso + (iso.endsWith("Z") ? "" : "Z"));
    return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function formatSize(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
    return `${bytes.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  }

  // ---------- View switching ----------
  function showView(name) {
    $$(".view").forEach((v) => (v.hidden = true));
    const view = $(`#view-${name}`);
    if (view) view.hidden = false;
    $$(".nav-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.view === name);
    });
    // page builder takes full width — hide sidebar padding
    document.querySelector(".content").classList.toggle("pb-active", name === "page-editor");
    if (name === "dashboard") loadDashboard();
    if (name === "pages") loadPages();
    if (name === "posts") loadPosts();
    if (name === "media") loadMedia();
  }

  $$(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });

  $$("[data-back]").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.back));
  });

  // ---------- Session ----------
  async function loadMe() {
    try {
      const me = await api("/api/me");
      $("#user-name").textContent = me.user ? `👤 ${me.user}` : "";
    } catch (_) { /* already redirected */ }
  }
  $("#btn-logout").addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });

  // ---------- Dashboard ----------
  async function loadDashboard() {
    try {
      const s = await api("/api/admin/stats");
      $("#stats-grid").innerHTML = `
        <div class="stat-card">
          <div class="label">Seiten</div>
          <div class="value">${s.pages.total}</div>
          <div class="sub">${s.pages.published} veröffentlicht</div>
        </div>
        <div class="stat-card">
          <div class="label">Blogposts</div>
          <div class="value">${s.posts.total}</div>
          <div class="sub">${s.posts.published} veröffentlicht</div>
        </div>
        <div class="stat-card">
          <div class="label">Medien</div>
          <div class="value">${s.media.total}</div>
          <div class="sub">Bilder im Speicher</div>
        </div>`;
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  $$("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const a = btn.dataset.action;
      if (a === "new-post") { showView("posts"); newPost(); }
      if (a === "new-page") { showView("pages"); newPage(); }
      if (a === "open-media") showView("media");
    });
  });

  // ---------- Pages ----------
  async function loadPages() {
    try {
      const rows = await api("/api/admin/pages");
      const container = $("#pages-list");
      if (!rows.length) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="icon">📄</div>
            <p>Noch keine Seiten angelegt.</p>
            <button class="btn primary" onclick="document.getElementById('btn-new-page').click()">+ Erste Seite anlegen</button>
          </div>`;
        return;
      }
      container.innerHTML = `
        <table class="data-table">
          <thead><tr><th>Titel</th><th>Slug</th><th>Status</th><th>Menü</th><th>Aktualisiert</th><th></th></tr></thead>
          <tbody>
            ${rows.map((p) => `
              <tr>
                <td><div class="row-title">${escapeHtml(p.title)}</div><div class="row-sub">${escapeHtml(p.excerpt || "")}</div></td>
                <td><code>/${escapeHtml(p.slug)}</code></td>
                <td><span class="badge ${p.status}">${p.status === "published" ? "Live" : "Entwurf"}</span></td>
                <td>${p.show_in_menu ? "Ja" : "Nein"}</td>
                <td>${formatDate(p.updated_at)}</td>
                <td><button class="btn small" data-edit-page="${p.id}">Bearbeiten</button></td>
              </tr>`).join("")}
          </tbody>
        </table>`;
      container.querySelectorAll("[data-edit-page]").forEach((b) =>
        b.addEventListener("click", () => editPage(Number(b.dataset.editPage)))
      );
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  $("#btn-new-page").addEventListener("click", () => newPage());

  // ---------- Block Editor ----------
  state.blocks = [];

  const BLOCK_TYPES = {
    hero: { label: "Hero", icon: "🏔", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Titel", type: "text" },
      { key: "subtitle", label: "Untertitel", type: "textarea" },
      { key: "cta_text", label: "Button-Text", type: "text" },
      { key: "cta_href", label: "Button-Link", type: "text" },
      { key: "image", label: "Bild-URL", type: "text" },
    ]},
    text: { label: "Text", icon: "📝", fields: [
      { key: "content", label: "Inhalt (Markdown)", type: "textarea-lg" },
    ]},
    cards: { label: "Karten", icon: "🃏", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Überschrift", type: "text" },
      { key: "items", label: "Karten (eine pro Zeile: Titel | Text | Link)", type: "textarea-lg" },
    ]},
    testimonials: { label: "Testimonials", icon: "💬", fields: [
      { key: "title", label: "Überschrift", type: "text" },
      { key: "items", label: "Zitate (eines pro Absatz, Leerzeile trennt)", type: "textarea-lg" },
    ]},
    cta: { label: "Call to Action", icon: "📣", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Titel", type: "text" },
      { key: "text", label: "Text", type: "textarea" },
      { key: "cta_text", label: "Button-Text", type: "text" },
      { key: "cta_href", label: "Button-Link", type: "text" },
      { key: "style", label: "Stil (dark / light)", type: "text" },
    ]},
    marquee: { label: "Marquee", icon: "✦", fields: [
      { key: "items", label: "Texte (durch | getrennt, z.B. Recovery ist möglich. | Du darfst langsam sein.)", type: "textarea" },
    ]},
    feature: { label: "Feature", icon: "⭐", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Titel", type: "text" },
      { key: "text", label: "Text", type: "textarea" },
      { key: "bullets", label: "Bullet-Punkte (eine pro Zeile)", type: "textarea-lg" },
      { key: "cta_text", label: "Button-Text", type: "text" },
      { key: "cta_href", label: "Button-Link", type: "text" },
      { key: "style", label: "Stil (dark / light)", type: "text" },
    ]},
    image: { label: "Bild", icon: "🖼", fields: [
      { key: "src", label: "Bild-URL", type: "text" },
      { key: "alt", label: "Alt-Text", type: "text" },
      { key: "caption", label: "Bildunterschrift", type: "text" },
    ]},
    person: { label: "Person", icon: "👤", fields: [
      { key: "image", label: "Bild-URL", type: "text" },
      { key: "name", label: "Name", type: "text" },
      { key: "role", label: "Rolle/Titel", type: "text" },
      { key: "text", label: "Beschreibung", type: "textarea" },
      { key: "cta_text", label: "Button-Text", type: "text" },
      { key: "cta_href", label: "Button-Link", type: "text" },
    ]},
    columns: { label: "Zwei-Spalten", icon: "◫", fields: [
      { key: "layout", label: "Layout (text-image / image-text / text-text)", type: "text" },
      { key: "left_content", label: "Linke Spalte (Markdown)", type: "textarea-lg" },
      { key: "right_content", label: "Rechte Spalte (Markdown/Bild-URL)", type: "textarea-lg" },
    ]},
    numberedcards: { label: "Nummerierte Karten", icon: "🔢", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Überschrift", type: "text" },
      { key: "subtitle", label: "Untertitel", type: "textarea" },
      { key: "items", label: "Karten (pro Zeile: Titel | Text)", type: "textarea-lg" },
    ]},
    bento: { label: "Bento-Grid", icon: "▦", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Überschrift", type: "text" },
      { key: "link_text", label: "Link-Text (oben rechts)", type: "text" },
      { key: "link_href", label: "Link-URL", type: "text" },
      { key: "items", label: "Karten (pro Zeile: Label | Titel | Text | Link | Stil: big/butter/outline)", type: "textarea-lg" },
    ]},
    posts: { label: "Blog-Posts", icon: "📰", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Überschrift", type: "text" },
      { key: "count", label: "Anzahl (3, 4 oder 6)", type: "text" },
      { key: "link_text", label: "Alle-Posts Link-Text", type: "text" },
      { key: "link_href", label: "Link-URL", type: "text" },
    ]},
    video: { label: "Video", icon: "🎬", fields: [
      { key: "url", label: "Video-URL (YouTube oder Vimeo)", type: "text" },
      { key: "caption", label: "Bildunterschrift", type: "text" },
    ]},
    gallery: { label: "Galerie", icon: "🏞", fields: [
      { key: "columns", label: "Spalten (2, 3 oder 4)", type: "text" },
      { key: "images", label: "Bilder (pro Zeile: URL | Alt-Text | Caption)", type: "textarea-lg" },
    ]},
    divider: { label: "Trennlinie", icon: "─", fields: [
      { key: "style", label: "Stil (line / space / dots)", type: "text" },
      { key: "size", label: "Größe (sm / md / lg)", type: "text" },
    ]},
    accordion: { label: "Akkordeon", icon: "▸", fields: [
      { key: "title", label: "Überschrift", type: "text" },
      { key: "items", label: "Fragen & Antworten (pro Zeile: Frage | Antwort)", type: "textarea-lg" },
    ]},
    stats: { label: "Zahlen", icon: "📊", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "items", label: "Zahlen (pro Zeile: Zahl | Beschreibung)", type: "textarea-lg" },
    ]},
    pricing: { label: "Preistabelle", icon: "💰", fields: [
      { key: "eyebrow", label: "Eyebrow", type: "text" },
      { key: "title", label: "Überschrift", type: "text" },
      { key: "items", label: "Pakete (pro Zeile: Name | Preis | Features;getrennt | Button-Text | Link)", type: "textarea-lg" },
    ]},
    quote: { label: "Zitat", icon: "❝", fields: [
      { key: "text", label: "Zitat-Text", type: "textarea" },
      { key: "author", label: "Autor", type: "text" },
      { key: "role", label: "Rolle/Titel", type: "text" },
    ]},
    list: { label: "Liste", icon: "📋", fields: [
      { key: "title", label: "Überschrift", type: "text" },
      { key: "style", label: "Stil (check / dot / arrow)", type: "text" },
      { key: "items", label: "Einträge (einer pro Zeile)", type: "textarea-lg" },
    ]},
    callout: { label: "Hinweis", icon: "💡", fields: [
      { key: "style", label: "Stil (info / warning / tip)", type: "text" },
      { key: "title", label: "Titel", type: "text" },
      { key: "text", label: "Text", type: "textarea" },
    ]},
    timeline: { label: "Timeline", icon: "📅", fields: [
      { key: "title", label: "Überschrift", type: "text" },
      { key: "items", label: "Schritte (pro Zeile: Titel | Text)", type: "textarea-lg" },
    ]},
  };

  function blockPreview(block) {
    const e = escapeHtml;
    if (block.type === "hero") {
      return `<div class="bp bp-hero">
        ${block.image ? `<div class="bp-hero-img"><img src="${e(block.image)}" alt="" /></div>` : ""}
        <div class="bp-hero-body">
          ${block.eyebrow ? `<div class="bp-eyebrow">${e(block.eyebrow)}</div>` : ""}
          ${block.title ? `<div class="bp-h1">${e(block.title)}</div>` : '<div class="bp-h1 bp-placeholder">Hero Titel...</div>'}
          ${block.subtitle ? `<div class="bp-sub">${e(block.subtitle)}</div>` : ""}
          ${block.cta_text ? `<span class="bp-btn">${e(block.cta_text)} →</span>` : ""}
        </div>
      </div>`;
    }
    if (block.type === "text") {
      const text = (block.content || "").slice(0, 200);
      return `<div class="bp bp-text">
        <div class="bp-prose">${text ? e(text) + (block.content && block.content.length > 200 ? "..." : "") : '<span class="bp-placeholder">Text eingeben...</span>'}</div>
      </div>`;
    }
    if (block.type === "cards") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 4);
      return `<div class="bp bp-cards">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        <div class="bp-cards-grid">
          ${items.length ? items.map((line) => {
            const [title] = line.split("|");
            return `<div class="bp-card-item">${e((title || "").trim())}</div>`;
          }).join("") : '<div class="bp-card-item bp-placeholder">Karten hinzufügen...</div>'}
        </div>
      </div>`;
    }
    if (block.type === "testimonials") {
      const items = (block.items || "").split("\n\n").filter((t) => t.trim()).slice(0, 3);
      return `<div class="bp bp-testimonials">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        <div class="bp-testi-grid">
          ${items.length ? items.map((t) => `<div class="bp-testi-item">„ ${e(t.trim().slice(0, 80))}..."</div>`).join("") : '<div class="bp-testi-item bp-placeholder">Zitate einfügen...</div>'}
        </div>
      </div>`;
    }
    if (block.type === "cta") {
      const isDark = (block.style || "dark") === "dark";
      return `<div class="bp bp-cta ${isDark ? "bp-cta-dark" : "bp-cta-light"}">
        ${block.eyebrow ? `<div class="bp-eyebrow">${e(block.eyebrow)}</div>` : ""}
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : '<div class="bp-h2 bp-placeholder">CTA Titel...</div>'}
        ${block.text ? `<div class="bp-sub">${e(block.text)}</div>` : ""}
        ${block.cta_text ? `<span class="bp-btn">${e(block.cta_text)} →</span>` : ""}
      </div>`;
    }
    if (block.type === "marquee") {
      const items = (block.items || "Recovery ist möglich. | Du darfst langsam sein. | Bindung vor Methode.").split("|").map((s) => s.trim()).filter(Boolean);
      return `<div class="bp bp-marquee">
        <div class="bp-marquee-items">
          ${items.map((t) => `<span class="bp-marquee-item">${e(t)}</span><span class="bp-marquee-dot">✦</span>`).join("")}
        </div>
      </div>`;
    }
    if (block.type === "feature") {
      const isDark = (block.style || "dark") === "dark";
      const bullets = (block.bullets || "").split("\n").filter((l) => l.trim()).slice(0, 6);
      return `<div class="bp bp-feature ${isDark ? "bp-feature-dark" : "bp-feature-light"}">
        ${block.eyebrow ? `<div class="bp-eyebrow">${e(block.eyebrow)}</div>` : ""}
        ${block.title ? `<div class="bp-h1">${e(block.title)}</div>` : '<div class="bp-h1 bp-placeholder">Titel...</div>'}
        ${block.text ? `<div class="bp-sub">${e(block.text)}</div>` : ""}
        ${bullets.length ? `<div class="bp-bullets">${bullets.map((b) => `<span class="bp-bullet">• ${e(b.trim())}</span>`).join("")}</div>` : ""}
        ${block.cta_text ? `<span class="bp-btn">${e(block.cta_text)} →</span>` : ""}
      </div>`;
    }
    if (block.type === "image") {
      return `<div class="bp bp-image">
        ${block.src ? `<img src="${e(block.src)}" alt="${e(block.alt || "")}" />` : '<div class="bp-placeholder">Bild-URL einfügen...</div>'}
        ${block.caption ? `<div class="bp-caption">${e(block.caption)}</div>` : ""}
      </div>`;
    }
    if (block.type === "person") {
      return `<div class="bp bp-person">
        <div class="bp-person-img">${block.image ? `<img src="${e(block.image)}" alt="" />` : '<div class="bp-placeholder">👤</div>'}</div>
        <div class="bp-person-body">
          ${block.name ? `<div class="bp-h2">${e(block.name)}</div>` : '<div class="bp-h2 bp-placeholder">Name...</div>'}
          ${block.role ? `<div class="bp-eyebrow">${e(block.role)}</div>` : ""}
          ${block.text ? `<div class="bp-sub">${e(block.text).slice(0, 100)}...</div>` : ""}
          ${block.cta_text ? `<span class="bp-btn">${e(block.cta_text)} →</span>` : ""}
        </div>
      </div>`;
    }
    if (block.type === "columns") {
      const layout = block.layout || "text-image";
      return `<div class="bp bp-columns">
        <div class="bp-col">${e((block.left_content || "").slice(0, 80)) || '<span class="bp-placeholder">Linke Spalte...</span>'}</div>
        <div class="bp-col">${layout.includes("image") ? (block.right_content ? `<img src="${e(block.right_content)}" alt="" style="max-height:60px;border-radius:4px;" />` : '<span class="bp-placeholder">Bild/Text...</span>') : (e((block.right_content || "").slice(0, 80)) || '<span class="bp-placeholder">Rechte Spalte...</span>')}</div>
      </div>`;
    }
    if (block.type === "numberedcards") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 4);
      return `<div class="bp bp-numcards">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        <div class="bp-numcards-grid">${items.length ? items.map((line, i) => {
          const [title] = line.split("|");
          return `<div class="bp-numcard"><span class="bp-numcard-num">${String(i + 1).padStart(2, "0")}</span> ${e((title || "").trim())}</div>`;
        }).join("") : '<div class="bp-numcard bp-placeholder">Karten hinzufügen...</div>'}</div>
      </div>`;
    }
    if (block.type === "bento") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 3);
      return `<div class="bp bp-bento">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        <div class="bp-bento-grid">${items.length ? items.map((line, i) => {
          const parts = line.split("|").map((s) => s.trim());
          return `<div class="bp-bento-item ${i === 0 ? 'bp-bento-big' : ''}">${e(parts[1] || parts[0] || "")}</div>`;
        }).join("") : '<div class="bp-bento-item bp-placeholder">Karten...</div>'}</div>
      </div>`;
    }
    if (block.type === "posts") {
      return `<div class="bp bp-posts">
        ${block.eyebrow ? `<div class="bp-eyebrow">${e(block.eyebrow)}</div>` : ""}
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : '<div class="bp-h2">Blog-Posts</div>'}
        <div class="bp-posts-grid"><div class="bp-post-ph"></div><div class="bp-post-ph"></div><div class="bp-post-ph"></div></div>
      </div>`;
    }
    if (block.type === "video") {
      return `<div class="bp bp-video">
        <div class="bp-video-box">${block.url ? `▶ ${e(block.url)}` : '<span class="bp-placeholder">Video-URL...</span>'}</div>
        ${block.caption ? `<div class="bp-caption">${e(block.caption)}</div>` : ""}
      </div>`;
    }
    if (block.type === "gallery") {
      const imgs = (block.images || "").split("\n").filter((l) => l.trim()).slice(0, 6);
      const cols = Number(block.columns) || 3;
      return `<div class="bp bp-gallery">
        <div class="bp-gallery-grid" style="grid-template-columns:repeat(${cols},1fr)">
          ${imgs.length ? imgs.map((line) => {
            const [url] = line.split("|");
            return `<div class="bp-gallery-item">${url ? `<img src="${e(url.trim())}" alt="" />` : ""}</div>`;
          }).join("") : '<div class="bp-gallery-item bp-placeholder">Bilder...</div>'}
        </div>
      </div>`;
    }
    if (block.type === "divider") {
      const sz = block.size || "md";
      const st = block.style || "line";
      const h = sz === "sm" ? 16 : sz === "lg" ? 48 : 32;
      return `<div class="bp bp-divider" style="height:${h}px;display:flex;align-items:center;justify-content:center;">
        ${st === "line" ? '<div style="width:80%;height:1px;background:#ece7df;"></div>' : st === "dots" ? '<div style="letter-spacing:8px;color:#c9936b;">···</div>' : ""}
      </div>`;
    }
    if (block.type === "accordion") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 4);
      return `<div class="bp bp-accordion">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        ${items.length ? items.map((line) => {
          const [q] = line.split("|");
          return `<div class="bp-acc-item">▸ ${e((q || "").trim())}</div>`;
        }).join("") : '<div class="bp-acc-item bp-placeholder">Fragen hinzufügen...</div>'}
      </div>`;
    }
    if (block.type === "stats") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 4);
      return `<div class="bp bp-stats">
        ${block.eyebrow ? `<div class="bp-eyebrow">${e(block.eyebrow)}</div>` : ""}
        <div class="bp-stats-grid">${items.length ? items.map((line) => {
          const [num, label] = line.split("|").map((s) => s.trim());
          return `<div class="bp-stat"><span class="bp-stat-num">${e(num)}</span><span class="bp-stat-label">${e(label || "")}</span></div>`;
        }).join("") : '<div class="bp-stat bp-placeholder">Zahlen...</div>'}</div>
      </div>`;
    }
    if (block.type === "pricing") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 3);
      return `<div class="bp bp-pricing">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        <div class="bp-pricing-grid">${items.length ? items.map((line) => {
          const [name, price] = line.split("|").map((s) => s.trim());
          return `<div class="bp-price-card"><div class="bp-price-name">${e(name)}</div><div class="bp-price-amount">${e(price || "")}</div></div>`;
        }).join("") : '<div class="bp-price-card bp-placeholder">Pakete...</div>'}</div>
      </div>`;
    }
    if (block.type === "quote") {
      return `<div class="bp bp-quote">
        <div class="bp-quote-mark">„</div>
        <div class="bp-quote-text">${block.text ? e(block.text).slice(0, 120) + "..." : '<span class="bp-placeholder">Zitat...</span>'}</div>
        ${block.author ? `<div class="bp-quote-author">— ${e(block.author)}${block.role ? `, ${e(block.role)}` : ""}</div>` : ""}
      </div>`;
    }
    if (block.type === "list") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 6);
      const icon = block.style === "arrow" ? "→" : block.style === "dot" ? "•" : "✓";
      return `<div class="bp bp-list">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        ${items.length ? items.map((item) => `<div class="bp-list-item"><span class="bp-list-icon">${icon}</span> ${e(item.trim())}</div>`).join("") : '<div class="bp-list-item bp-placeholder">Einträge...</div>'}
      </div>`;
    }
    if (block.type === "callout") {
      const st = block.style || "info";
      const icons = { info: "ℹ️", warning: "⚠️", tip: "💡" };
      return `<div class="bp bp-callout bp-callout-${st}">
        <span class="bp-callout-icon">${icons[st] || "ℹ️"}</span>
        <div>
          ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
          ${block.text ? `<div class="bp-sub">${e(block.text).slice(0, 100)}</div>` : ""}
        </div>
      </div>`;
    }
    if (block.type === "timeline") {
      const items = (block.items || "").split("\n").filter((l) => l.trim()).slice(0, 5);
      return `<div class="bp bp-timeline">
        ${block.title ? `<div class="bp-h2">${e(block.title)}</div>` : ""}
        ${items.length ? items.map((line, i) => {
          const [title] = line.split("|");
          return `<div class="bp-tl-item"><span class="bp-tl-dot"></span><span class="bp-tl-text">${e((title || "").trim())}</span></div>`;
        }).join("") : '<div class="bp-tl-item bp-placeholder">Schritte...</div>'}
      </div>`;
    }
    return `<div class="bp"><span class="bp-placeholder">Block: ${e(block.type)}</span></div>`;
  }

  function renderBlocks() {
    const container = $("#blocks-container");
    if (!state.blocks.length) {
      container.innerHTML = '<div class="empty-blocks muted">Keine Blöcke. Füge oben einen hinzu oder nutze den Fallback-Markdown.</div>';
      return;
    }
    container.innerHTML = state.blocks.map((block, i) => {
      const def = BLOCK_TYPES[block.type] || { label: block.type, icon: "?", fields: [] };
      const fieldsHtml = def.fields.map((f) => {
        const val = escapeHtml(block[f.key] || "");
        if (f.type === "textarea-lg") return `<label class="block-field">${f.label}<textarea rows="6" data-block="${i}" data-key="${f.key}">${val}</textarea></label>`;
        if (f.type === "textarea") return `<label class="block-field">${f.label}<textarea rows="3" data-block="${i}" data-key="${f.key}">${val}</textarea></label>`;
        return `<label class="block-field">${f.label}<input data-block="${i}" data-key="${f.key}" value="${val}" /></label>`;
      }).join("");
      return `
        <div class="block-card" data-index="${i}" draggable="true">
          <div class="block-header">
            <span class="block-drag-handle" title="Ziehen zum Verschieben">⠿</span>
            <span class="block-type">${def.icon} ${def.label}</span>
            <div class="block-actions">
              <button type="button" class="btn tiny" data-toggle-block="${i}">✏️</button>
              <button type="button" class="btn tiny danger" data-remove-block="${i}">✕</button>
            </div>
          </div>
          <div class="block-preview" data-preview="${i}">${blockPreview(block)}</div>
          <div class="block-fields" data-fields="${i}" hidden>${fieldsHtml}</div>
        </div>`;
    }).join("");

    // Bind field changes — update preview live
    container.querySelectorAll("[data-block][data-key]").forEach((el) => {
      el.addEventListener("input", () => {
        const idx = Number(el.dataset.block);
        state.blocks[idx][el.dataset.key] = el.value;
        const previewEl = container.querySelector(`[data-preview="${idx}"]`);
        if (previewEl) previewEl.innerHTML = blockPreview(state.blocks[idx]);
      });
    });
    // Toggle edit/preview
    container.querySelectorAll("[data-toggle-block]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = btn.dataset.toggleBlock;
        const fields = container.querySelector(`[data-fields="${i}"]`);
        const preview = container.querySelector(`[data-preview="${i}"]`);
        if (fields && preview) {
          const isEditing = !fields.hidden;
          fields.hidden = isEditing;
          preview.hidden = !isEditing;
          btn.textContent = isEditing ? "✏️" : "👁";
          if (isEditing) preview.innerHTML = blockPreview(state.blocks[Number(i)]);
        }
      });
    });
    // Bind remove
    container.querySelectorAll("[data-remove-block]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.blocks.splice(Number(btn.dataset.removeBlock), 1);
        renderBlocks();
      });
    });
    // Drag-and-drop reordering
    let dragSrc = null;
    container.querySelectorAll(".block-card").forEach((card) => {
      card.addEventListener("dragstart", (ev) => {
        dragSrc = Number(card.dataset.index);
        ev.dataTransfer.effectAllowed = "move";
        card.classList.add("dragging");
      });
      card.addEventListener("dragend", () => {
        card.classList.remove("dragging");
        container.querySelectorAll(".block-card").forEach((c) => c.classList.remove("drag-over"));
      });
      card.addEventListener("dragover", (ev) => {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        container.querySelectorAll(".block-card").forEach((c) => c.classList.remove("drag-over"));
        card.classList.add("drag-over");
      });
      card.addEventListener("drop", (ev) => {
        ev.preventDefault();
        const target = Number(card.dataset.index);
        if (dragSrc === null || dragSrc === target) return;
        const moved = state.blocks.splice(dragSrc, 1)[0];
        state.blocks.splice(target, 0, moved);
        dragSrc = null;
        renderBlocks();
      });
    });
  }

  // Add block buttons (delegated — handles dynamically rendered buttons too)
  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-add-block]");
    if (!btn) return;
    const type = btn.dataset.addBlock;
    const block = { type };
    const def = BLOCK_TYPES[type];
    if (def) def.fields.forEach((f) => { block[f.key] = ""; });
    state.blocks.push(block);
    renderBlocks();
    const last = $("#blocks-container").lastElementChild;
    if (last) last.scrollIntoView({ behavior: "smooth", block: "nearest" });
    // auto-open edit mode for new block
    const idx = state.blocks.length - 1;
    const fields = document.querySelector(`[data-fields="${idx}"]`);
    const preview = document.querySelector(`[data-preview="${idx}"]`);
    const toggleBtn = document.querySelector(`[data-toggle-block="${idx}"]`);
    if (fields && preview) {
      fields.hidden = false;
      preview.hidden = true;
      if (toggleBtn) toggleBtn.textContent = "👁";
    }
  });

  // ---------- Page Builder helpers ----------
  const pbState = {
    title: "", slug: "", excerpt: "", content: "",
    status: "published", sort_order: 0, show_in_menu: true,
    meta_title: "", meta_description: "",
  };

  function pbLoadSettings(p) {
    pbState.title = p.title || "";
    pbState.slug = p.slug || "";
    pbState.excerpt = p.excerpt || "";
    pbState.content = p.content || "";
    pbState.status = p.status || "published";
    pbState.sort_order = p.sort_order || 0;
    pbState.show_in_menu = !!p.show_in_menu;
    pbState.meta_title = p.meta_title || "";
    pbState.meta_description = p.meta_description || "";
    // sync settings drawer
    $("#ps-title").value = pbState.title;
    $("#ps-slug").value = pbState.slug;
    $("#ps-excerpt").value = pbState.excerpt;
    $("#ps-sort-order").value = pbState.sort_order;
    $("#ps-show-in-menu").checked = pbState.show_in_menu;
    $("#ps-meta-title").value = pbState.meta_title;
    $("#ps-meta_description") && ($("#ps-meta-description").value = pbState.meta_description);
  }

  function pbReadSettings() {
    pbState.title = $("#ps-title").value.trim();
    pbState.slug = $("#ps-slug").value.trim();
    pbState.excerpt = $("#ps-excerpt").value.trim();
    pbState.sort_order = Number($("#ps-sort-order").value) || 0;
    pbState.show_in_menu = $("#ps-show-in-menu").checked;
    pbState.meta_title = $("#ps-meta-title").value.trim();
    pbState.meta_description = $("#ps-meta-description").value.trim();
  }

  function pbRefreshPreview() {
    const base = (localStorage.getItem("pb_preview_url") || "http://localhost:4321").replace(/\/$/, "");
    const slug = pbState.slug;
    if (!slug) return;
    const url = slug === "home" ? base + "/" : base + "/" + slug;
    const iframe = $("#pb-iframe");
    if (iframe.src === url) {
      iframe.contentWindow && iframe.contentWindow.location.reload();
    } else {
      iframe.src = url;
    }
  }

  // Preview URL input
  const pbUrlInput = $("#pb-url-input");
  pbUrlInput.value = localStorage.getItem("pb_preview_url") || "http://localhost:4321";
  pbUrlInput.addEventListener("change", () => {
    localStorage.setItem("pb_preview_url", pbUrlInput.value.trim());
    pbRefreshPreview();
  });

  // Device buttons
  $$(".pb-device-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".pb-device-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const wrap = $("#pb-iframe-wrap");
      wrap.dataset.device = btn.dataset.device;
    });
  });

  // Settings drawer
  $("#pb-settings-btn").addEventListener("click", () => {
    pbLoadSettings(pbState);
    $("#pb-settings-overlay").hidden = false;
  });
  $("#pb-settings-close").addEventListener("click", () => {
    pbReadSettings();
    $("#page-editor-title").textContent = pbState.title || "Neue Seite";
    $("#pb-settings-overlay").hidden = true;
  });

  // Vorschau button
  $("#pb-preview-btn").addEventListener("click", () => {
    const base = (localStorage.getItem("pb_preview_url") || "http://localhost:4321").replace(/\/$/, "");
    const url = pbState.slug === "home" ? base + "/" : base + "/" + pbState.slug;
    window.open(url, "_blank");
  });

  function newPage() {
    state.editingPageId = null;
    state.blocks = [];
    pbLoadSettings({ title: "", slug: "", excerpt: "", content: "", status: "published", sort_order: 0, show_in_menu: true, meta_title: "", meta_description: "" });
    $("#page-editor-title").textContent = "Neue Seite";
    $("#page-delete-btn").hidden = true;
    $("#pb-iframe").src = "about:blank";
    renderBlocks();
    showView("page-editor");
  }

  async function editPage(id) {
    try {
      const p = await api(`/api/admin/pages/${id}`);
      state.editingPageId = id;
      state.blocks = Array.isArray(p.blocks) ? p.blocks : [];
      pbLoadSettings(p);
      $("#page-editor-title").textContent = p.title;
      $("#page-delete-btn").hidden = false;
      renderBlocks();
      showView("page-editor");
      // load preview
      setTimeout(pbRefreshPreview, 200);
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  $("#page-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    pbReadSettings();
    const data = {
      title: pbState.title,
      slug: pbState.slug,
      content: pbState.content,
      excerpt: pbState.excerpt,
      status: pbState.status,
      sort_order: pbState.sort_order,
      show_in_menu: pbState.show_in_menu,
      meta_title: pbState.meta_title,
      meta_description: pbState.meta_description,
      blocks: state.blocks,
    };
    try {
      if (state.editingPageId) {
        await api(`/api/admin/pages/${state.editingPageId}`, { method: "PUT", body: data });
        toast("Gespeichert ✓", "success");
      } else {
        const res = await api("/api/admin/pages", { method: "POST", body: data });
        state.editingPageId = res.id;
        pbState.slug = res.slug || pbState.slug;
        $("#page-delete-btn").hidden = false;
        toast("Seite angelegt", "success");
      }
      // refresh preview after save
      setTimeout(pbRefreshPreview, 400);
    } catch (err) {
      toast(`Fehler: ${err.message}`, "error");
    }
  });

  $("#page-delete-btn").addEventListener("click", async () => {
    if (!state.editingPageId) return;
    if (!confirm("Diese Seite wirklich löschen?")) return;
    try {
      await api(`/api/admin/pages/${state.editingPageId}`, { method: "DELETE" });
      toast("Gelöscht", "success");
      showView("pages");
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });

  // ---------- Posts ----------
  async function loadPosts() {
    try {
      const rows = await api("/api/admin/posts");
      const container = $("#posts-list");
      if (!rows.length) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="icon">✎</div>
            <p>Noch keine Blogposts.</p>
            <button class="btn primary" onclick="document.getElementById('btn-new-post').click()">+ Ersten Beitrag schreiben</button>
          </div>`;
        return;
      }
      container.innerHTML = `
        <table class="data-table">
          <thead><tr><th>Titel</th><th>Status</th><th>Tags</th><th>Veröffentlicht</th><th></th></tr></thead>
          <tbody>
            ${rows.map((p) => `
              <tr>
                <td><div class="row-title">${escapeHtml(p.title)}</div><div class="row-sub">${escapeHtml(p.excerpt || "")}</div></td>
                <td><span class="badge ${p.status}">${p.status === "published" ? "Live" : "Entwurf"}</span></td>
                <td>${(p.tags || []).map((t) => `<span class="badge tag">${escapeHtml(t.name)}</span>`).join("")}</td>
                <td>${formatDate(p.published_at || p.created_at)}</td>
                <td><button class="btn small" data-edit-post="${p.id}">Bearbeiten</button></td>
              </tr>`).join("")}
          </tbody>
        </table>`;
      container.querySelectorAll("[data-edit-post]").forEach((b) =>
        b.addEventListener("click", () => editPost(Number(b.dataset.editPost)))
      );
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  $("#btn-new-post").addEventListener("click", () => newPost());

  function newPost() {
    state.editingPostId = null;
    const f = $("#post-form");
    f.reset();
    f.status.value = "draft";
    $("#post-editor-title").textContent = "Neuer Blogpost";
    $("#post-delete-btn").hidden = true;
    $("#post-preview").hidden = true;
    showView("post-editor");
  }

  async function editPost(id) {
    try {
      const p = await api(`/api/admin/posts/${id}`);
      state.editingPostId = id;
      const f = $("#post-form");
      f.title.value = p.title;
      f.slug.value = p.slug;
      f.excerpt.value = p.excerpt;
      f.content.value = p.content;
      f.cover_image.value = p.cover_image;
      f.status.value = p.status;
      f.tags.value = (p.tags || []).map((t) => t.name).join(", ");
      f.meta_title.value = p.meta_title;
      f.meta_description.value = p.meta_description;
      $("#post-editor-title").textContent = `Beitrag: ${p.title}`;
      $("#post-delete-btn").hidden = false;
      $("#post-preview").hidden = true;
      showView("post-editor");
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  $("#post-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const data = {
      title: f.title.value.trim(),
      slug: f.slug.value.trim(),
      excerpt: f.excerpt.value,
      content: f.content.value,
      cover_image: f.cover_image.value.trim(),
      status: f.status.value,
      tags: f.tags.value.split(",").map((t) => t.trim()).filter(Boolean),
      meta_title: f.meta_title.value,
      meta_description: f.meta_description.value,
    };
    try {
      if (state.editingPostId) {
        await api(`/api/admin/posts/${state.editingPostId}`, { method: "PUT", body: data });
        toast("Beitrag gespeichert", "success");
      } else {
        const res = await api("/api/admin/posts", { method: "POST", body: data });
        state.editingPostId = res.id;
        $("#post-delete-btn").hidden = false;
        toast("Beitrag angelegt", "success");
      }
    } catch (err) {
      toast(`Fehler: ${err.message}`, "error");
    }
  });

  $("#post-delete-btn").addEventListener("click", async () => {
    if (!state.editingPostId) return;
    if (!confirm("Diesen Beitrag wirklich löschen?")) return;
    try {
      await api(`/api/admin/posts/${state.editingPostId}`, { method: "DELETE" });
      toast("Gelöscht", "success");
      showView("posts");
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });

  $("#post-preview-btn").addEventListener("click", async () => {
    const content = $("#post-form").content.value;
    try {
      const res = await api("/api/admin/preview", { method: "POST", body: { content } });
      const box = $("#post-preview");
      box.innerHTML = res.html;
      box.hidden = false;
      box.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });

  // ---------- Media ----------
  async function loadMedia() {
    try {
      const items = await api("/api/admin/media");
      const grid = $("#media-grid");
      if (!items.length) {
        grid.innerHTML = '<p class="muted" style="grid-column:1/-1;padding:20px;text-align:center;">Noch keine Medien hochgeladen.</p>';
        return;
      }
      grid.innerHTML = items.map((m) => `
        <div class="media-item" data-id="${m.id}" data-url="${escapeHtml(m.url)}">
          <div class="thumb"><img src="${escapeHtml(m.url)}" alt="${escapeHtml(m.alt || m.original_name)}" /></div>
          <div class="info">
            <div class="name">${escapeHtml(m.original_name)}</div>
            <div class="size">${formatSize(m.size)}</div>
          </div>
        </div>
      `).join("");
      grid.querySelectorAll(".media-item").forEach((el) =>
        el.addEventListener("click", () => openMediaDetail(Number(el.dataset.id), el.dataset.url))
      );
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  async function openMediaDetail(id, url) {
    const action = prompt(
      `Bild-URL: ${url}\n\nEingabe:\n  [Leer] schließen\n  "copy" URL in Zwischenablage\n  "delete" Bild löschen`,
      ""
    );
    if (!action) return;
    if (action === "copy") {
      try {
        await navigator.clipboard.writeText(window.location.origin + url);
        toast("URL kopiert", "success");
      } catch {
        toast("Kopieren nicht möglich", "error");
      }
    } else if (action === "delete") {
      if (!confirm("Dieses Bild wirklich löschen?")) return;
      try {
        await api(`/api/admin/media/${id}`, { method: "DELETE" });
        toast("Gelöscht", "success");
        loadMedia();
      } catch (e) {
        toast(`Fehler: ${e.message}`, "error");
      }
    }
  }

  const uploadZone = $("#upload-zone");
  const uploadInput = $("#upload-input");
  uploadInput.addEventListener("change", (e) => handleUpload(e.target.files[0]));
  ["dragover", "dragenter"].forEach((ev) =>
    uploadZone.addEventListener(ev, (e) => {
      e.preventDefault();
      uploadZone.classList.add("drag-over");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    uploadZone.addEventListener(ev, (e) => {
      e.preventDefault();
      uploadZone.classList.remove("drag-over");
    })
  );
  uploadZone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files[0]);
  });

  async function handleUpload(file) {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("alt", "");
    try {
      await api("/api/admin/media", { method: "POST", body: fd });
      toast("Hochgeladen", "success");
      loadMedia();
      uploadInput.value = "";
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  // ---------- Media picker ----------
  $("#pick-cover-btn").addEventListener("click", async () => {
    try {
      const items = await api("/api/admin/media");
      const grid = $("#media-picker-grid");
      if (!items.length) {
        grid.innerHTML = '<p class="muted">Noch keine Bilder hochgeladen.</p>';
      } else {
        grid.innerHTML = items.map((m) => `
          <div class="media-item" data-url="${escapeHtml(m.url)}">
            <div class="thumb"><img src="${escapeHtml(m.url)}" alt="" /></div>
            <div class="info"><div class="name">${escapeHtml(m.original_name)}</div></div>
          </div>
        `).join("");
        grid.querySelectorAll(".media-item").forEach((el) =>
          el.addEventListener("click", () => {
            $("#post-form").cover_image.value = el.dataset.url;
            $("#media-picker").hidden = true;
            toast("Bild zugewiesen", "success");
          })
        );
      }
      $("#media-picker").hidden = false;
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });
  $("#media-picker-cancel").addEventListener("click", () => {
    $("#media-picker").hidden = true;
  });

  // ---------- Keyboard shortcut ----------
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      const form = document.querySelector(".view:not([hidden]) form");
      if (form) {
        e.preventDefault();
        form.requestSubmit();
      }
    }
  });

  // ---------- Init ----------
  loadMe();
  loadDashboard();
})();
