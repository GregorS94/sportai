/* Newsletter Mailing – dashboard logic */
(() => {
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  const state = {
    selectedListId: null,
    lists: [],
    pendingSendNewsletterId: null,
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
        const data = await res.json();
        msg = data.detail || JSON.stringify(data);
      } catch (_) {
        /* ignore */
      }
      throw new Error(msg);
    }
    if (res.status === 204) return null;
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  // ---------- Status bar ----------
  function toast(msg, kind = "") {
    const bar = $("#status-bar");
    bar.textContent = msg;
    bar.className = `status-bar show ${kind}`;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => bar.classList.remove("show"), 3500);
  }

  // ---------- Tabs ----------
  $$(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".tab-btn").forEach((b) => b.classList.remove("active"));
      $$(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      $(`#tab-${btn.dataset.tab}`).classList.add("active");
      if (btn.dataset.tab === "newsletters") loadNewsletters();
      if (btn.dataset.tab === "lists") loadLists();
      if (btn.dataset.tab === "history") loadCampaigns();
      if (btn.dataset.tab === "settings") loadSettings();
    });
  });

  // ---------- Newsletters ----------
  async function loadNewsletters() {
    try {
      const items = await api("/api/newsletters");
      const container = $("#newsletters-list");
      if (!items.length) {
        container.innerHTML =
          '<p class="muted">Noch keine Newsletter angelegt. Klicke auf „Neuer Newsletter".</p>';
        return;
      }
      container.innerHTML = items
        .map(
          (n) => `
        <div class="card">
          <h3>${escapeHtml(n.name)}</h3>
          <div class="card-subject">${escapeHtml(n.subject || "(kein Betreff)")}</div>
          <div class="card-meta">Zuletzt aktualisiert: ${formatDate(n.updated_at)}</div>
          <div class="card-actions">
            <a class="btn small" href="/designer?id=${n.id}">✎ Bearbeiten</a>
            <button class="btn small" data-preview="${n.id}">👁 Vorschau</button>
            <button class="btn small primary" data-send="${n.id}">📤 Senden</button>
            <button class="btn small" data-duplicate="${n.id}">⧉</button>
            <button class="btn small danger" data-delete="${n.id}">✕</button>
          </div>
        </div>`
        )
        .join("");

      container.querySelectorAll("[data-preview]").forEach((b) =>
        b.addEventListener("click", () => openPreview(b.dataset.preview))
      );
      container.querySelectorAll("[data-send]").forEach((b) =>
        b.addEventListener("click", () => openSendModal(b.dataset.send))
      );
      container.querySelectorAll("[data-duplicate]").forEach((b) =>
        b.addEventListener("click", async () => {
          try {
            await api(`/api/newsletters/${b.dataset.duplicate}/duplicate`, { method: "POST" });
            toast("Newsletter dupliziert", "success");
            loadNewsletters();
          } catch (e) {
            toast(`Fehler: ${e.message}`, "error");
          }
        })
      );
      container.querySelectorAll("[data-delete]").forEach((b) =>
        b.addEventListener("click", async () => {
          if (!confirm("Diesen Newsletter wirklich löschen?")) return;
          try {
            await api(`/api/newsletters/${b.dataset.delete}`, { method: "DELETE" });
            toast("Gelöscht", "success");
            loadNewsletters();
          } catch (e) {
            toast(`Fehler: ${e.message}`, "error");
          }
        })
      );
    } catch (e) {
      toast(`Fehler beim Laden: ${e.message}`, "error");
    }
  }

  // ---------- New newsletter dialog ----------
  $("#btn-new-newsletter").addEventListener("click", () => {
    $("#new-nl-name").value = "";
    $("#new-nl-subject").value = "";
    $("#newsletter-modal").hidden = false;
    $("#new-nl-name").focus();
  });
  $("#btn-nl-cancel").addEventListener("click", () => {
    $("#newsletter-modal").hidden = true;
  });
  $("#btn-nl-create").addEventListener("click", async () => {
    const name = $("#new-nl-name").value.trim();
    if (!name) {
      toast("Bitte Name eingeben", "error");
      return;
    }
    try {
      const res = await api("/api/newsletters", {
        method: "POST",
        body: { name, subject: $("#new-nl-subject").value.trim(), blocks: [] },
      });
      $("#newsletter-modal").hidden = true;
      window.location.href = `/designer?id=${res.id}`;
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });

  // ---------- Preview ----------
  function openPreview(id) {
    $("#preview-frame").src = `/api/newsletters/${id}/preview`;
    $("#preview-modal").hidden = false;
  }
  $("#btn-preview-close").addEventListener("click", () => {
    $("#preview-modal").hidden = true;
    $("#preview-frame").src = "about:blank";
  });

  // ---------- Send modal ----------
  async function openSendModal(id) {
    state.pendingSendNewsletterId = id;
    $("#send-status").textContent = "";
    $("#test-email-input").value = "";
    const select = $("#send-list-select");
    try {
      const lists = await api("/api/lists");
      if (!lists.length) {
        select.innerHTML = '<option value="">(Keine Listen vorhanden)</option>';
      } else {
        select.innerHTML = lists
          .map(
            (l) => `<option value="${l.id}">${escapeHtml(l.name)} (${l.recipient_count})</option>`
          )
          .join("");
      }
      $("#send-modal").hidden = false;
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }
  $("#btn-send-cancel").addEventListener("click", () => {
    $("#send-modal").hidden = true;
  });
  $("#btn-send-confirm").addEventListener("click", async () => {
    const listId = $("#send-list-select").value;
    if (!listId) {
      toast("Bitte Liste wählen", "error");
      return;
    }
    if (!confirm(`Newsletter jetzt wirklich senden?`)) return;
    $("#send-status").textContent = "Versand wird gestartet…";
    try {
      const res = await api(
        `/api/newsletters/${state.pendingSendNewsletterId}/send`,
        { method: "POST", body: { list_id: Number(listId) } }
      );
      $("#send-status").textContent = `Versand gestartet an ${res.recipients} Empfänger.`;
      toast("Versand läuft im Hintergrund", "success");
    } catch (e) {
      $("#send-status").textContent = `Fehler: ${e.message}`;
      toast(`Fehler: ${e.message}`, "error");
    }
  });
  $("#btn-send-test").addEventListener("click", async () => {
    const email = $("#test-email-input").value.trim();
    if (!email) {
      toast("Bitte E-Mail eingeben", "error");
      return;
    }
    $("#send-status").textContent = "Test-Mail wird gesendet…";
    try {
      await api(`/api/newsletters/${state.pendingSendNewsletterId}/test`, {
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

  // ---------- Lists ----------
  async function loadLists() {
    try {
      state.lists = await api("/api/lists");
      const ul = $("#lists-list");
      if (!state.lists.length) {
        ul.innerHTML = '<li class="muted" style="cursor:default;">Keine Listen vorhanden.</li>';
        $("#recipients-actions").style.display = "none";
        $("#recipients-hint").textContent = "Erstelle zuerst eine Liste.";
        return;
      }
      ul.innerHTML = state.lists
        .map(
          (l) => `
        <li data-list-id="${l.id}" class="${state.selectedListId === l.id ? "active" : ""}">
          <div class="info">
            <strong>${escapeHtml(l.name)}</strong>
            <small>${l.recipient_count} Empfänger</small>
          </div>
          <button class="btn small danger" data-delete-list="${l.id}">✕</button>
        </li>`
        )
        .join("");
      ul.querySelectorAll("li[data-list-id]").forEach((li) =>
        li.addEventListener("click", (e) => {
          if (e.target.dataset.deleteList) return;
          state.selectedListId = Number(li.dataset.listId);
          loadLists();
          loadRecipients();
        })
      );
      ul.querySelectorAll("[data-delete-list]").forEach((b) =>
        b.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (!confirm("Liste inkl. aller Empfänger löschen?")) return;
          try {
            await api(`/api/lists/${b.dataset.deleteList}`, { method: "DELETE" });
            if (state.selectedListId === Number(b.dataset.deleteList)) {
              state.selectedListId = null;
            }
            toast("Liste gelöscht", "success");
            loadLists();
            loadRecipients();
          } catch (err) {
            toast(`Fehler: ${err.message}`, "error");
          }
        })
      );
      if (state.selectedListId) loadRecipients();
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  async function loadRecipients() {
    if (!state.selectedListId) {
      $("#recipients-actions").style.display = "none";
      $("#recipients-hint").textContent = "Wähle eine Liste links aus.";
      $("#recipients-list")?.remove();
      $("#recipient-count").textContent = "0";
      return;
    }
    try {
      const rows = await api(`/api/recipients?list_id=${state.selectedListId}`);
      $("#recipient-count").textContent = String(rows.length);
      $("#recipients-hint").textContent = "";
      $("#recipients-actions").style.display = "block";
      const ul = $("#recipients-list");
      if (!rows.length) {
        ul.innerHTML = '<li class="muted" style="cursor:default;">Noch keine Empfänger.</li>';
        return;
      }
      ul.innerHTML = rows
        .map(
          (r) => `
        <li>
          <div class="info">
            <strong>${escapeHtml(r.email)}</strong>
            <small>${escapeHtml(r.name || "")}</small>
          </div>
          <button class="btn small danger" data-delete-recipient="${r.id}">✕</button>
        </li>`
        )
        .join("");
      ul.querySelectorAll("[data-delete-recipient]").forEach((b) =>
        b.addEventListener("click", async () => {
          try {
            await api(`/api/recipients/${b.dataset.deleteRecipient}`, { method: "DELETE" });
            loadRecipients();
            loadLists();
          } catch (err) {
            toast(`Fehler: ${err.message}`, "error");
          }
        })
      );
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  $("#btn-new-list").addEventListener("click", () => {
    $("#new-list-name").value = "";
    $("#list-modal").hidden = false;
    $("#new-list-name").focus();
  });
  $("#btn-list-cancel").addEventListener("click", () => ($("#list-modal").hidden = true));
  $("#btn-list-create").addEventListener("click", async () => {
    const name = $("#new-list-name").value.trim();
    if (!name) return toast("Bitte Name eingeben", "error");
    try {
      await api("/api/lists", { method: "POST", body: { name } });
      $("#list-modal").hidden = true;
      toast("Liste erstellt", "success");
      loadLists();
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  });

  $("#add-recipient-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.selectedListId) return;
    const form = e.target;
    try {
      await api("/api/recipients", {
        method: "POST",
        body: {
          email: form.email.value.trim(),
          name: form.name.value.trim(),
          list_id: state.selectedListId,
        },
      });
      form.reset();
      loadRecipients();
      loadLists();
    } catch (err) {
      toast(`Fehler: ${err.message}`, "error");
    }
  });

  $("#import-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.selectedListId) return;
    const form = e.target;
    const fd = new FormData();
    fd.append("list_id", String(state.selectedListId));
    fd.append("file", form.file.files[0]);
    try {
      const res = await api("/api/recipients/import", { method: "POST", body: fd });
      toast(`Import: ${res.added} hinzugefügt, ${res.skipped} übersprungen`, "success");
      form.reset();
      loadRecipients();
      loadLists();
    } catch (err) {
      toast(`Fehler: ${err.message}`, "error");
    }
  });

  // ---------- History ----------
  async function loadCampaigns() {
    try {
      const rows = await api("/api/campaigns");
      const tbody = $("#campaigns-table tbody");
      if (!rows.length) {
        tbody.innerHTML =
          '<tr><td colspan="8" class="muted" style="padding:20px;text-align:center;">Noch keine Kampagnen versendet.</td></tr>';
        return;
      }
      tbody.innerHTML = rows
        .map((c) => {
          const statusClass =
            c.status === "completed"
              ? "success"
              : c.status === "failed"
              ? "danger"
              : c.status === "partial"
              ? "warning"
              : "muted";
          return `
          <tr>
            <td>${escapeHtml(c.newsletter_name || `#${c.newsletter_id}`)}</td>
            <td>${escapeHtml(c.list_name || "Alle")}</td>
            <td><span class="badge ${statusClass}">${c.status}</span></td>
            <td>${c.success}</td>
            <td>${c.failed}</td>
            <td>${c.total}</td>
            <td>${formatDate(c.started_at)}</td>
            <td><button class="btn small" data-campaign="${c.id}">Details</button></td>
          </tr>`;
        })
        .join("");
      tbody.querySelectorAll("[data-campaign]").forEach((b) =>
        b.addEventListener("click", () => showCampaignDetails(b.dataset.campaign))
      );
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }
  $("#btn-refresh-history").addEventListener("click", loadCampaigns);

  async function showCampaignDetails(id) {
    try {
      const data = await api(`/api/campaigns/${id}`);
      const logs = (data.logs || [])
        .map((l) => `${l.status === "sent" ? "✓" : "✗"} ${l.email}${l.error ? " – " + l.error : ""}`)
        .join("\n");
      alert(
        `Kampagne #${data.id}\nStatus: ${data.status}\nErfolg: ${data.success} / Fehler: ${data.failed} / Gesamt: ${data.total}\n\n${logs || "(keine Einträge)"}`
      );
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }

  // ---------- Settings ----------
  async function loadSettings() {
    try {
      const s = await api("/api/settings");
      const form = $("#settings-form");
      Object.entries(s).forEach(([k, v]) => {
        if (form.elements[k]) form.elements[k].value = v ?? "";
      });
    } catch (e) {
      toast(`Fehler: ${e.message}`, "error");
    }
  }
  $("#settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const data = {
      smtp_host: form.smtp_host.value.trim(),
      smtp_port: Number(form.smtp_port.value),
      smtp_security: form.smtp_security.value,
      smtp_user: form.smtp_user.value.trim(),
      smtp_password: form.smtp_password.value || undefined,
      from_email: form.from_email.value.trim(),
      from_name: form.from_name.value.trim(),
    };
    try {
      await api("/api/settings", { method: "POST", body: data });
      $("#settings-status").textContent = "Gespeichert.";
      toast("Einstellungen gespeichert", "success");
      form.smtp_password.value = "";
      loadSettings();
    } catch (err) {
      toast(`Fehler: ${err.message}`, "error");
    }
  });

  // ---------- Helpers ----------
  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso + (iso.endsWith("Z") ? "" : "Z"));
    return d.toLocaleString("de-DE");
  }

  // ---------- Init ----------
  loadNewsletters();
})();
