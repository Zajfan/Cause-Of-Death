import json
import os
from functools import lru_cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "cases.json"
PROGRESS_FILE = BASE_DIR / "progress.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("PORT", "8000"))


@lru_cache(maxsize=1)
def load_cases() -> list[dict]:
    raw = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    return raw["cases"] if isinstance(raw, dict) and "cases" in raw else raw


@lru_cache(maxsize=1)
def load_progress() -> dict:
    if not PROGRESS_FILE.exists():
        return {"notes": {}, "solved": []}
    raw = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {
        "notes": raw.get("notes", {}),
        "solved": raw.get("solved", []),
    }


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")
    load_progress.cache_clear()


def case_by_id(case_id: str) -> dict | None:
    return next((case for case in load_cases() if case["id"] == case_id), None)


def case_summary(case: dict) -> dict:
    progress = load_progress()
    solved = case["id"] in set(progress.get("solved", []))
    return {
        "id": case["id"],
        "title": case["title"],
        "status": case.get("status", "Open"),
        "victim": case.get("victim", {}),
        "location": case.get("location", ""),
        "solved": solved,
    }


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cause of Death</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f1116;
      --panel: #171b24;
      --panel-2: #1d2330;
      --line: #2a3142;
      --text: #e8ecf4;
      --muted: #9ca7bc;
      --accent: #86b7ff;
      --accent-2: #6ee7b7;
      --danger: #ff7a7a;
      --shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: radial-gradient(circle at top, #171c28 0%, var(--bg) 55%);
      color: var(--text);
      min-height: 100vh;
    }
    header {
      padding: 20px 22px 10px;
      border-bottom: 1px solid var(--line);
      background: rgba(12, 14, 19, 0.55);
      backdrop-filter: blur(8px);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1 { margin: 0; font-size: 28px; letter-spacing: 0.02em; }
    .sub { color: var(--muted); margin-top: 6px; }
    .status { margin-top: 10px; color: var(--accent); font-size: 14px; }
    main {
      display: grid;
      grid-template-columns: 290px minmax(0, 1fr) 350px;
      gap: 14px;
      padding: 14px;
      align-items: start;
    }
    .panel {
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)), var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .panel h2 {
      margin: 0;
      padding: 14px 16px;
      font-size: 15px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #cdd7f7;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }
    .panel .content { padding: 14px; }
    .list { display: grid; gap: 8px; }
    .case-item, .suspect-item, .evidence-item {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel-2);
      padding: 10px 12px;
      cursor: pointer;
      transition: 0.15s ease;
    }
    .case-item:hover, .suspect-item:hover, .evidence-item:hover { transform: translateY(-1px); border-color: #40609f; }
    .case-item.active, .suspect-item.active, .evidence-item.active { border-color: var(--accent); box-shadow: inset 0 0 0 1px rgba(134,183,255,0.2); }
    .case-title { font-weight: 700; }
    .case-meta, .small { color: var(--muted); font-size: 13px; margin-top: 4px; }
    .badge { display: inline-block; margin-top: 6px; padding: 2px 8px; border-radius: 999px; font-size: 12px; background: rgba(110,231,183,0.12); color: var(--accent-2); }
    .badge.open { background: rgba(134,183,255,0.12); color: var(--accent); }
    .badge.solved { background: rgba(110,231,183,0.14); color: var(--accent-2); }
    .section { margin-top: 14px; }
    .section:first-child { margin-top: 0; }
    .section-title { color: #cdd7f7; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }
    .card {
      border: 1px solid var(--line);
      background: var(--panel-2);
      border-radius: 14px;
      padding: 12px;
    }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .kv { color: var(--muted); font-size: 13px; }
    .kv strong { color: var(--text); display: block; font-size: 14px; margin-top: 2px; }
    .textblock { white-space: pre-wrap; line-height: 1.55; color: #eef2fb; }
    textarea, select, input[type="text"] {
      width: 100%;
      border: 1px solid var(--line);
      background: #131824;
      color: var(--text);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
      outline: none;
    }
    textarea { min-height: 170px; resize: vertical; }
    .btnrow { display: flex; gap: 8px; flex-wrap: wrap; }
    button {
      border: 1px solid var(--line);
      background: #20263a;
      color: var(--text);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
      cursor: pointer;
    }
    button.primary { background: linear-gradient(180deg, #3b5ea8, #2d4e93); border-color: #4c70bf; }
    button:hover { filter: brightness(1.06); }
    .muted { color: var(--muted); }
    .message { margin-top: 12px; padding: 12px; border-radius: 12px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }
    .message.good { border-color: rgba(110,231,183,0.35); color: #b7f5d3; }
    .message.bad { border-color: rgba(255,122,122,0.35); color: #ffb2b2; }
    @media (max-width: 1180px) { main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>Cause of Death</h1>
    <div class="sub">A Python-powered crime-solving prototype — case list, evidence viewer, suspect panel, notes area, accusation screen.</div>
    <div class="status" id="status">Loading cases…</div>
  </header>

  <main>
    <section class="panel">
      <h2>Case List</h2>
      <div class="content">
        <div class="list" id="caseList"></div>
      </div>
    </section>

    <section class="panel">
      <h2>Investigation Desk</h2>
      <div class="content">
        <div class="section">
          <div class="section-title">Case File</div>
          <div class="card" id="caseFile">Select a case.</div>
        </div>

        <div class="section grid-2">
          <div>
            <div class="section-title">Evidence Viewer</div>
            <div class="list" id="evidenceList"></div>
          </div>
          <div>
            <div class="section-title">Evidence Details</div>
            <div class="card textblock" id="evidenceDetails">Pick a clue.</div>
          </div>
        </div>

        <div class="section">
          <div class="section-title">Notes Area</div>
          <textarea id="notes" placeholder="Write down contradictions, timelines, and theories."></textarea>
          <div class="btnrow" style="margin-top:10px;">
            <button class="primary" id="saveNotes">Save Notes</button>
            <button id="clearNotes">Clear Notes</button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>Suspects & Accusation</h2>
      <div class="content">
        <div class="section">
          <div class="section-title">Suspect Panel</div>
          <div class="list" id="suspectList"></div>
          <div class="card textblock section" id="suspectDetails">Choose a suspect.</div>
        </div>

        <div class="section">
          <div class="section-title">Accusation Screen</div>
          <div class="card">
            <div class="small">Suspect</div>
            <select id="accSuspect"></select>
            <div class="small" style="margin-top:10px;">Method</div>
            <select id="accMethod"></select>
            <div class="small" style="margin-top:10px;">Motive</div>
            <select id="accMotive"></select>
            <div class="small" style="margin-top:10px;">Key evidence</div>
            <select id="accEvidence"></select>
            <div class="btnrow" style="margin-top:12px;">
              <button class="primary" id="submitAccusation">Submit Accusation</button>
              <button id="resetTheory">Reset Theory</button>
            </div>
            <div class="message" id="accMessage">Choose your final theory and submit it here.</div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <script>
    const state = {
      cases: [],
      currentCase: null,
      currentEvidence: null,
      currentSuspect: null,
    };

    const el = (id) => document.getElementById(id);
    const caseList = el('caseList');
    const caseFile = el('caseFile');
    const evidenceList = el('evidenceList');
    const evidenceDetails = el('evidenceDetails');
    const suspectList = el('suspectList');
    const suspectDetails = el('suspectDetails');
    const notes = el('notes');
    const status = el('status');
    const accSuspect = el('accSuspect');
    const accMethod = el('accMethod');
    const accMotive = el('accMotive');
    const accEvidence = el('accEvidence');
    const accMessage = el('accMessage');

    let notesTimer = null;

    function setStatus(text) { status.textContent = text; }

    function escapeHtml(s) {
      return String(s)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function option(label, value) {
      return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
    }

    function renderCaseList() {
      caseList.innerHTML = state.cases.map(c => {
        const active = state.currentCase && state.currentCase.id === c.id ? 'active' : '';
        const badge = c.solved ? '<span class="badge solved">Solved</span>' : '<span class="badge open">Open</span>';
        return `
          <div class="case-item ${active}" data-id="${escapeHtml(c.id)}">
            <div class="case-title">${escapeHtml(c.title)}</div>
            <div class="case-meta">${escapeHtml(c.victim.name)} — ${escapeHtml(c.location)}</div>
            ${badge}
          </div>
        `;
      }).join('');
      caseList.querySelectorAll('.case-item').forEach(node => {
        node.addEventListener('click', () => loadCase(node.dataset.id));
      });
    }

    function renderCaseFile(c) {
      caseFile.innerHTML = `
        <div class="grid-2">
          <div class="kv">Case<strong>${escapeHtml(c.title)}</strong></div>
          <div class="kv">Status<strong>${escapeHtml(c.status || 'Open')}</strong></div>
          <div class="kv">Victim<strong>${escapeHtml(c.victim.name)} — ${escapeHtml(c.victim.occupation)}</strong></div>
          <div class="kv">Location<strong>${escapeHtml(c.location)}</strong></div>
        </div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Brief</div>
          <div class="textblock">${escapeHtml(c.brief)}</div>
        </div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Scene</div>
          <div class="textblock">${escapeHtml(c.scene)}</div>
        </div>
      `;
    }

    function renderEvidence(c) {
      evidenceList.innerHTML = c.evidence.map((e, idx) => {
        const active = state.currentEvidence && state.currentEvidence.id === e.id ? 'active' : (!state.currentEvidence && idx === 0 ? 'active' : '');
        return `
          <div class="evidence-item ${active}" data-id="${escapeHtml(e.id)}">
            <div class="case-title">${escapeHtml(e.title)}</div>
            <div class="case-meta">${escapeHtml(e.type)} — ${escapeHtml(e.media_hint || 'no media file')}</div>
          </div>
        `;
      }).join('');
      evidenceList.querySelectorAll('.evidence-item').forEach(node => {
        node.addEventListener('click', () => selectEvidence(node.dataset.id));
      });
      if (!state.currentEvidence && c.evidence.length) selectEvidence(c.evidence[0].id, true);
    }

    function renderEvidenceDetails(e) {
      evidenceDetails.innerHTML = `
        <div class="kv">Title<strong>${escapeHtml(e.title)}</strong></div>
        <div class="grid-2" style="margin-top:10px;">
          <div class="kv">Type<strong>${escapeHtml(e.type)}</strong></div>
          <div class="kv">Media<strong>${escapeHtml(e.media_hint || 'N/A')}</strong></div>
        </div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Summary</div>
          <div class="textblock">${escapeHtml(e.summary)}</div>
        </div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Details</div>
          <div class="textblock">${escapeHtml(e.details)}</div>
        </div>
      `;
    }

    function renderSuspects(c) {
      suspectList.innerHTML = c.suspects.map((s, idx) => {
        const active = state.currentSuspect && state.currentSuspect.name === s.name ? 'active' : (!state.currentSuspect && idx === 0 ? 'active' : '');
        return `
          <div class="suspect-item ${active}" data-name="${escapeHtml(s.name)}">
            <div class="case-title">${escapeHtml(s.name)}</div>
            <div class="case-meta">${escapeHtml(s.role)}</div>
          </div>
        `;
      }).join('');
      suspectList.querySelectorAll('.suspect-item').forEach(node => {
        node.addEventListener('click', () => selectSuspect(node.dataset.name, true));
      });
      if (!state.currentSuspect && c.suspects.length) selectSuspect(c.suspects[0].name, true);
    }

    function renderSuspectDetails(s) {
      suspectDetails.innerHTML = `
        <div class="kv">Name<strong>${escapeHtml(s.name)}</strong></div>
        <div class="kv" style="margin-top:10px;">Role<strong>${escapeHtml(s.role)}</strong></div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Profile</div>
          <div class="textblock">${escapeHtml(s.profile)}</div>
        </div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Relationship</div>
          <div class="textblock">${escapeHtml(s.relationship)}</div>
        </div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Alibi</div>
          <div class="textblock">${escapeHtml(s.alibi)}</div>
        </div>
        <div class="section">
          <div class="section-title" style="margin:12px 0 6px;">Motive</div>
          <div class="textblock">${escapeHtml(s.motive)}</div>
        </div>
      `;
    }

    function populateAccusation(c) {
      accSuspect.innerHTML = [option('Select suspect', '')].concat(c.suspects.map(s => option(s.name, s.name))).join('');
      const methods = [...new Set(c.methods || [])];
      const motives = [...new Set(c.motives || [])];
      accMethod.innerHTML = [option('Select method', '')].concat(methods.map(m => option(m, m))).join('');
      accMotive.innerHTML = [option('Select motive', '')].concat(motives.map(m => option(m, m))).join('');
      accEvidence.innerHTML = [option('Select evidence', '')].concat(c.evidence.map(e => option(`${e.id.toUpperCase()} — ${e.title}`, e.id))).join('');
      resetTheory(false);
    }

    function resetTheory(showMessage = true) {
      accSuspect.value = '';
      accMethod.value = '';
      accMotive.value = '';
      accEvidence.value = '';
      if (showMessage) accMessage.className = 'message';
      if (showMessage) accMessage.textContent = 'Choose your final theory and submit it here.';
    }

    function updateNotesFromState(c) {
      notes.value = c.notes || '';
    }

    async function saveNotes() {
      if (!state.currentCase) return;
      const body = { notes: notes.value };
      await fetch(`/api/cases/${encodeURIComponent(state.currentCase.id)}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(body),
      });
      setStatus(`Saved notes for ${state.currentCase.title}.`);
    }

    async function selectEvidence(id, silent = false) {
      if (!state.currentCase) return;
      state.currentEvidence = state.currentCase.evidence.find(e => e.id === id) || state.currentCase.evidence[0];
      renderEvidence(state.currentCase);
      renderEvidenceDetails(state.currentEvidence);
      if (!silent) setStatus(`Viewing evidence: ${state.currentEvidence.title}`);
    }

    async function selectSuspect(name, silent = false) {
      if (!state.currentCase) return;
      state.currentSuspect = state.currentCase.suspects.find(s => s.name === name) || state.currentCase.suspects[0];
      renderSuspects(state.currentCase);
      renderSuspectDetails(state.currentSuspect);
      if (!silent) setStatus(`Viewing suspect: ${state.currentSuspect.name}`);
    }

    async function loadCase(id) {
      const resp = await fetch(`/api/cases/${encodeURIComponent(id)}`, { headers: { 'Accept': 'application/json' } });
      const c = await resp.json();
      state.currentCase = c;
      state.currentEvidence = c.evidence[0] || null;
      state.currentSuspect = c.suspects[0] || null;
      renderCaseList();
      renderCaseFile(c);
      renderEvidence(c);
      renderSuspects(c);
      populateAccusation(c);
      updateNotesFromState(c);
      if (c.evidence[0]) renderEvidenceDetails(c.evidence[0]);
      if (c.suspects[0]) renderSuspectDetails(c.suspects[0]);
      setStatus(`Case loaded: ${c.title} | Victim: ${c.victim.name} | Status: ${c.solved ? 'Solved' : 'Open'}`);
    }

    async function submitAccusation() {
      if (!state.currentCase) return;
      const payload = {
        suspect: accSuspect.value,
        method: accMethod.value,
        motive: accMotive.value,
        evidence: accEvidence.value,
      };
      const resp = await fetch(`/api/cases/${encodeURIComponent(state.currentCase.id)}/accusation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await resp.json();
      accMessage.className = `message ${result.solved ? 'good' : 'bad'}`;
      accMessage.textContent = result.message;
      if (result.solved) {
        setStatus(`Case solved: ${state.currentCase.title}`);
        await boot();
      }
    }

    async function boot() {
      const resp = await fetch('/api/cases', { headers: { 'Accept': 'application/json' } });
      state.cases = await resp.json();
      renderCaseList();
      if (!state.currentCase && state.cases.length) {
        await loadCase(state.cases[0].id);
      } else if (state.currentCase) {
        await loadCase(state.currentCase.id);
      }
    }

    el('saveNotes').addEventListener('click', saveNotes);
    el('clearNotes').addEventListener('click', async () => {
      notes.value = '';
      await saveNotes();
    });
    el('resetTheory').addEventListener('click', () => resetTheory(true));
    el('submitAccusation').addEventListener('click', submitAccusation);
    notes.addEventListener('input', () => {
      clearTimeout(notesTimer);
      notesTimer = setTimeout(saveNotes, 350);
    });

    boot().catch(err => {
      setStatus(`Failed to load cases: ${err}`);
      console.error(err);
    });
  </script>
</body>
</html>"""


class CauseOfDeathHandler(BaseHTTPRequestHandler):
    server_version = "CauseOfDeath/0.2"

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send_html(HTML_PAGE)
            return
        if path == "/api/cases":
            json_response(self, [case_summary(case) for case in load_cases()])
            return
        if path.startswith("/api/cases/"):
            parts = path.split("/")
            if len(parts) >= 4:
                case_id = parts[3]
                case = case_by_id(case_id)
                if not case:
                    json_response(self, {"error": "Case not found"}, HTTPStatus.NOT_FOUND)
                    return
                if len(parts) == 4:
                    self._send_case(case)
                    return
                if len(parts) == 5 and parts[4] == "notes":
                    progress = load_progress()
                    notes = progress.get("notes", {}).get(case_id, "")
                    json_response(self, {"case_id": case_id, "notes": notes})
                    return
        json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/cases/"):
            json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        parts = path.split("/")
        if len(parts) < 5:
            json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        case_id = parts[3]
        action = parts[4]
        case = case_by_id(case_id)
        if not case:
            json_response(self, {"error": "Case not found"}, HTTPStatus.NOT_FOUND)
            return
        body = self._read_json_body()
        progress = load_progress()
        if action == "notes":
            progress.setdefault("notes", {})[case_id] = body.get("notes", "")
            save_progress(progress)
            json_response(self, {"ok": True, "case_id": case_id, "notes": progress["notes"][case_id]})
            return
        if action == "accusation":
            result = self._grade_accusation(case, body, progress)
            save_progress(progress)
            json_response(self, result)
            return
        json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def _send_html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_case(self, case: dict) -> None:
        progress = load_progress()
        notes = progress.get("notes", {}).get(case["id"], "")
        solved = case["id"] in set(progress.get("solved", []))
        payload = dict(case)
        payload["notes"] = notes
        payload["solved"] = solved
        json_response(self, payload)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _grade_accusation(self, case: dict, body: dict, progress: dict) -> dict:
        solution = case["solution"]
        correct_evidence = next(
            (f"{item['id'].upper()} — {item['title']}" for item in case["evidence"] if item["id"] == solution["key_evidence"]),
            "",
        )
        guess = {
            "suspect": body.get("suspect", ""),
            "method": body.get("method", ""),
            "motive": body.get("motive", ""),
            "evidence": body.get("evidence", ""),
        }
        matches = {
            "suspect": guess["suspect"] == solution["killer"],
            "method": guess["method"] == solution["method"],
            "motive": guess["motive"] == solution["motive"],
            "evidence": guess["evidence"] == correct_evidence,
        }
        score = sum(matches.values())
        if score == 4:
            solved = set(progress.get("solved", []))
            solved.add(case["id"])
            progress["solved"] = sorted(solved)
            return {
                "ok": True,
                "solved": True,
                "score": 4,
                "message": f"Case solved. You correctly identified {solution['killer']}, the {solution['method']} method, the {solution['motive']} motive, and the key evidence.",
            }
        failed = ", ".join(name for name, ok in matches.items() if not ok)
        return {
            "ok": False,
            "solved": False,
            "score": score,
            "message": f"Accusation rejected. You matched {score}/4 parts. Review: {failed}.",
        }


def main() -> None:
    server = ThreadingHTTPServer((DEFAULT_HOST, DEFAULT_PORT), CauseOfDeathHandler)
    print(f"Cause of Death running at http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
