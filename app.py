import json
import os
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import tkinter as tk
from tkinter import ttk

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "cases.json"
PROGRESS_FILE = BASE_DIR / "progress.json"
IMAGE_EXTENSIONS = {".png", ".gif", ".ppm", ".pgm"}


@dataclass
class EvidenceItem:
    id: str
    type: str
    title: str
    summary: str
    details: str
    media_hint: str = ""


@dataclass
class SuspectItem:
    name: str
    role: str
    profile: str
    alibi: str
    motive: str
    relationship: str


@dataclass
class CaseItem:
    id: str
    title: str
    status: str
    victim: dict
    location: str
    brief: str
    scene: str
    methods: list[str]
    motives: list[str]
    suspects: list[SuspectItem]
    evidence: list[EvidenceItem]
    solution: dict


@lru_cache(maxsize=1)
def load_cases() -> list[CaseItem]:
    raw = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    records = raw["cases"] if isinstance(raw, dict) and "cases" in raw else raw
    parsed: list[CaseItem] = []
    for item in records:
        parsed.append(
            CaseItem(
                id=item["id"],
                title=item["title"],
                status=item.get("status", "Open"),
                victim=item["victim"],
                location=item["location"],
                brief=item["brief"],
                scene=item["scene"],
                methods=list(item.get("methods", [])),
                motives=list(item.get("motives", [])),
                suspects=[SuspectItem(**suspect) for suspect in item.get("suspects", [])],
                evidence=[EvidenceItem(**evidence) for evidence in item.get("evidence", [])],
                solution=item["solution"],
            )
        )
    return parsed


def default_progress() -> dict:
    return {
        "selected_case_id": "",
        "open_case_id": "",
        "solved": [],
        "notes": {},
    }


def normalize_progress(raw: dict) -> dict:
    progress = default_progress()
    progress["selected_case_id"] = raw.get("selected_case_id", "") or ""
    progress["open_case_id"] = raw.get("open_case_id", "") or ""
    progress["solved"] = list(raw.get("solved", []))

    notes: dict[str, list[str]] = {}
    for case_id, value in raw.get("notes", {}).items():
        if isinstance(value, list):
            notes[case_id] = [str(note) for note in value if str(note).strip()]
        elif isinstance(value, str) and value.strip():
            notes[case_id] = [value.strip()]
        else:
            notes[case_id] = []
    progress["notes"] = notes
    return progress


def load_progress() -> dict:
    if not PROGRESS_FILE.exists():
        return default_progress()
    try:
        raw = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_progress()
    if not isinstance(raw, dict):
        return default_progress()
    return normalize_progress(raw)


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")


def evidence_label(evidence: EvidenceItem) -> str:
    return f"{evidence.id.upper()} — {evidence.title}"


def resolve_media_path(media_hint: str) -> Path | None:
    if not media_hint:
        return None
    candidates = [
        BASE_DIR / media_hint,
        BASE_DIR / "assets" / media_hint,
        BASE_DIR / "media" / media_hint,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def open_external_file(path: Path) -> bool:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


class CauseOfDeathApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cause of Death")
        self.geometry("1560x960")
        self.minsize(1320, 840)
        self.configure(bg="#10131a")

        self.cases = load_cases()
        self.case_by_id = {case.id: case for case in self.cases}
        self.progress = load_progress()
        self.solved_case_ids = set(self.progress.get("solved", []))
        self.selected_case_id = self._choose_case_id(self.progress.get("selected_case_id", ""))
        self.open_case_id = self._choose_case_id(self.progress.get("open_case_id", ""))
        self.current_case = self.case_by_id.get(self.open_case_id)
        if self.current_case is None:
            self.open_case_id = ""

        self.current_evidence_id = ""
        self.current_suspect_name = ""
        self.preview_image: tk.PhotoImage | None = None

        self.status_var = tk.StringVar(value="Select a case, then open it to begin the investigation.")
        self.preview_title_var = tk.StringVar(value="No case selected")
        self.preview_victim_var = tk.StringVar(value="Victim: —")
        self.preview_location_var = tk.StringVar(value="Location: —")
        self.preview_status_var = tk.StringVar(value="Status: —")
        self.case_title_var = tk.StringVar(value="Case file locked")
        self.case_victim_var = tk.StringVar(value="Victim: —")
        self.case_location_var = tk.StringVar(value="Location: —")
        self.case_brief_var = tk.StringVar(value="Open a case to inspect its brief.")
        self.case_scene_var = tk.StringVar(value="")
        self.evidence_kind_var = tk.StringVar(value="No evidence selected")
        self.evidence_title_var = tk.StringVar(value="—")
        self.evidence_media_var = tk.StringVar(value="Media: —")
        self.evidence_summary_var = tk.StringVar(value="Pick a clue from the evidence list.")
        self.evidence_details_var = tk.StringVar(value="")
        self.evidence_preview_var = tk.StringVar(value="Evidence preview will appear here.")
        self.suspect_name_var = tk.StringVar(value="—")
        self.suspect_role_var = tk.StringVar(value="Role: —")
        self.suspect_profile_var = tk.StringVar(value="Select a suspect to review their profile.")
        self.suspect_relationship_var = tk.StringVar(value="Relationship: —")
        self.suspect_alibi_var = tk.StringVar(value="Alibi: —")
        self.suspect_motive_var = tk.StringVar(value="Motive: —")
        self.accusation_result_var = tk.StringVar(value="Choose your final theory and submit it here.")
        self.new_note_var = tk.StringVar(value="")
        self.open_button_var = tk.StringVar(value="Open Case")

        self._setup_style()
        self._build_ui()
        self._refresh_case_list()
        self._sync_selection()
        self._sync_open_case_state()

    def _choose_case_id(self, case_id: str) -> str:
        if case_id and case_id in self.case_by_id:
            return case_id
        return self.cases[0].id if self.cases else ""

    def _setup_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background="#10131a", foreground="#e9edf7")
        style.configure("TFrame", background="#10131a")
        style.configure("TLabel", background="#10131a", foreground="#e9edf7")
        style.configure("TButton", padding=(10, 6), background="#283142", foreground="#ffffff")
        style.map("TButton", background=[("active", "#3a4660")])
        style.configure("TLabelframe", background="#10131a", foreground="#cfd8ff")
        style.configure("TLabelframe.Label", background="#10131a", foreground="#9fb6ff", font=("Segoe UI", 10, "bold"))
        style.configure("TCombobox", fieldbackground="#171d29", background="#171d29", foreground="#e9edf7")

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(18, 16, 18, 12))
        header.grid(row=0, column=0, columnspan=3, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Cause of Death", font=("Segoe UI", 24, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="A Python desktop crime-solving game — select a case, open it, inspect evidence, study suspects, take notes, and accuse.",
            foreground="#a7b2c9",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(header, textvariable=self.status_var, foreground="#86b7ff").grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=1)

        self.left_frame = ttk.Frame(self, padding=(16, 0, 8, 16))
        self.center_frame = ttk.Frame(self, padding=(8, 0, 8, 16))
        self.right_frame = ttk.Frame(self, padding=(8, 0, 16, 16))
        self.left_frame.grid(row=1, column=0, sticky="nsew")
        self.center_frame.grid(row=1, column=1, sticky="nsew")
        self.right_frame.grid(row=1, column=2, sticky="nsew")
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self._build_left_panel()
        self._build_center_panel()
        self._build_right_panel()

    def _build_left_panel(self) -> None:
        case_box = ttk.LabelFrame(self.left_frame, text="Case List", padding=10)
        case_box.pack(fill=tk.BOTH, expand=True)

        list_row = ttk.Frame(case_box)
        list_row.pack(fill=tk.BOTH, expand=False)
        self.case_listbox = tk.Listbox(
            list_row,
            height=13,
            bg="#151b26",
            fg="#e9edf7",
            selectbackground="#4360b3",
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            activestyle="dotbox",
            exportselection=False,
        )
        case_scroll = ttk.Scrollbar(list_row, orient=tk.VERTICAL, command=self.case_listbox.yview)
        self.case_listbox.configure(yscrollcommand=case_scroll.set)
        self.case_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        case_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.case_listbox.bind("<<ListboxSelect>>", self._on_case_selected)

        self.case_preview_box = ttk.LabelFrame(case_box, text="Case Opening", padding=10)
        self.case_preview_box.pack(fill=tk.BOTH, expand=False, pady=(12, 0))

        ttk.Label(self.case_preview_box, textvariable=self.preview_title_var, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(self.case_preview_box, textvariable=self.preview_victim_var, foreground="#a7b2c9", wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(4, 0))
        ttk.Label(self.case_preview_box, textvariable=self.preview_location_var, foreground="#a7b2c9", wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))
        ttk.Label(self.case_preview_box, textvariable=self.preview_status_var, foreground="#8bc4ff", wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))

        button_row = ttk.Frame(self.case_preview_box)
        button_row.pack(fill=tk.X, pady=(10, 0))
        self.open_button = ttk.Button(button_row, textvariable=self.open_button_var, command=self._open_selected_case)
        self.open_button.pack(side=tk.LEFT)
        self.close_button = ttk.Button(button_row, text="Close Case", command=self._close_case)
        self.close_button.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(
            self.case_preview_box,
            text="Select a case, then open it to start the investigation desk.",
            foreground="#a7b2c9",
            wraplength=360,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(10, 0))

    def _build_center_panel(self) -> None:
        self.center_locked = ttk.LabelFrame(self.center_frame, text="Investigation Desk", padding=14)
        self.center_locked.pack(fill=tk.BOTH, expand=True)
        self.center_locked_message = ttk.Label(
            self.center_locked,
            text="No case is open yet. Choose one from the case list and click Open Case.",
            foreground="#a7b2c9",
            wraplength=580,
            justify=tk.LEFT,
        )
        self.center_locked_message.pack(anchor="w")

        self.center_content = ttk.Frame(self.center_frame)
        self.center_content.pack(fill=tk.BOTH, expand=True)

        file_box = ttk.LabelFrame(self.center_content, text="Case File", padding=12)
        file_box.pack(fill=tk.X, expand=False)
        ttk.Label(file_box, textvariable=self.case_title_var, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(file_box, textvariable=self.case_victim_var, foreground="#a7b2c9", wraplength=700, justify=tk.LEFT).pack(anchor="w", pady=(4, 0))
        ttk.Label(file_box, textvariable=self.case_location_var, foreground="#a7b2c9", wraplength=700, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))
        ttk.Label(file_box, text="Brief", foreground="#9fb6ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        ttk.Label(file_box, textvariable=self.case_brief_var, wraplength=700, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))
        ttk.Label(file_box, text="Scene", foreground="#9fb6ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        ttk.Label(file_box, textvariable=self.case_scene_var, wraplength=700, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))

        evidence_row = ttk.Frame(self.center_content)
        evidence_row.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        evidence_list_box = ttk.LabelFrame(evidence_row, text="Evidence Viewer", padding=10)
        evidence_list_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.evidence_listbox = tk.Listbox(
            evidence_list_box,
            height=10,
            bg="#151b26",
            fg="#e9edf7",
            selectbackground="#4360b3",
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            activestyle="dotbox",
            exportselection=False,
        )
        evidence_scroll = ttk.Scrollbar(evidence_list_box, orient=tk.VERTICAL, command=self.evidence_listbox.yview)
        self.evidence_listbox.configure(yscrollcommand=evidence_scroll.set)
        self.evidence_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        evidence_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.evidence_listbox.bind("<<ListboxSelect>>", self._on_evidence_selected)

        evidence_detail_box = ttk.LabelFrame(evidence_row, text="Evidence Details", padding=10)
        evidence_detail_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        ttk.Label(evidence_detail_box, textvariable=self.evidence_kind_var, foreground="#8bc4ff", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(evidence_detail_box, textvariable=self.evidence_title_var, font=("Segoe UI", 12, "bold"), wraplength=480, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))
        ttk.Label(evidence_detail_box, textvariable=self.evidence_media_var, foreground="#a7b2c9", wraplength=480, justify=tk.LEFT).pack(anchor="w", pady=(4, 0))

        self.evidence_preview_label = ttk.Label(
            evidence_detail_box,
            textvariable=self.evidence_preview_var,
            justify=tk.CENTER,
            anchor="center",
            background="#0e1219",
            foreground="#a7b2c9",
            relief=tk.SOLID,
            borderwidth=1,
            padding=12,
            wraplength=460,
        )
        self.evidence_preview_label.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        ttk.Label(evidence_detail_box, text="Summary", foreground="#9fb6ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        ttk.Label(evidence_detail_box, textvariable=self.evidence_summary_var, wraplength=480, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))
        ttk.Label(evidence_detail_box, text="Details", foreground="#9fb6ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        ttk.Label(evidence_detail_box, textvariable=self.evidence_details_var, wraplength=480, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))

        media_buttons = ttk.Frame(evidence_detail_box)
        media_buttons.pack(fill=tk.X, pady=(10, 0))
        self.open_media_button = ttk.Button(media_buttons, text="Open Media", command=self._open_current_media)
        self.open_media_button.pack(side=tk.LEFT)

        notes_box = ttk.LabelFrame(self.center_content, text="Notes Area", padding=10)
        notes_box.pack(fill=tk.BOTH, expand=False, pady=(12, 0))
        notes_row = ttk.Frame(notes_box)
        notes_row.pack(fill=tk.X)
        ttk.Entry(notes_row, textvariable=self.new_note_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(notes_row, text="Add Note", command=self._add_note).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(notes_row, text="Delete Selected", command=self._delete_selected_note).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(notes_row, text="Clear Notes", command=self._clear_notes).pack(side=tk.LEFT, padx=(8, 0))

        notes_list_row = ttk.Frame(notes_box)
        notes_list_row.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.notes_listbox = tk.Listbox(
            notes_list_row,
            height=7,
            bg="#151b26",
            fg="#e9edf7",
            selectbackground="#4360b3",
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            activestyle="dotbox",
            exportselection=False,
        )
        notes_scroll = ttk.Scrollbar(notes_list_row, orient=tk.VERTICAL, command=self.notes_listbox.yview)
        self.notes_listbox.configure(yscrollcommand=notes_scroll.set)
        self.notes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notes_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.notes_count_var = tk.StringVar(value="0 notes")
        ttk.Label(notes_box, textvariable=self.notes_count_var, foreground="#a7b2c9").pack(anchor="e", pady=(8, 0))

    def _build_right_panel(self) -> None:
        self.right_locked = ttk.LabelFrame(self.right_frame, text="Suspects & Accusation", padding=14)
        self.right_locked.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            self.right_locked,
            text="Open a case to reveal the suspect panel and accusation screen.",
            foreground="#a7b2c9",
            wraplength=350,
            justify=tk.LEFT,
        ).pack(anchor="w")

        self.right_content = ttk.Frame(self.right_frame)
        self.right_content.pack(fill=tk.BOTH, expand=True)

        suspect_box = ttk.LabelFrame(self.right_content, text="Suspect Panel", padding=10)
        suspect_box.pack(fill=tk.BOTH, expand=True)
        self.suspect_listbox = tk.Listbox(
            suspect_box,
            height=10,
            bg="#151b26",
            fg="#e9edf7",
            selectbackground="#4360b3",
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            activestyle="dotbox",
            exportselection=False,
        )
        suspect_scroll = ttk.Scrollbar(suspect_box, orient=tk.VERTICAL, command=self.suspect_listbox.yview)
        self.suspect_listbox.configure(yscrollcommand=suspect_scroll.set)
        self.suspect_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        suspect_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.suspect_listbox.bind("<<ListboxSelect>>", self._on_suspect_selected)

        suspect_detail_box = ttk.LabelFrame(suspect_box, text="Suspect Details", padding=10)
        suspect_detail_box.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        ttk.Label(suspect_detail_box, textvariable=self.suspect_name_var, font=("Segoe UI", 12, "bold"), wraplength=360, justify=tk.LEFT).pack(anchor="w")
        ttk.Label(suspect_detail_box, textvariable=self.suspect_role_var, foreground="#a7b2c9").pack(anchor="w", pady=(2, 0))
        ttk.Label(suspect_detail_box, text="Profile", foreground="#9fb6ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        ttk.Label(suspect_detail_box, textvariable=self.suspect_profile_var, wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(2, 0))
        ttk.Label(suspect_detail_box, textvariable=self.suspect_relationship_var, wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(10, 0))
        ttk.Label(suspect_detail_box, textvariable=self.suspect_alibi_var, wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(4, 0))
        ttk.Label(suspect_detail_box, textvariable=self.suspect_motive_var, wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(4, 0))

        accusation_box = ttk.LabelFrame(self.right_content, text="Accusation Screen", padding=10)
        accusation_box.pack(fill=tk.BOTH, expand=False, pady=(12, 0))

        self.acc_suspect = ttk.Combobox(accusation_box, state="readonly")
        self.acc_method = ttk.Combobox(accusation_box, state="readonly")
        self.acc_motive = ttk.Combobox(accusation_box, state="readonly")
        self.acc_evidence = ttk.Combobox(accusation_box, state="readonly")

        self._combo_row(accusation_box, "Suspect", self.acc_suspect, 0)
        self._combo_row(accusation_box, "Method", self.acc_method, 1)
        self._combo_row(accusation_box, "Motive", self.acc_motive, 2)
        self._combo_row(accusation_box, "Key evidence", self.acc_evidence, 3)

        button_row = ttk.Frame(accusation_box)
        button_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 6))
        ttk.Button(button_row, text="Submit Accusation", command=self._submit_accusation).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Reset Theory", command=self._reset_theory).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(
            accusation_box,
            textvariable=self.accusation_result_var,
            wraplength=360,
            justify=tk.LEFT,
            foreground="#c7d6ff",
        ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        accusation_box.columnconfigure(1, weight=1)

    def _combo_row(self, parent: ttk.Frame, label: str, combo: ttk.Combobox, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=(10, 0))

    def _refresh_case_list(self) -> None:
        self.case_listbox.delete(0, tk.END)
        for case in self.cases:
            prefix = "✓ " if case.id in self.solved_case_ids else ""
            self.case_listbox.insert(tk.END, f"{prefix}{case.title}")
        selected_index = next((index for index, case in enumerate(self.cases) if case.id == self.selected_case_id), 0)
        if self.cases:
            self.case_listbox.selection_set(selected_index)
            self.case_listbox.activate(selected_index)
            self.case_listbox.see(selected_index)

    def _sync_selection(self) -> None:
        selected_case = self.case_by_id.get(self.selected_case_id, self.cases[0] if self.cases else None)
        if not selected_case:
            return
        self.preview_title_var.set(selected_case.title)
        self.preview_victim_var.set(f"Victim: {selected_case.victim['name']} — {selected_case.victim['occupation']}")
        self.preview_location_var.set(f"Location: {selected_case.location}")
        if self.current_case and self.current_case.id == selected_case.id:
            self.preview_status_var.set("Status: open in the desk")
            self.open_button_var.set("Resume Case")
        elif self.current_case:
            self.preview_status_var.set("Status: selected, but another case is currently open")
            self.open_button_var.set("Open Selected Case")
        else:
            self.preview_status_var.set("Status: ready to open")
            self.open_button_var.set("Open Case")
        self._render_case_preview_buttons()

    def _render_case_preview_buttons(self) -> None:
        if self.current_case:
            self.close_button.state(["!disabled"])
        else:
            self.close_button.state(["disabled"])

    def _selected_case(self) -> CaseItem | None:
        return self.case_by_id.get(self.selected_case_id)

    def _on_case_selected(self, event: object | None = None) -> None:
        selection = self.case_listbox.curselection()
        if not selection:
            return
        case = self.cases[selection[0]]
        self.selected_case_id = case.id
        self.progress["selected_case_id"] = case.id
        save_progress(self.progress)
        self._sync_selection()
        self.status_var.set(f"Selected case: {case.title}. Click Open Case to begin.")

    def _open_selected_case(self) -> None:
        case = self._selected_case()
        if not case:
            return
        self.open_case_id = case.id
        self.current_case = case
        self.current_evidence_id = case.evidence[0].id if case.evidence else ""
        self.current_suspect_name = case.suspects[0].name if case.suspects else ""
        self.progress["open_case_id"] = case.id
        self.progress["selected_case_id"] = case.id
        save_progress(self.progress)
        self._refresh_case_list()
        self._sync_selection()
        self._sync_open_case_state()
        self._status_open_case(case)

    def _close_case(self) -> None:
        self.open_case_id = ""
        self.current_case = None
        self.current_evidence_id = ""
        self.current_suspect_name = ""
        self.progress["open_case_id"] = ""
        save_progress(self.progress)
        self._sync_selection()
        self._sync_open_case_state()
        self.status_var.set("Case closed. Select another case or resume the same one.")

    def _sync_open_case_state(self) -> None:
        if self.current_case:
            self.center_locked.pack_forget()
            self.right_locked.pack_forget()
            self.center_content.pack(fill=tk.BOTH, expand=True)
            self.right_content.pack(fill=tk.BOTH, expand=True)
            self.close_button.state(["!disabled"])
            self._render_case_contents(self.current_case)
            self._render_case_list_details(self.current_case)
        else:
            self.center_content.pack_forget()
            self.right_content.pack_forget()
            self.center_locked.pack(fill=tk.BOTH, expand=True)
            self.right_locked.pack(fill=tk.BOTH, expand=True)
            self.close_button.state(["disabled"])
            self._clear_case_fields()

    def _status_open_case(self, case: CaseItem) -> None:
        self.status_var.set(f"Case opened: {case.title} | Victim: {case.victim['name']} | Status: {case.status}")

    def _clear_case_fields(self) -> None:
        self.case_title_var.set("Case file locked")
        self.case_victim_var.set("Victim: —")
        self.case_location_var.set("Location: —")
        self.case_brief_var.set("Open a case to inspect its brief.")
        self.case_scene_var.set("")
        self.evidence_kind_var.set("No evidence selected")
        self.evidence_title_var.set("—")
        self.evidence_media_var.set("Media: —")
        self.evidence_summary_var.set("Pick a clue from the evidence list.")
        self.evidence_details_var.set("")
        self.evidence_preview_var.set("Evidence preview will appear here.")
        self.suspect_name_var.set("—")
        self.suspect_role_var.set("Role: —")
        self.suspect_profile_var.set("Select a suspect to review their profile.")
        self.suspect_relationship_var.set("Relationship: —")
        self.suspect_alibi_var.set("Alibi: —")
        self.suspect_motive_var.set("Motive: —")
        self.notes_listbox.delete(0, tk.END)
        self.notes_count_var.set("0 notes")
        self.evidence_listbox.delete(0, tk.END)
        self.suspect_listbox.delete(0, tk.END)
        self.acc_suspect["values"] = []
        self.acc_method["values"] = []
        self.acc_motive["values"] = []
        self.acc_evidence["values"] = []
        self._reset_theory()

    def _render_case_contents(self, case: CaseItem) -> None:
        self.case_title_var.set(case.title)
        self.case_victim_var.set(f"Victim: {case.victim['name']} — {case.victim['occupation']}")
        self.case_location_var.set(f"Location: {case.location}")
        self.case_brief_var.set(case.brief)
        self.case_scene_var.set(case.scene)
        self._render_evidence_list(case)
        self._render_suspect_list(case)
        self._render_accusation_options(case)
        self._render_notes()
        self._select_default_evidence(case)
        self._select_default_suspect(case)

    def _render_case_list_details(self, case: CaseItem) -> None:
        self.preview_title_var.set(case.title)
        self.preview_victim_var.set(f"Victim: {case.victim['name']} — {case.victim['occupation']}")
        self.preview_location_var.set(f"Location: {case.location}")
        if self.current_case and self.current_case.id == case.id:
            self.preview_status_var.set("Status: open in the desk")
            self.open_button_var.set("Resume Case")
        else:
            self.preview_status_var.set("Status: ready to open")
            self.open_button_var.set("Open Case")

    def _render_evidence_list(self, case: CaseItem) -> None:
        self.evidence_listbox.delete(0, tk.END)
        for evidence in case.evidence:
            self.evidence_listbox.insert(tk.END, evidence_label(evidence))

    def _render_suspect_list(self, case: CaseItem) -> None:
        self.suspect_listbox.delete(0, tk.END)
        for suspect in case.suspects:
            self.suspect_listbox.insert(tk.END, f"{suspect.name} — {suspect.role}")

    def _render_accusation_options(self, case: CaseItem) -> None:
        self.acc_suspect["values"] = ["Select suspect"] + [suspect.name for suspect in case.suspects]
        self.acc_method["values"] = ["Select method"] + list(dict.fromkeys(case.methods))
        self.acc_motive["values"] = ["Select motive"] + list(dict.fromkeys(case.motives))
        self.acc_evidence["values"] = ["Select evidence"] + [evidence_label(item) for item in case.evidence]
        self._reset_theory()

    def _select_default_evidence(self, case: CaseItem) -> None:
        if not case.evidence:
            return
        self.evidence_listbox.selection_clear(0, tk.END)
        self.evidence_listbox.selection_set(0)
        self.evidence_listbox.activate(0)
        self._on_evidence_selected()

    def _select_default_suspect(self, case: CaseItem) -> None:
        if not case.suspects:
            return
        self.suspect_listbox.selection_clear(0, tk.END)
        self.suspect_listbox.selection_set(0)
        self.suspect_listbox.activate(0)
        self._on_suspect_selected()

    def _on_evidence_selected(self, event: object | None = None) -> None:
        if not self.current_case:
            return
        selection = self.evidence_listbox.curselection()
        if not selection:
            return
        evidence = self.current_case.evidence[selection[0]]
        self.current_evidence_id = evidence.id
        self._render_evidence_details(evidence)

    def _on_suspect_selected(self, event: object | None = None) -> None:
        if not self.current_case:
            return
        selection = self.suspect_listbox.curselection()
        if not selection:
            return
        suspect = self.current_case.suspects[selection[0]]
        self.current_suspect_name = suspect.name
        self._render_suspect_details(suspect)

    def _render_evidence_details(self, evidence: EvidenceItem) -> None:
        self.evidence_kind_var.set(evidence.type.upper())
        self.evidence_title_var.set(evidence.title)
        self.evidence_media_var.set(f"Media: {evidence.media_hint or 'No media file yet'}")
        self.evidence_summary_var.set(evidence.summary)
        self.evidence_details_var.set(evidence.details)

        media_path = resolve_media_path(evidence.media_hint)
        self._update_media_preview(evidence, media_path)

    def _update_media_preview(self, evidence: EvidenceItem, media_path: Path | None) -> None:
        self.preview_image = None
        if evidence.type == "photo":
            if media_path and media_path.suffix.lower() in IMAGE_EXTENSIONS:
                try:
                    self.preview_image = tk.PhotoImage(file=str(media_path))
                    self.evidence_preview_label.configure(image=self.preview_image, text="", compound=tk.CENTER)
                    self.evidence_preview_var.set(f"Previewing {media_path.name}")
                    self.open_media_button.state(["!disabled"])
                    return
                except tk.TclError:
                    pass
            if media_path:
                self.evidence_preview_var.set(
                    f"Photo file found: {media_path.name}\n\nTk can only preview PNG, GIF, PGM, and PPM files directly. Use Open Media to view it in your desktop app."
                )
                self.open_media_button.state(["!disabled"])
            else:
                self.evidence_preview_var.set(
                    "Photo evidence placeholder\n\nNo image file is attached yet. Add a PNG, GIF, JPG, or similar file later and the viewer can open it from the desktop."
                )
                self.open_media_button.state(["disabled"])
            self.evidence_preview_label.configure(image="", text=self.evidence_preview_var.get(), compound=tk.CENTER)
            return

        if evidence.type in {"audio", "video"}:
            if media_path:
                self.evidence_preview_var.set(
                    f"{evidence.type.title()} file found: {media_path.name}\n\nUse Open Media to launch it in your desktop player."
                )
                self.open_media_button.state(["!disabled"])
            else:
                self.evidence_preview_var.set(
                    f"{evidence.type.title()} evidence placeholder\n\nNo media file is attached yet. When you add one, Open Media will launch it externally."
                )
                self.open_media_button.state(["disabled"])
            self.evidence_preview_label.configure(image="", text=self.evidence_preview_var.get(), compound=tk.CENTER)
            return

        self.evidence_preview_var.set(
            "Document / transcript evidence\n\nRead the summary and details. If a file is attached later, Open Media will launch it externally."
        )
        self.evidence_preview_label.configure(image="", text=self.evidence_preview_var.get(), compound=tk.CENTER)
        self.open_media_button.state(["!disabled"] if media_path else ["disabled"])

    def _render_suspect_details(self, suspect: SuspectItem) -> None:
        self.suspect_name_var.set(suspect.name)
        self.suspect_role_var.set(f"Role: {suspect.role}")
        self.suspect_profile_var.set(suspect.profile)
        self.suspect_relationship_var.set(f"Relationship: {suspect.relationship}")
        self.suspect_alibi_var.set(f"Alibi: {suspect.alibi}")
        self.suspect_motive_var.set(f"Motive: {suspect.motive}")

    def _render_notes(self) -> None:
        self.notes_listbox.delete(0, tk.END)
        notes = self.progress.get("notes", {}).get(self.current_case.id, []) if self.current_case else []
        for note in notes:
            self.notes_listbox.insert(tk.END, note)
        self.notes_count_var.set(f"{len(notes)} note{'s' if len(notes) != 1 else ''}")

    def _add_note(self) -> None:
        if not self.current_case:
            return
        note = self.new_note_var.get().strip()
        if not note:
            return
        notes = self.progress.setdefault("notes", {}).setdefault(self.current_case.id, [])
        notes.append(note)
        self.new_note_var.set("")
        save_progress(self.progress)
        self._render_notes()
        self.status_var.set(f"Saved note for {self.current_case.title}.")

    def _delete_selected_note(self) -> None:
        if not self.current_case:
            return
        selection = self.notes_listbox.curselection()
        if not selection:
            return
        notes = self.progress.setdefault("notes", {}).setdefault(self.current_case.id, [])
        if selection[0] < len(notes):
            notes.pop(selection[0])
            save_progress(self.progress)
            self._render_notes()
            self.status_var.set(f"Removed a note from {self.current_case.title}.")

    def _clear_notes(self) -> None:
        if not self.current_case:
            return
        self.progress.setdefault("notes", {})[self.current_case.id] = []
        save_progress(self.progress)
        self._render_notes()
        self.status_var.set(f"Cleared notes for {self.current_case.title}.")

    def _open_current_media(self) -> None:
        if not self.current_case or not self.current_evidence_id:
            return
        evidence = next((item for item in self.current_case.evidence if item.id == self.current_evidence_id), None)
        if not evidence:
            return
        media_path = resolve_media_path(evidence.media_hint)
        if media_path and open_external_file(media_path):
            self.status_var.set(f"Opened media: {media_path.name}")
        else:
            self.status_var.set("No media file is available to open yet.")

    def _reset_theory(self) -> None:
        self.acc_suspect.set("Select suspect")
        self.acc_method.set("Select method")
        self.acc_motive.set("Select motive")
        self.acc_evidence.set("Select evidence")
        self.accusation_result_var.set("Choose your final theory and submit it here.")

    def _submit_accusation(self) -> None:
        if not self.current_case:
            return
        suspect = self.acc_suspect.get()
        method = self.acc_method.get()
        motive = self.acc_motive.get()
        evidence = self.acc_evidence.get()
        if any(value.startswith("Select ") or not value for value in (suspect, method, motive, evidence)):
            self.accusation_result_var.set("Choose a suspect, method, motive, and key evidence before submitting.")
            return

        solution = self.current_case.solution
        correct_evidence = evidence_label(
            next(item for item in self.current_case.evidence if item.id == solution["key_evidence"])
        )
        matches = {
            "suspect": suspect == solution["killer"],
            "method": method == solution["method"],
            "motive": motive == solution["motive"],
            "evidence": evidence == correct_evidence,
        }
        score = sum(matches.values())
        if score == 4:
            self.solved_case_ids.add(self.current_case.id)
            self.progress["solved"] = sorted(self.solved_case_ids)
            save_progress(self.progress)
            self._refresh_case_list()
            self.accusation_result_var.set("Case solved. All four parts of the accusation are correct.")
            self.status_var.set(f"Case solved: {self.current_case.title}")
            return

        failed = ", ".join(name for name, ok in matches.items() if not ok)
        self.accusation_result_var.set(f"Accusation rejected. You matched {score}/4 parts. Review: {failed}.")
        self.status_var.set(f"Accusation failed for {self.current_case.title}.")


def main() -> None:
    app = CauseOfDeathApp()
    app.mainloop()


if __name__ == "__main__":
    main()
