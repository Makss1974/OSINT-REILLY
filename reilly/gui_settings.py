"""Settings window: language and AI key, and the list of RSS sources
(switch on/off, test, delete, add by site address)."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.parse import urlparse

from . import config, llm, profiles
from .collectors import rss
from .http import get_text
from .i18n import LANG_NAMES, LANGS


def open_settings(app) -> None:
    t = app.t
    win = tk.Toplevel(app.root)
    win.title(t("settings"))
    win.geometry("1150x640")
    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=8, pady=8)
    nb.add(_general(app, win, nb), text=t("general"))
    nb.add(_sources(app, nb), text=t("sources_tab"))


def _general(app, win, parent) -> ttk.Frame:
    t = app.t
    f = ttk.Frame(parent, padding=12)
    f.columnconfigure(1, weight=1)
    lang = ttk.Combobox(f, values=[LANG_NAMES[x] for x in LANGS], state="readonly", width=16)
    lang.set(LANG_NAMES[t.lang])
    key = tk.StringVar(value=config.OPENROUTER_TOKEN)
    model = tk.StringVar(value=config.OPENROUTER_MODEL)
    contact = tk.StringVar(value=config.CONTACT)
    models = ttk.Combobox(f, textvariable=model, values=llm.RECOMMENDED, width=58)
    cost = ttk.Label(f, text="", foreground="#667", wraplength=560, justify="left")
    rows = [(t("language"), lang),
            (t("api_key"), ttk.Entry(f, textvariable=key, show="•", width=60)),
            (t("model_label"), models),
            ("", cost),
            (t("contact_label"), ttk.Entry(f, textvariable=contact, width=60))]
    for n, (label, widget) in enumerate(rows):
        ttk.Label(f, text=label).grid(row=n, column=0, sticky="w", pady=4, padx=(0, 10))
        widget.grid(row=n, column=1, sticky="w", pady=4)

    def show_price(_event=None):
        name = model.get().strip()
        if not name:
            cost.configure(text=t("free_models_note"))
            return
        cost.configure(text="…")

        def job():  # network: runs off the UI thread, result comes back via the queue
            try:
                p = llm.price(name)
            except Exception:  # noqa: BLE001 - offline: just no price
                p = None
            app.queue.put(("call", lambda: done(p)))

        def done(p):
            if model.get().strip() != name or not cost.winfo_exists():
                return
            if p is None:
                cost.configure(text=t("price_unknown"))
            else:
                cost.configure(text=f"≈ ${p[2]:.4f} {t('per_task')}   "
                                    f"(${p[0]:.3f} / ${p[1]:.3f} {t('per_million')})")

        threading.Thread(target=job, daemon=True).start()

    models.bind("<<ComboboxSelected>>", show_price)
    models.bind("<Return>", show_price)
    models.bind("<FocusOut>", show_price)
    show_price()
    state = ttk.Label(f, text=t("key_set") if config.OPENROUTER_TOKEN else t("key_missing"))
    state.grid(row=len(rows), column=1, sticky="w", pady=(0, 8))
    ttk.Label(f, text=t("key_note"), foreground="#667", wraplength=700, justify="left").grid(
        row=len(rows) + 1, column=0, columnspan=2, sticky="w", pady=(0, 12))

    def save():
        config.update_env({"OPENROUTER_API_TOKEN": key.get().strip(),
                           "OPENROUTER_MODEL": model.get().strip(),
                           "REILLY_CONTACT": contact.get().strip()})
        state.configure(text=t("key_set") if config.OPENROUTER_TOKEN else t("key_missing"))
        new_lang = LANGS[[LANG_NAMES[x] for x in LANGS].index(lang.get())]
        if new_lang != app.t.lang:
            app.lang_box.set(lang.get())
            app.change_lang()
            win.destroy()
            return
        app.status.configure(text=t("saved_ok"))

    buttons = ttk.Frame(f)
    buttons.grid(row=len(rows) + 2, column=0, columnspan=2, sticky="w")
    ttk.Button(buttons, text=t("save"), command=save).pack(side="left")
    from .gui import open_path
    for name in ("profiles.json", "sources.json"):
        ttk.Button(buttons, text=f"{t('open_file')} {name}",
                   command=lambda n=name: open_path(config.ROOT / n)).pack(side="left", padx=6)
    return f


def _sources(app, parent) -> ttk.Frame:
    t = app.t
    f = ttk.Frame(parent, padding=8)
    cols = ("on", "name", "lang", "tier", "tags", "url")
    heads = (t("enabled_col"), t("name_label"), t("language"), t("tier_label").split(" (")[0],
             t("tags_col"), "URL")
    table = ttk.Frame(f)
    table.pack(fill="both", expand=True)
    tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
    ysb = ttk.Scrollbar(table, command=tree.yview)
    tree.configure(yscrollcommand=ysb.set)
    ysb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    for c, h, w in zip(cols, heads, (50, 180, 60, 60, 220, 420)):
        tree.heading(c, text=h)
        tree.column(c, width=w, stretch=c == "url")
    msg = ttk.Label(f, text="")

    def refresh():
        tree.delete(*tree.get_children())
        for fid, feed in profiles.all_feeds().items():
            tree.insert("", "end", iid=fid, values=(
                "✔" if feed.get("enabled", True) else "—", feed["name"], feed.get("lang", ""),
                feed.get("tier", 2), ", ".join(feed.get("tags", [])), feed["url"]))

    def toggle():
        fid = tree.focus()
        if fid:
            feeds = profiles.all_feeds()
            feeds[fid]["enabled"] = not feeds[fid].get("enabled", True)
            if feeds[fid]["enabled"]:
                del feeds[fid]["enabled"]
            profiles.save_feeds(feeds)
            refresh()
            tree.focus(fid)
            tree.selection_set(fid)

    def delete():
        fid = tree.focus()
        if fid and messagebox.askyesno(t("delete"), f"{t('confirm_delete')}\n{fid}", parent=f):
            feeds = profiles.all_feeds()
            feeds.pop(fid, None)
            profiles.save_feeds(feeds)
            refresh()

    def background(job, done):
        """Network off the UI thread; the result comes back through the app queue."""
        def run():
            try:
                out = job()
            except Exception as exc:  # noqa: BLE001 - shown to the analyst
                out = exc
            app.queue.put(("call", lambda: f.winfo_exists() and done(out)))
        threading.Thread(target=run, daemon=True).start()

    def test():
        fid = tree.focus()
        if not fid:
            return
        feed = profiles.all_feeds()[fid]
        msg.configure(text=f"{t('running')}… {feed['name']}")

        def done(out):
            if isinstance(out, Exception):
                msg.configure(text=f"✘ {feed['name']}: {str(out)[:150]}")
            else:
                msg.configure(text=f"✔ {feed['name']}: {len(out)} {t('items')}"
                                   + (f" — {out[0].title[:90]}" if out else ""))
        background(lambda: rss.parse(get_text(feed["url"], ttl=0), feed), done)

    buttons = ttk.Frame(f)
    buttons.pack(fill="x", pady=6)
    ttk.Button(buttons, text=t("toggle"), command=toggle).pack(side="left")
    ttk.Button(buttons, text=t("test"), command=test).pack(side="left", padx=6)
    ttk.Button(buttons, text=t("delete"), command=delete).pack(side="left")
    msg.pack(anchor="w")

    add = ttk.LabelFrame(f, text=t("add_source"), padding=8)
    add.pack(fill="x", pady=(8, 0))
    url, name = tk.StringVar(), tk.StringVar()
    lang = tk.StringVar(value=t.lang)
    tier = tk.StringVar(value="2")
    focused = tk.BooleanVar(value=False)
    ttk.Label(add, text=t("site_or_rss")).grid(row=0, column=0, sticky="w")
    ttk.Entry(add, textvariable=url, width=50).grid(row=0, column=1, sticky="w", padx=6)
    ttk.Label(add, text=t("name_label")).grid(row=0, column=2, sticky="w")
    ttk.Entry(add, textvariable=name, width=22).grid(row=0, column=3, sticky="w", padx=6)
    ttk.Label(add, text=t("language")).grid(row=1, column=0, sticky="w", pady=4)
    small = ttk.Frame(add)
    small.grid(row=1, column=1, columnspan=3, sticky="w", padx=6)
    ttk.Combobox(small, textvariable=lang, values=list(LANGS) + ["ru", "cs", "sk", "lt", "ro"],
                 width=5).pack(side="left")
    ttk.Label(small, text=t("tier_label")).pack(side="left", padx=(14, 4))
    ttk.Combobox(small, textvariable=tier, values=["1", "2", "3"], width=3,
                 state="readonly").pack(side="left")
    ttk.Checkbutton(small, text=t("focused_label"), variable=focused).pack(side="left", padx=14)
    ttk.Label(add, text=t("to_profiles")).grid(row=2, column=0, sticky="nw")
    boxes = ttk.Frame(add)
    boxes.grid(row=2, column=1, columnspan=3, sticky="w", padx=6)
    use = {}
    for n, (pid, tag) in enumerate(profiles.profile_tags().items()):
        use[tag] = tk.BooleanVar(value=False)
        ttk.Checkbutton(boxes, text=t("p_" + pid), variable=use[tag]).grid(
            row=n // 4, column=n % 4, sticky="w", padx=(0, 12))

    def find_add():
        address = url.get().strip()
        if not address:
            return
        msg.configure(text=f"{t('running')}… {address}")

        def done(out):
            if isinstance(out, Exception):
                msg.configure(text=f"✘ {t('no_feed')}: {address}")
                return
            known = {x["url"] for x in profiles.all_feeds().values()}
            if out["url"] in known:
                msg.configure(text=f"= {out['url']}")
                return
            title = name.get().strip() or out["title"] or urlparse(out["url"]).netloc
            tags = [tag for tag, v in use.items() if v.get()]
            fid = profiles.add_feed(title, out["url"], lang.get().strip() or t.lang,
                                    int(tier.get()), tags, focused.get())
            refresh()
            tree.see(fid)
            tree.selection_set(fid)
            msg.configure(text=f"✔ {t('added')}: {title} — {out['items']} {t('items')} "
                               f"({out['url']})")
            url.set("")
            name.set("")
        background(lambda: rss.discover(address), done)

    ttk.Button(add, text=t("find_add"), command=find_add).grid(row=3, column=1, sticky="w",
                                                               padx=6, pady=(8, 0))
    refresh()
    return f
