"""Desktop window (tkinter, part of the standard library).

Left: standing profiles and a form for an own topic. Right: one tab per run,
inside it one table per report section. Runs go in a background thread; the
window polls a queue so it never freezes.
"""

import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser
import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk
from typing import Any, Dict, List, Tuple

from . import config, journal, pipeline, planner, profiles, report
from .i18n import LANG_NAMES, LANGS, Translator

Job = Tuple[str, Any]          # ("profile", pid) or ("custom", spec dict)


def _split(value: str) -> list:
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def open_path(path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 - local folder chosen by the program
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.t = Translator(config.saved_lang())
        self.queue: "queue.Queue[tuple]" = queue.Queue()
        self.worker: threading.Thread = None
        self.results: List[Dict[str, Any]] = []
        self.checks = {pid: tk.BooleanVar(value=False) for pid in profiles.profile_ids()}
        self.form = {k: tk.StringVar(value=v) for k, v in (
            ("topic", ""), ("assets", ""), ("countries", ""), ("langs", ""), ("hypothesis", ""),
            ("prior", "0.5"), ("horizon", "30"), ("polarity", "risk"), ("direction", "auto"))}
        self.use_llm = tk.BooleanVar(value=True)
        self.log_lines: List[str] = []
        w, h = min(1400, root.winfo_screenwidth() - 40), min(860, root.winfo_screenheight() - 80)
        root.geometry(f"{w}x{h}+10+10")
        root.minsize(980, 600)
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        self.build()
        root.after(150, self.poll)

    # ---------- layout ----------
    def build(self) -> None:
        t = self.t
        for w in self.root.winfo_children():
            w.destroy()
        self.root.title(t("title"))

        top = ttk.Frame(self.root, padding=(8, 6))
        top.pack(fill="x")
        ttk.Label(top, text=t("language") + ":").pack(side="left")
        self.lang_box = ttk.Combobox(top, values=[LANG_NAMES[x] for x in LANGS], width=12,
                                     state="readonly")
        self.lang_box.set(LANG_NAMES[t.lang])
        self.lang_box.bind("<<ComboboxSelected>>", self.change_lang)
        self.lang_box.pack(side="left", padx=(4, 16))
        ttk.Button(top, text=t("run_selected"), command=self.run_selected).pack(side="left", padx=2)
        ttk.Button(top, text=t("run_all"), command=self.run_all).pack(side="left", padx=2)
        ttk.Checkbutton(top, text="LLM", variable=self.use_llm).pack(side="left", padx=10)
        ttk.Button(top, text=t("open_reports"),
                   command=lambda: open_path(config.REPORTS_DIR)).pack(side="right", padx=2)
        ttk.Button(top, text=t("journal"), command=self.open_journal).pack(side="right", padx=2)

        bottom = ttk.Frame(self.root, padding=(8, 4, 8, 8))
        bottom.pack(side="bottom", fill="x")
        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8)
        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        body.add(left, weight=0)
        right = ttk.Frame(body)
        body.add(right, weight=1)

        box = ttk.LabelFrame(left, text=t("profiles"), padding=6)
        box.pack(fill="x")
        for pid, var in self.checks.items():
            ttk.Checkbutton(box, text=t("p_" + pid), variable=var).pack(anchor="w", pady=1)

        form = ttk.LabelFrame(left, text=t("custom"), padding=6)
        form.pack(fill="x", pady=(8, 0))
        fields = [("topic", t("topic_prompt").split(" / ")[0]),
                  ("assets", t("assets_prompt").split(" (")[0]),
                  ("countries", t("countries_prompt").split(" (")[0]),
                  ("langs", t("langs_label")),
                  ("hypothesis", t("hypothesis_prompt").split(" (")[0]),
                  ("prior", t("prior")), ("horizon", t("horizon_prompt").split(" (")[0])]
        form.columnconfigure(1, weight=1)
        for n, (key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=n, column=0, sticky="w", padx=(0, 6), pady=2)
            ttk.Entry(form, textvariable=self.form[key], width=26).grid(row=n, column=1,
                                                                         sticky="ew", pady=2)
        row = ttk.Frame(form)
        row.grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=2)
        ttk.Combobox(row, textvariable=self.form["polarity"], values=["risk", "positive"],
                     width=9, state="readonly").pack(side="left")
        ttk.Combobox(row, textvariable=self.form["direction"], values=["auto", "up", "down"],
                     width=6, state="readonly").pack(side="left", padx=6)
        ttk.Button(form, text=t("run_custom"), command=self.run_custom).grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        bar = ttk.Frame(right)
        bar.pack(fill="x")
        ttk.Label(bar, text=t("double_click"), foreground="#667").pack(side="left")
        ttk.Button(bar, text=t("close_tab"), command=self.close_tab).pack(side="right")
        ttk.Button(bar, text=t("copy_ai"), command=self.copy_for_ai).pack(side="right", padx=4)
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True, pady=(4, 0))
        for r in self.results:
            self.add_result(r, select=False)

        status = ttk.Frame(bottom)
        status.pack(fill="x")
        self.status = ttk.Label(status, text="")
        self.status.pack(side="left")
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=220)
        self.progress.pack(side="right")
        self.log = tk.Text(bottom, height=5, wrap="word", font=("Consolas", 9))
        self.log.pack(fill="x", pady=(4, 0))
        self.log.insert("end", "\n".join(self.log_lines[-200:]))
        self.log.see("end")
        self.log.configure(state="disabled")
        if self.worker and self.worker.is_alive():
            self.progress.start(12)
            self.status.configure(text=self.t("running") + "…")

    def change_lang(self, _event=None) -> None:
        lang = LANGS[[LANG_NAMES[x] for x in LANGS].index(self.lang_box.get())]
        config.save_lang(lang)
        self.t = Translator(lang)
        self.build()

    # ---------- results ----------
    def add_result(self, r: Dict[str, Any], select: bool = True) -> None:
        """One run = section list on the left, the chosen table on the right
        (a list instead of nested tabs, so no section ever falls off-screen)."""
        frame = ttk.Frame(self.nb)
        names = tk.Listbox(frame, width=24, exportselection=False, activestyle="none",
                           font=("Segoe UI", 10))
        names.pack(side="left", fill="y")
        view = ttk.Frame(frame)
        view.pack(side="left", fill="both", expand=True, padx=(6, 0))
        title = ttk.Label(view, text="", font=("Segoe UI", 10, "bold"))
        title.pack(anchor="w", pady=(0, 4))
        pages = []
        for s in report.sections(r, self.t, full=True):
            if s["rows"]:
                pages.append((s["title"], self.table(view, s)))
        if r.get("summary"):
            box = ttk.Frame(view)
            text = tk.Text(box, wrap="word", font=("Segoe UI", 10), padx=10, pady=8)
            scroll = ttk.Scrollbar(box, command=text.yview)
            text.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            text.pack(fill="both", expand=True)
            text.insert("end", r["summary"] + "\n\n" + self.t("disclaimer"))
            text.configure(state="disabled")
            pages.append((self.t("summary_tab"), box))
        for label, _ in pages:
            names.insert("end", label.split(" — ")[0])

        def show(_event=None):
            sel = names.curselection()
            if not sel:
                return
            for _, page in pages:
                page.pack_forget()
            label, page = pages[sel[0]]
            title.configure(text=label)
            page.pack(fill="both", expand=True)

        names.bind("<<ListboxSelect>>", show)
        if pages:
            names.selection_set(0)
            show()
        p = r["plan"]
        name = self.t("p_" + p["profile"]) if p.get("profile") else p["topic"]
        self.nb.add(frame, text=name[:28])
        if select:
            self.nb.select(frame)

    def table(self, parent, s: Dict[str, Any]) -> ttk.Frame:
        frame = ttk.Frame(parent)
        cols = [str(c) or f"#{i + 1}" for i, c in enumerate(s["columns"])]
        ids = [f"c{i}" for i in range(len(cols))]
        tree = ttk.Treeview(frame, columns=ids, show="headings" if any(s["columns"]) else "",
                            selectmode="browse")
        ysb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        ysb.pack(side="right", fill="y")
        xsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True)
        measure = tkfont.nametofont("TkDefaultFont").measure
        for i, (cid, name) in enumerate(zip(ids, cols)):
            sample = [name] + [str(row[i]) for row in s["rows"][:60] if i < len(row)]
            tree.heading(cid, text=name if any(s["columns"]) else "")
            tree.column(cid, width=min(700, max(50, max(measure(x) for x in sample) + 18)),
                        stretch=i == 0 or s["key"] == "plan", anchor="w")
        danger, warning = self.t("lvl_DANGER"), self.t("lvl_WARNING")
        tree.tag_configure("danger", background="#f8d7da")
        tree.tag_configure("warning", background="#fff3cd")
        links = s.get("links") or []
        urls = {}
        for n, row in enumerate(s["rows"]):
            values = [str(x).replace("\n", " ") for x in row]
            tag = ("danger",) if s["key"] == "hazards" and values[0] == danger else \
                  ("warning",) if s["key"] == "hazards" and values[0] == warning else ()
            iid = tree.insert("", "end", values=values, tags=tag)
            if n < len(links) and links[n]:
                urls[iid] = links[n]

        def on_double(_event):
            sel = tree.focus()
            if sel in urls and urls[sel].startswith(("http://", "https://")):
                webbrowser.open(urls[sel])

        tree.bind("<Double-1>", on_double)
        return frame

    def copy_for_ai(self) -> None:
        current = self.nb.select()
        if not current:
            return
        r = self.results[self.nb.index(current)]
        self.root.clipboard_clear()
        self.root.clipboard_append(report.to_ai_text(r, self.t))
        self.status.configure(text=self.t("copied"))

    def close_tab(self) -> None:
        current = self.nb.select()
        if current:
            idx = self.nb.index(current)
            self.nb.forget(current)
            del self.results[idx]

    # ---------- runs ----------
    def run_selected(self) -> None:
        self.start([("profile", pid) for pid, v in self.checks.items() if v.get()])

    def run_all(self) -> None:
        self.start([("profile", pid) for pid in self.checks])

    def run_custom(self) -> None:
        f = {k: v.get().strip() for k, v in self.form.items()}
        if not f["topic"]:
            return
        try:
            prior, horizon = float(f["prior"] or 0.5), int(f["horizon"] or 30)
        except ValueError:
            messagebox.showerror(self.t("rejected"), f"{self.t('prior')} / "
                                 f"{self.t('horizon_prompt')}")
            return
        self.start([("custom", {"topic": f["topic"], "assets": _split(f["assets"]) or None,
                                "countries": _split(f["countries"]) or None,
                                "langs": _split(f["langs"]) or None,
                                "hypothesis": f["hypothesis"], "polarity": f["polarity"],
                                "asset_direction": f["direction"], "prior": prior,
                                "horizon": horizon})])

    def start(self, jobs: List[Job]) -> None:
        if not jobs:
            return
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(self.t("title"), self.t("busy"))
            return
        self.progress.start(12)
        self.status.configure(text=self.t("running") + "…")
        self.worker = threading.Thread(target=self.work, args=(jobs, self.t, self.use_llm.get()),
                                       daemon=True)
        self.worker.start()

    def work(self, jobs: List[Job], t: Translator, use_llm: bool) -> None:
        """Background thread: never touches widgets, only the queue."""
        for kind, arg in jobs:
            name = t("p_" + arg) if kind == "profile" else arg["topic"]
            try:
                if kind == "profile":
                    plan = profiles.build_plan(arg, t.lang)
                else:
                    plan = planner.build(arg["topic"], lang=t.lang, assets=arg["assets"],
                                         countries=arg["countries"], urls=[],
                                         search_langs=arg["langs"],
                                         hypothesis=arg["hypothesis"], polarity=arg["polarity"],
                                         asset_direction=arg["asset_direction"],
                                         prior=arg["prior"], horizon_days=arg["horizon"],
                                         translate=use_llm)
                self.queue.put(("log", f"▶ {name}"))
                collected = pipeline.collect(plan, lambda m, n=name: self.queue.put(
                    ("status", f"{n}: {m}")))
                result = pipeline.analyze(plan, collected, use_llm=use_llm)
                paths = report.save(result, t)
                self.queue.put(("result", name, result,
                                str(paths["html"].relative_to(config.ROOT))))
            except planner.Rejected as exc:
                self.queue.put(("log", f"✘ {name}: {t('rejected')}: {t(str(exc))}"))
            except Exception as exc:  # keep the window alive, report the failure
                self.queue.put(("log", f"✘ {name}: {exc}"))
                self.queue.put(("log", traceback.format_exc(limit=3)))
        self.queue.put(("done",))

    def poll(self) -> None:
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == "status":
                    self.status.configure(text=msg[1][:150])
                elif msg[0] == "log":
                    self.write_log(msg[1])
                elif msg[0] == "result":
                    _, name, r, path = msg
                    self.results.append(r)
                    self.add_result(r)
                    errs = len(r["errors"])
                    self.write_log(f"✔ {name}: {r['counts']['articles']} / {r['n_stories']}"
                                   f"{f', {errs} ' + self.t('errors').lower() if errs else ''}"
                                   f" → {path}")
                elif msg[0] == "done":
                    self.progress.stop()
                    self.progress["value"] = 0
                    self.status.configure(text=self.t("finished"))
                elif msg[0] == "journal":
                    msg[1]()
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def write_log(self, line: str) -> None:
        self.log_lines.append(line)
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------- forecast journal ----------
    def open_journal(self) -> None:
        t = self.t
        win = tk.Toplevel(self.root)
        win.title(t("journal"))
        win.geometry("1000x520")
        cols = ("id", t("question"), "p", t("due"), t("outcome"))
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c, w in zip(cols, (90, 600, 60, 100, 80)):
            tree.heading(c, text=c)
            tree.column(c, width=w, stretch=c == t("question"))
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        score = ttk.Label(win, text="")
        score.pack(anchor="w", padx=8)

        def refresh():
            tree.delete(*tree.get_children())
            sb = journal.scoreboard()
            for row in reversed(sb["rows"]):
                outcome = "—" if row["outcome"] is None else ("✔" if row["outcome"] else "✘")
                tree.insert("", "end", iid=row["id"], values=(
                    row["id"], row["question"], f"{row['p'] * 100:.0f}%",
                    journal.fmt_date(row["due"]), outcome))
            na = "—"
            score.configure(text=f"{t('brier')}: {sb['brier'] if sb['brier'] is not None else na}"
                                 f"   {t('hit_rate')}: "
                                 f"{sb['hit_rate'] if sb['hit_rate'] is not None else na}"
                                 f"   ({sb['resolved']}/{sb['total']})")

        def resolve(outcome: bool):
            if tree.focus():
                journal.resolve(tree.focus(), outcome)
                refresh()

        buttons = ttk.Frame(win, padding=8)
        buttons.pack(fill="x")
        ttk.Button(buttons, text=t("yes"), command=lambda: resolve(True)).pack(side="left")
        ttk.Button(buttons, text=t("no"), command=lambda: resolve(False)).pack(side="left", padx=6)
        refresh()

        def auto():  # market forecasts resolve from prices: network, so off the UI thread
            try:
                journal.auto_resolve()
            finally:
                self.queue.put(("journal", lambda: win.winfo_exists() and refresh()))

        threading.Thread(target=auto, daemon=True).start()


def main() -> None:
    config.ensure_dirs()
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()
