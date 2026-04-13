/* Newsletter Designer – block-based editor */
(() => {
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const uid = () => Math.random().toString(36).slice(2, 10);

  const state = {
    id: null,
    name: "",
    subject: "",
    preheader: "",
    blocks: [],
    selectedId: null,
    dirty: false,
  };

  // ---------- API helper ----------
  async function api(path, options = {}) {
    const opts = { headers: {}, ...options };
    if (opts.body && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
      if (typeof opts.body !== "string") opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, opts);
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

  function toast(msg, kind = "") {
    const bar = $("#status-bar");
    bar.textContent = msg;
    bar.className = `status-bar show ${kind}`;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => bar.classList.remove("show"), 3500);
  }

  // ---------- Block defaults ----------
  const BLOCK_DEFAULTS = {
    heading: { level: "h2", text: "Deine Überschrift", color: "#111111", align: "left" },
    text: {
      text: "Schreibe hier deinen Text. Platzhalter wie {{name}} werden beim Versand ersetzt.",
      color: "#333333",
      size: "16px",
      align: "left",
    },
    image: {
      src: "",
      alt: "Bild",
      width: 560,
      align: "center",
      link: "",
    },
    button: {
      text: "Mehr erfahren",
      url: "https://",
      bg_color: "#2563eb",
      text_color: "#ffffff",
      align: "center",
    },
    divider: { color: "#e5e7eb" },
    spacer: { height: 24 },
  };

  function createBlock(type) {
    return {
      id: uid(),
      type,
      props: JSON.parse(JSON.stringify(BLOCK_DEFAULTS[type] || {})),
    };
  }

  // ---------- Load existing newsletter ----------
  async function load() {
    const url = new URL(window.location.href);
    const id = url.searchParams.get("id");
    if (!id) {
      toast("Keine Newsletter-ID angegeben", "error");
      return;
    }
    state.id = Number(id);
    try {
      const data = await api(`/api/newsletters/${id}`);
      state.name = data.name;
      state.subject = data.subject || "";
      state.preheader = data.preheader || "";
      // Ensure each block has an id for selection tracking
      state.blocks = (data.blocks || []).map((b) => ({ ...b, id: b.id || uid() }));
      $("#newsletter-name").value = state.name;
      $("#newsletter-subject").value = state.subject;
      $("#newsletter-preheader").value = state.preheader;
      renderCanvas();
    } catch (e) {
      toast(`Fehler beim Laden: ${e.message}`, "error");
    }
  }

  // ---------- Rendering ----------
  function renderCanvas() {
    const canvas = $("#canvas");
    if (!state.blocks.length) {
      canvas.innerHTML =
        '<div class="canvas-empty">Füge links Blöcke hinzu, um deinen Newsletter zu gestalten.</div>';
      return;
    }
    canvas.innerHTML = state.blocks
      .map(
        (b) => `
      <div class="block ${state.selectedId === b.id ? "selected" : ""}"
           data-block-id="${b.id}" draggable="true">
        <div class="block-toolbar">
          <button data-action="up" title="Nach oben">↑</button>
          <button data-action="down" title="Nach unten">↓</button>
          <button data-action="duplicate" title="Duplizieren">⧉</button>
          <button data-action="delete" title="Löschen">✕</button>
        </div>
        ${renderBlockInline(b)}
      </div>`
      )
      .join("");
    attachBlockListeners();
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderBlockInline(b) {
    const p = b.props || {};
    const align = p.align || "left";
    switch (b.type) {
      case "heading": {
        const sz = { h1: "32px", h2: "24px", h3: "20px" }[p.level || "h2"];
        return `<div style="padding:16px 24px 8px;text-align:${align};
          font-family:Arial,sans-serif;font-size:${sz};font-weight:bold;
          color:${p.color || "#111"};line-height:1.25;">${escapeHtml(p.text)}</div>`;
      }
      case "text": {
        const html = (p.text || "").split("\n").map(escapeHtml).join("<br />");
        return `<div style="padding:8px 24px;text-align:${align};
          font-family:Arial,sans-serif;font-size:${p.size || "16px"};
          color:${p.color || "#333"};line-height:1.6;">${html}</div>`;
      }
      case "image": {
        if (!p.src) {
          return `<div style="padding:30px 24px;text-align:${align};
            color:#9ca3af;font-style:italic;background:#f9fafb;
            border:1px dashed #e5e7eb;margin:16px 24px;border-radius:4px;">
            🖼 Bild – URL in den Eigenschaften setzen</div>`;
        }
        return `<div style="padding:16px 24px;text-align:${align};">
          <img src="${escapeHtml(p.src)}" alt="${escapeHtml(p.alt || "")}"
               style="max-width:100%;height:auto;display:inline-block;"
               width="${p.width || 560}" /></div>`;
      }
      case "button": {
        return `<div style="padding:16px 24px;text-align:${align};">
          <span style="display:inline-block;padding:12px 24px;border-radius:6px;
            background:${p.bg_color || "#2563eb"};color:${p.text_color || "#fff"};
            font-family:Arial,sans-serif;font-weight:bold;font-size:16px;">
            ${escapeHtml(p.text || "Button")}</span></div>`;
      }
      case "divider": {
        return `<div style="padding:12px 24px;">
          <div style="height:1px;background:${p.color || "#e5e7eb"};"></div></div>`;
      }
      case "spacer": {
        return `<div style="height:${p.height || 24}px;"></div>`;
      }
      default:
        return `<div style="padding:20px;color:#999;">Unbekannter Blocktyp: ${b.type}</div>`;
    }
  }

  // ---------- Block interactions ----------
  function attachBlockListeners() {
    $$(".block").forEach((el) => {
      const id = el.dataset.blockId;
      el.addEventListener("click", (e) => {
        if (e.target.closest(".block-toolbar")) return;
        selectBlock(id);
      });
      el.querySelectorAll(".block-toolbar button").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          handleBlockAction(id, btn.dataset.action);
        });
      });

      // Drag-and-drop reordering
      el.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", id);
        e.dataTransfer.effectAllowed = "move";
      });
      el.addEventListener("dragover", (e) => {
        e.preventDefault();
        const rect = el.getBoundingClientRect();
        const before = (e.clientY - rect.top) < rect.height / 2;
        el.classList.toggle("drag-over-top", before);
        el.classList.toggle("drag-over-bottom", !before);
      });
      el.addEventListener("dragleave", () => {
        el.classList.remove("drag-over-top", "drag-over-bottom");
      });
      el.addEventListener("drop", (e) => {
        e.preventDefault();
        const sourceId = e.dataTransfer.getData("text/plain");
        const rect = el.getBoundingClientRect();
        const before = (e.clientY - rect.top) < rect.height / 2;
        el.classList.remove("drag-over-top", "drag-over-bottom");
        moveBlock(sourceId, id, before);
      });
    });
  }

  function selectBlock(id) {
    state.selectedId = id;
    renderCanvas();
    renderProps();
  }

  function handleBlockAction(id, action) {
    const idx = state.blocks.findIndex((b) => b.id === id);
    if (idx === -1) return;
    if (action === "up" && idx > 0) {
      [state.blocks[idx - 1], state.blocks[idx]] = [state.blocks[idx], state.blocks[idx - 1]];
    } else if (action === "down" && idx < state.blocks.length - 1) {
      [state.blocks[idx + 1], state.blocks[idx]] = [state.blocks[idx], state.blocks[idx + 1]];
    } else if (action === "delete") {
      state.blocks.splice(idx, 1);
      if (state.selectedId === id) state.selectedId = null;
    } else if (action === "duplicate") {
      const copy = JSON.parse(JSON.stringify(state.blocks[idx]));
      copy.id = uid();
      state.blocks.splice(idx + 1, 0, copy);
    } else {
      return;
    }
    state.dirty = true;
    renderCanvas();
    renderProps();
  }

  function moveBlock(sourceId, targetId, before) {
    if (sourceId === targetId) return;
    const srcIdx = state.blocks.findIndex((b) => b.id === sourceId);
    if (srcIdx === -1) return;
    const [item] = state.blocks.splice(srcIdx, 1);
    let tgtIdx = state.blocks.findIndex((b) => b.id === targetId);
    if (tgtIdx === -1) {
      state.blocks.push(item);
    } else {
      state.blocks.splice(before ? tgtIdx : tgtIdx + 1, 0, item);
    }
    state.dirty = true;
    renderCanvas();
  }

  // ---------- Add blocks ----------
  $$(".block-add").forEach((btn) => {
    btn.addEventListener("click", () => {
      const block = createBlock(btn.dataset.block);
      state.blocks.push(block);
      state.selectedId = block.id;
      state.dirty = true;
      renderCanvas();
      renderProps();
    });
  });

  // ---------- Properties panel ----------
  function renderProps() {
    const wrap = $("#props-content");
    const empty = $("#props-empty");
    const block = state.blocks.find((b) => b.id === state.selectedId);
    if (!block) {
      wrap.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    wrap.innerHTML = propsForm(block);

    wrap.querySelectorAll("[data-prop]").forEach((input) => {
      input.addEventListener("input", () => {
        const key = input.dataset.prop;
        let value = input.type === "number" ? Number(input.value) : input.value;
        block.props[key] = value;
        state.dirty = true;
        // Sync color text with picker
        if (input.type === "color") {
          const text = wrap.querySelector(`[data-prop-text="${key}"]`);
          if (text) text.value = value;
        }
        if (input.dataset.propText) {
          const picker = wrap.querySelector(`input[type="color"][data-prop="${input.dataset.propText}"]`);
          if (picker) picker.value = value;
          block.props[input.dataset.propText] = value;
        }
        renderCanvasThrottled();
      });
    });
  }

  let renderTimer = null;
  function renderCanvasThrottled() {
    clearTimeout(renderTimer);
    renderTimer = setTimeout(renderCanvas, 100);
  }

  function alignField(p) {
    return `
      <div class="prop-group">
        <label>Ausrichtung</label>
        <select data-prop="align">
          <option value="left" ${p.align === "left" ? "selected" : ""}>Links</option>
          <option value="center" ${p.align === "center" ? "selected" : ""}>Zentriert</option>
          <option value="right" ${p.align === "right" ? "selected" : ""}>Rechts</option>
        </select>
      </div>`;
  }

  function colorField(label, key, value) {
    return `
      <div class="prop-group">
        <label>${label}</label>
        <div class="color-row">
          <input type="color" data-prop="${key}" value="${value}" />
          <input type="text" data-prop-text="${key}" value="${value}" />
        </div>
      </div>`;
  }

  function propsForm(b) {
    const p = b.props || {};
    switch (b.type) {
      case "heading":
        return `
          <div class="prop-group">
            <label>Text</label>
            <input type="text" data-prop="text" value="${escapeHtml(p.text)}" />
          </div>
          <div class="prop-group">
            <label>Ebene</label>
            <select data-prop="level">
              <option value="h1" ${p.level === "h1" ? "selected" : ""}>H1 – Groß</option>
              <option value="h2" ${p.level === "h2" ? "selected" : ""}>H2 – Mittel</option>
              <option value="h3" ${p.level === "h3" ? "selected" : ""}>H3 – Klein</option>
            </select>
          </div>
          ${colorField("Farbe", "color", p.color || "#111111")}
          ${alignField(p)}
        `;
      case "text":
        return `
          <div class="prop-group">
            <label>Text (Zeilenumbrüche erlaubt)</label>
            <textarea data-prop="text" rows="6">${escapeHtml(p.text)}</textarea>
          </div>
          <div class="prop-group">
            <label>Schriftgröße</label>
            <select data-prop="size">
              <option value="14px" ${p.size === "14px" ? "selected" : ""}>14px</option>
              <option value="16px" ${p.size === "16px" ? "selected" : ""}>16px</option>
              <option value="18px" ${p.size === "18px" ? "selected" : ""}>18px</option>
              <option value="20px" ${p.size === "20px" ? "selected" : ""}>20px</option>
            </select>
          </div>
          ${colorField("Textfarbe", "color", p.color || "#333333")}
          ${alignField(p)}
        `;
      case "image":
        return `
          <div class="prop-group">
            <label>Bild-URL</label>
            <input type="url" data-prop="src" value="${escapeHtml(p.src)}"
              placeholder="https://..." />
          </div>
          <div class="prop-group">
            <label>Alternativtext</label>
            <input type="text" data-prop="alt" value="${escapeHtml(p.alt)}" />
          </div>
          <div class="prop-group">
            <label>Breite (px)</label>
            <input type="number" data-prop="width" value="${p.width || 560}" min="50" max="600" />
          </div>
          <div class="prop-group">
            <label>Ziel-URL beim Klick (optional)</label>
            <input type="url" data-prop="link" value="${escapeHtml(p.link || "")}" />
          </div>
          ${alignField(p)}
        `;
      case "button":
        return `
          <div class="prop-group">
            <label>Button-Text</label>
            <input type="text" data-prop="text" value="${escapeHtml(p.text)}" />
          </div>
          <div class="prop-group">
            <label>URL</label>
            <input type="url" data-prop="url" value="${escapeHtml(p.url)}" />
          </div>
          ${colorField("Hintergrund", "bg_color", p.bg_color || "#2563eb")}
          ${colorField("Textfarbe", "text_color", p.text_color || "#ffffff")}
          ${alignField(p)}
        `;
      case "divider":
        return colorField("Linienfarbe", "color", p.color || "#e5e7eb");
      case "spacer":
        return `
          <div class="prop-group">
            <label>Höhe (px)</label>
            <input type="number" data-prop="height" value="${p.height || 24}" min="1" max="200" />
          </div>`;
      default:
        return "";
    }
  }

  // ---------- Top-bar fields ----------
  $("#newsletter-name").addEventListener("input", (e) => {
    state.name = e.target.value;
    state.dirty = true;
  });
  $("#newsletter-subject").addEventListener("input", (e) => {
    state.subject = e.target.value;
    state.dirty = true;
  });
  $("#newsletter-preheader").addEventListener("input", (e) => {
    state.preheader = e.target.value;
    state.dirty = true;
  });

  // ---------- Save ----------
  async function save() {
    if (!state.name.trim()) {
      toast("Bitte Name vergeben", "error");
      return false;
    }
    try {
      await api(`/api/newsletters/${state.id}`, {
        method: "PUT",
        body: {
          name: state.name,
          subject: state.subject,
          preheader: state.preheader,
          blocks: state.blocks.map(({ id, type, props }) => ({ id, type, props })),
        },
      });
      state.dirty = false;
      toast("Gespeichert", "success");
      return true;
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
      return false;
    }
  }
  $("#btn-save").addEventListener("click", save);

  // Ctrl/Cmd+S shortcut
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      save();
    }
  });
  window.addEventListener("beforeunload", (e) => {
    if (state.dirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });

  // ---------- Preview ----------
  $("#btn-preview").addEventListener("click", async () => {
    try {
      const html = await api("/api/preview", {
        method: "POST",
        body: {
          blocks: state.blocks.map(({ id, type, props }) => ({ id, type, props })),
          subject: state.subject,
          preheader: state.preheader,
        },
      });
      const frame = $("#preview-frame");
      frame.srcdoc = html;
      $("#preview-modal").hidden = false;
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });
  $("#btn-preview-close").addEventListener("click", () => {
    $("#preview-modal").hidden = true;
  });

  // ---------- Send ----------
  $("#btn-send").addEventListener("click", async () => {
    if (state.dirty) {
      const ok = await save();
      if (!ok) return;
    }
    try {
      const lists = await api("/api/lists");
      const select = $("#send-list-select");
      if (!lists.length) {
        select.innerHTML = '<option value="">(Keine Listen vorhanden)</option>';
      } else {
        select.innerHTML = lists
          .map(
            (l) => `<option value="${l.id}">${escapeHtml(l.name)} (${l.recipient_count})</option>`
          )
          .join("");
      }
      $("#send-status").textContent = "";
      $("#test-email-input").value = "";
      $("#send-modal").hidden = false;
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });
  $("#btn-send-cancel").addEventListener("click", () => ($("#send-modal").hidden = true));
  $("#btn-send-confirm").addEventListener("click", async () => {
    const listId = $("#send-list-select").value;
    if (!listId) return toast("Bitte Liste wählen", "error");
    if (!confirm("Newsletter jetzt wirklich versenden?")) return;
    $("#send-status").textContent = "Versand wird gestartet…";
    try {
      const res = await api(`/api/newsletters/${state.id}/send`, {
        method: "POST",
        body: { list_id: Number(listId) },
      });
      $("#send-status").textContent = `Versand gestartet an ${res.recipients} Empfänger.`;
      toast("Versand läuft im Hintergrund", "success");
    } catch (e) {
      $("#send-status").textContent = `Fehler: ${e.message}`;
      toast(`Fehler: ${e.message}`, "error");
    }
  });
  $("#btn-send-test").addEventListener("click", async () => {
    const email = $("#test-email-input").value.trim();
    if (!email) return toast("Bitte E-Mail eingeben", "error");
    if (state.dirty) {
      const ok = await save();
      if (!ok) return;
    }
    $("#send-status").textContent = "Test-Mail wird gesendet…";
    try {
      await api(`/api/newsletters/${state.id}/test`, {
        method: "POST",
        body: { test_email: email },
      });
      $("#send-status").textContent = `Test-Mail an ${email} gesendet.`;
      toast("Test-Mail gesendet", "success");
    } catch (e) {
      $("#send-status").textContent = `Fehler: ${e.message}`;
      toast(`Fehler: ${e.message}`, "error");
    }
  });

  // ---------- Init ----------
  load();
})();
