const GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8"];

const Coach = {
  user: null,

  async api(path, options = {}) {
    const opts = {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    };
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.detail || res.statusText);
      err.status = res.status;
      throw err;
    }
    return data;
  },

  async refreshUser() {
    try {
      const data = await this.api("/api/me");
      this.user = data.user;
    } catch {
      this.user = null;
    }
    return this.user;
  },

  fillStates(select, selected) {
    return this.api("/api/states").then((data) => {
      select.innerHTML = data.jurisdictions.map((s) =>
        `<option value="${s.abbr}" ${s.abbr === selected ? "selected" : ""}>${s.name}</option>`
      ).join("");
    });
  },

  fillGrades(select, selected) {
    select.innerHTML = GRADES.map((g) =>
      `<option value="${g}" ${String(selected) === g ? "selected" : ""}>Grade ${g}</option>`
    ).join("");
  },

  header() {
    const el = document.getElementById("site-header");
    if (!el) return;
    const signed = this.user;
    el.innerHTML = `
      <a class="header-brand" href="index.html">
        <div class="header-mark">EWC</div>
        <div>
          <div class="brand-name">Early Writing Coach</div>
          <div class="brand-sub">earlywritingcoach.ai</div>
        </div>
      </a>
      <nav class="header-nav">
        <a href="booklets.html">Printable booklets</a>
        <a href="account.html">${signed ? "Saved notes" : "Sign in"}</a>
        <a class="btn-main" href="write.html">Submit writing</a>
      </nav>`;
  },

  footer() {
    const el = document.getElementById("site-footer");
    if (!el) return;
    el.innerHTML = `<div>Early Writing Coach · earlywritingcoach.ai · earlywritingcoach.com · Writing samples are not stored.</div><strong>Save coaching notes on your computer.</strong>`;
  },

  params() {
    return new URLSearchParams(location.search);
  },

  downloadNote(result) {
    const focuses = (result.focuses || []).map((f) => `
      <h2>${escapeHtml(f.title)}</h2>
      <p>${escapeHtml(f.noticed)}</p>
      <h3>Practice at home</h3>
      <ol>${(f.home_practice || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ol>
      <h3>What to tell the teacher</h3>
      <p>${escapeHtml(f.teacher_share)}</p>
      ${(f.standards || []).map((s) => `<p><strong>${escapeHtml(s.code)}</strong> — ${escapeHtml(s.text)}</p>`).join("")}
    `).join("<hr>");
    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${escapeHtml(result.save_filename || "coaching-note")}</title>
      <style>body{font-family:Georgia,serif;max-width:720px;margin:2rem auto;line-height:1.45;color:#1C1917} h1{font-size:28px} .warn{background:#F4E3C7;padding:12px;border-radius:8px}</style></head>
      <body>
        <p class="warn"><strong>Save this file on your computer.</strong> Early Writing Coach does not keep the child’s writing. This note only names the skills you are reinforcing.</p>
        <h1>Early Writing Coach note</h1>
        <p>${escapeHtml(result.state_name)}, grade ${escapeHtml(result.grade)} · ${escapeHtml(result.assignment_label || "")}</p>
        <p>${escapeHtml(result.framework)}</p>
        ${focuses}
      </body></html>`;
    const blob = new Blob([html], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = result.save_filename || "early-writing-coach-note.html";
    a.click();
    URL.revokeObjectURL(a.href);
  }
};

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

document.addEventListener("DOMContentLoaded", async () => {
  await Coach.refreshUser();
  Coach.header();
  Coach.footer();
  if (typeof window.onCoachReady === "function") window.onCoachReady();
});
