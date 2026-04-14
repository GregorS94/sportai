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

  function newPage() {
    state.editingPageId = null;
    const f = $("#page-form");
    f.reset();
    f.querySelector('[name="status"]').value = "draft";
    f.querySelector('[name="sort_order"]').value = "0";
    f.querySelector('[name="show_in_menu"]').checked = true;
    $("#page-editor-title").textContent = "Neue Seite";
    $("#page-delete-btn").hidden = true;
    $("#page-preview").hidden = true;
    showView("page-editor");
  }

  async function editPage(id) {
    try {
      const p = await api(`/api/admin/pages/${id}`);
      state.editingPageId = id;
      const f = $("#page-form");
      f.title.value = p.title;
      f.slug.value = p.slug;
      f.content.value = p.content;
      f.excerpt.value = p.excerpt;
      f.status.value = p.status;
      f.sort_order.value = p.sort_order;
      f.show_in_menu.checked = !!p.show_in_menu;
      f.meta_title.value = p.meta_title;
      f.meta_description.value = p.meta_description;
      $("#page-editor-title").textContent = `Seite: ${p.title}`;
      $("#page-delete-btn").hidden = false;
      $("#page-preview").hidden = true;
      showView("page-editor");
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  $("#page-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const data = {
      title: f.title.value.trim(),
      slug: f.slug.value.trim(),
      content: f.content.value,
      excerpt: f.excerpt.value,
      status: f.status.value,
      sort_order: Number(f.sort_order.value) || 0,
      show_in_menu: f.show_in_menu.checked,
      meta_title: f.meta_title.value,
      meta_description: f.meta_description.value,
    };
    try {
      if (state.editingPageId) {
        await api(`/api/admin/pages/${state.editingPageId}`, { method: "PUT", body: data });
        toast("Seite gespeichert", "success");
      } else {
        const res = await api("/api/admin/pages", { method: "POST", body: data });
        state.editingPageId = res.id;
        $("#page-delete-btn").hidden = false;
        toast("Seite angelegt", "success");
      }
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

  $("#page-preview-btn").addEventListener("click", async () => {
    const content = $("#page-form").content.value;
    try {
      const res = await api("/api/admin/preview", { method: "POST", body: { content } });
      const box = $("#page-preview");
      box.innerHTML = res.html;
      box.hidden = false;
      box.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
