#!/usr/bin/env python3
"""OSINT-REILLY v5 — entry point.

  python main.py                         desktop window (tkinter)
  python main.py console                 interactive console menu
  python main.py profile [ids]           standing profiles (empty = all)
  python main.py task "..."              agent: picks sources and analyses a task
  python main.py run "topic" [options]   one analysis
  python main.py topics topics.json      batch of topics
  python main.py journal                 forecast journal and scores
  python main.py resolve <id> yes|no     close a hypothesis forecast
"""

import argparse
import json
import logging
import sys

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from reilly import agent, config, journal, pipeline, planner, profiles, report
from reilly.i18n import LANG_NAMES, LANGS, Translator

console = Console()
def split(value: str) -> list:
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def show(r: dict, t: Translator) -> None:
    for s in report.sections(r, t):
        table = Table(title=escape(s["title"]), title_justify="left",
                      header_style="bold cyan", show_header=any(s["columns"]))
        for col in s["columns"]:
            table.add_column(escape(str(col)), overflow="fold")
        for row in s["rows"]:
            table.add_row(*[escape(str(x)) for x in row])
        console.print(table)
    if r["summary"]:
        console.rule(t("summary"))
        console.print(escape(r["summary"]))
    console.print(f"[dim]{t('disclaimer')}[/dim]")


def run_one(spec: dict, t: Translator, use_llm: bool = True, record: bool = True) -> None:
    try:
        plan = planner.build(
            spec["topic"], lang=t.lang, assets=spec.get("assets"),
            countries=spec.get("countries"), urls=spec.get("urls"),
            search_langs=spec.get("langs"), hypothesis=spec.get("hypothesis", ""),
            polarity=spec.get("polarity", "risk"),
            asset_direction=spec.get("asset_direction", "auto"),
            prior=float(spec.get("prior", 0.5)),
            horizon_days=int(spec.get("horizon", 30)), translate=use_llm,
        )
    except planner.Rejected as exc:
        console.print(f"[red]{t('rejected')}: {t(str(exc))}[/red]")
        return
    with console.status(t("collecting")) as status:
        collected = pipeline.collect(plan, lambda msg: status.update(f"{t('collecting')}: {msg}"))
        result = pipeline.analyze(plan, collected, use_llm=use_llm, record_forecasts=record)
    show(result, t)
    paths = report.save(result, t)
    console.print(f"[green]{t('saved')}:[/green] " + "  ".join(str(p.relative_to(config.ROOT))
                                                            for p in paths.values()))


def run_profile(pid: str, t: Translator, use_llm: bool = True, record: bool = True,
                horizon: int = 30) -> None:
    plan = profiles.build_plan(pid, t.lang, horizon_days=horizon)
    console.rule(f"[bold]{escape(t('p_' + pid))}[/bold]")
    with console.status(t("collecting")) as status:
        collected = pipeline.collect(plan, lambda msg: status.update(f"{t('collecting')}: {msg}"))
        result = pipeline.analyze(plan, collected, use_llm=use_llm, record_forecasts=record)
    show(result, t)
    paths = report.save(result, t)
    console.print(f"[green]{t('saved')}:[/green] " + "  ".join(str(p.relative_to(config.ROOT))
                                                            for p in paths.values()))


def show_journal(t: Translator) -> None:
    n = journal.auto_resolve()
    if n:
        console.print(f"{n} {t('resolved_auto')}")
    sb = journal.scoreboard()
    table = Table(title=t("journal"), title_justify="left", header_style="bold cyan")
    for col in ("id", t("question"), "p", t("due"), t("outcome")):
        table.add_column(col, overflow="fold")
    for row in sb["rows"][-40:]:
        outcome = "—" if row["outcome"] is None else ("✔" if row["outcome"] else "✘")
        table.add_row(row["id"], row["question"][:90], f"{row['p'] * 100:.0f}%",
                      journal.fmt_date(row["due"]), outcome)
    console.print(table)
    console.print(f"{t('brier')}: {sb['brier'] if sb['brier'] is not None else '—'}   "
                  f"{t('hit_rate')}: {sb['hit_rate'] if sb['hit_rate'] is not None else '—'}   "
                  f"({sb['resolved']}/{sb['total']})")


def run_topics(path: str, t: Translator, use_llm: bool) -> None:
    with open(path, encoding="utf-8") as fh:
        specs = json.load(fh)
    for spec in specs:
        console.rule(spec.get("topic", "")[:80])
        run_one(spec, t, use_llm)


def interactive(t: Translator) -> None:
    while True:
        console.rule(f"[bold]{t('title')}[/bold]  [{LANG_NAMES[t.lang]}]")
        console.print(t("menu"))
        choice = console.input(f"{t('choice')}: ").strip()
        if choice == "1":
            spec = {"topic": console.input(f"{t('topic_prompt')}: ")}
            spec["assets"] = split(console.input(f"{t('assets_prompt')}: ")) or None
            spec["countries"] = split(console.input(f"{t('countries_prompt')}: ")) or None
            spec["urls"] = split(console.input(f"{t('urls_prompt')}: "))
            spec["hypothesis"] = console.input(f"{t('hypothesis_prompt')}: ").strip()
            if spec["hypothesis"]:
                spec["polarity"] = "positive" if console.input(
                    f"{t('polarity_prompt')} ").strip().lower().startswith("p") else "risk"
                if spec.get("assets"):
                    spec["asset_direction"] = console.input(
                        f"{t('direction_prompt')} [auto]: ").strip().lower() or "auto"
                spec["prior"] = float(console.input(f"{t('prior_prompt')} [0.5]: ") or 0.5)
            spec["horizon"] = int(console.input(f"{t('horizon_prompt')} [30]: ") or 30)
            run_one(spec, t)
        elif choice == "2":
            run_topics(console.input(f"{t('topics_file')} [topics.example.json]: ")
                       or "topics.example.json", t, True)
        elif choice == "3":
            show_journal(t)
        elif choice == "4":
            fid = console.input(f"{t('forecast_id')}: ").strip()
            yes = console.input(f"{t('happened')} ").strip().lower().startswith(("y", "т", "j", "o", "s", "t"))
            console.print(t("ok") if journal.resolve(fid, yes) else t("not_found"))
        elif choice == "5":
            console.print("  ".join(f"{k}={v}" for k, v in LANG_NAMES.items()))
            lang = console.input("> ").strip().lower()
            if lang in LANGS:
                config.save_lang(lang)
                t = Translator(lang)
        elif choice in ("0", "q", ""):
            return


def main() -> None:
    config.ensure_dirs()
    logging.basicConfig(filename=config.LOG_DIR / "reilly.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        encoding="utf-8")
    ap = argparse.ArgumentParser(description="OSINT-REILLY v5")
    ap.add_argument("--lang", choices=LANGS, help="interface / report language")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="analyse one topic")
    r.add_argument("topic")
    r.add_argument("--assets", default="", help="e.g. BTC,GC=F,^GDAXI,AAPL")
    r.add_argument("--countries", default="", help="ISO2 codes, e.g. DE,PL")
    r.add_argument("--urls", default="", help="public pages to monitor for changes")
    r.add_argument("--langs", default="", help="search languages, e.g. en,de,uk")
    r.add_argument("--hypothesis", default="")
    r.add_argument("--polarity", choices=["risk", "positive"], default="risk")
    r.add_argument("--asset-direction", choices=["auto", "up", "down"], default="auto",
                   help="asset move that supports the hypothesis (gas spike = risk + up)")
    r.add_argument("--prior", type=float, default=0.5)
    r.add_argument("--horizon", type=int, default=30, help="days")
    r.add_argument("--no-llm", action="store_true")
    r.add_argument("--no-journal", action="store_true", help="do not record forecasts")
    tk_ = sub.add_parser("task", help="agent: picks sources, searches, analyses a task")
    tk_.add_argument("text")
    tk_.add_argument("--horizon", type=int, default=30)
    tk_.add_argument("--no-llm", action="store_true")
    tk_.add_argument("--no-journal", action="store_true")
    pr = sub.add_parser("profile", help="run standing profiles from profiles.json")
    pr.add_argument("ids", nargs="*", help="profile ids (empty = all): " +
                    ", ".join(profiles.profile_ids()))
    pr.add_argument("--horizon", type=int, default=30)
    pr.add_argument("--no-llm", action="store_true")
    pr.add_argument("--no-journal", action="store_true")
    tp = sub.add_parser("topics", help="run every topic from a JSON file")
    tp.add_argument("file")
    tp.add_argument("--no-llm", action="store_true")
    sub.add_parser("console", help="interactive console menu")
    sub.add_parser("journal", help="forecast journal and calibration")
    rs = sub.add_parser("resolve", help="resolve a hypothesis forecast")
    rs.add_argument("id")
    rs.add_argument("outcome", choices=["yes", "no"])
    args = ap.parse_args()

    t = Translator(args.lang or config.saved_lang())
    if args.cmd == "run":
        run_one({"topic": args.topic, "assets": split(args.assets) or None,
                 "countries": split(args.countries) or None, "urls": split(args.urls),
                 "langs": split(args.langs) or None, "hypothesis": args.hypothesis,
                 "polarity": args.polarity, "asset_direction": args.asset_direction,
                 "prior": args.prior, "horizon": args.horizon},
                t, use_llm=not args.no_llm, record=not args.no_journal)
    elif args.cmd == "task":
        with console.status(t("collecting")) as status:
            result = agent.run_task(args.text, t.lang, args.horizon, not args.no_llm,
                                    record=not args.no_journal,
                                    progress=lambda m: status.update(f"{t('collecting')}: {m}"))
        show(result, t)
        paths = report.save(result, t)
        console.print(f"[green]{t('saved')}:[/green] " + "  ".join(
            str(p.relative_to(config.ROOT)) for p in paths.values()))
    elif args.cmd == "profile":
        for pid in args.ids or profiles.profile_ids():
            run_profile(pid, t, use_llm=not args.no_llm, record=not args.no_journal,
                        horizon=args.horizon)
    elif args.cmd == "topics":
        run_topics(args.file, t, not args.no_llm)
    elif args.cmd == "journal":
        show_journal(t)
    elif args.cmd == "resolve":
        console.print(t("ok") if journal.resolve(args.id, args.outcome == "yes") else t("not_found"))
    elif args.cmd == "console":
        interactive(t)
    else:
        try:
            from reilly import gui
        except ImportError as exc:  # Python built without tkinter
            console.print(f"[yellow]tkinter: {exc}[/yellow]")
            interactive(t)
        else:
            gui.main()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        sys.exit(130)
