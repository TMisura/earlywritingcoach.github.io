const GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8"];
const DESTINATIONS = {
  history: { title: "Today in History", klass: "btn-history", href: "history.html" },
  science: { title: "Strange Science", klass: "btn-science", href: "science.html" },
  letters: { title: "Letters to Family", klass: "btn-letters", href: "letters.html" },
  discoveries: { title: "Outrageous Discoveries", klass: "btn-discoveries", href: "discoveries.html" }
};

const Squad = {
  user: null,

  async api(path, options = {}) {
    const opts = { credentials: "include", headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options };
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.detail || res.statusText);
      err.status = res.status;
      err.data = data;
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

  header(active) {
    const el = document.getElementById("site-header");
    if (!el) return;
    const signed = this.user;
    el.innerHTML = `
      <a class="header-brand" href="index.html">
        <div class="header-mark">S</div>
        <div>
          <div class="brand-name">Summer</div>
          <div class="brand-sub">Writing Squad</div>
        </div>
      </a>
      <nav class="header-nav">
        <a href="history.html">History</a>
        <a href="science.html">Science</a>
        <a href="letters.html">Letters</a>
        <a href="discoveries.html">Discoveries</a>
        <a href="account.html">${signed ? "Account" : "Sign in"}</a>
        <a class="btn-gold" href="write.html">Start writing</a>
      </nav>`;
  },

  footer() {
    const el = document.getElementById("site-footer");
    if (!el) return;
    el.innerHTML = `<div>© 2026 Summer Writing Squad · Scores against K–8 ELA writing standards in all 50 states and DC</div><strong>Summer Writing Squad</strong>`;
  },

  params() {
    return new URLSearchParams(location.search);
  },

  saveDraft(draft) {
    sessionStorage.setItem("squad-draft", JSON.stringify(draft));
  },

  loadDraft() {
    try { return JSON.parse(sessionStorage.getItem("squad-draft") || "null"); }
    catch { return null; }
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  await Squad.refreshUser();
  Squad.header();
  Squad.footer();
  if (typeof window.onSquadReady === "function") window.onSquadReady();
});
