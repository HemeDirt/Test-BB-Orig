#!/usr/bin/env python3
"""inventory.py — инвентаризация репозитория БЛИЦ БОЙ (ШАГ А).

Обход всего дерева (кроме .git и служебных кэшей браузера), для каждого файла:
path, bytes, ext, mtime, md5 -> data/manifest.json + data/manifest.csv.
Затем: группы дубликатов (одинаковый md5) -> data/duplicates.json.
Затем классификация по правилам (расширение + шаблон имени + размер) на классы:
code, deck_data, sim_results, docs_rules, docs_reports, logs, web_junk,
zip_archives, duplicates, unknown -> data/classes.json (+ сводка в stdout).

Запуск: python3 tools/inventory.py [ROOT]   (ROOT по умолчанию — корень репозитория)
Класс "duplicates" помечает НЕ оригиналы: оставляем экземпляр без суффикса и
с наибольшим mtime (правило ШАГА Б), остальные помечены drop=True.
ВНИМАНИЕ: скрипт только читает и пишет в data/, перемещения не выполняет.
"""
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

SKIP_DIRS = {".git", "__pycache__", "@asamuzakjp", "@bramus", "@csstools"}
CLASSES = ["code", "deck_data", "sim_results", "docs_rules", "docs_reports",
           "logs", "web_junk", "zip_archives", "duplicates", "unknown"]

# колоды: 1_professiya ... 11_obmen и подобные числовые префиксы категорий
DECK_NUM = re.compile(r"^\d{1,2}_[a-zа-я_0-9-]+\.(txt|md|json)$", re.I)
DUP_SUFFIX = re.compile(r"\s*\((\d+)\)(?=\.[^.]*$)")
CODE_PY = re.compile(r"\.py$")
SIM_NAME = re.compile(r"(sweep|pool_sim|pool_indices|final_v5|dice|event_freq|harvest|"
                      r"verify_dop|report_numbers|fingerprint|results|tornado|pendulum|"
                      r"winrate|reserve|reputation|tilt|witness_seeds|plane\d+|b\d+_)", re.I)
REPORT_MD = re.compile(r"^(REPORT_|VIEW_|VERDICT_|WINRATE|TILT|PENDULUM|TORNADO|RESERVE|VIEWER)", re.I)
RULES_MD = re.compile(r"(ПРАВИЛА|ПРОТОКОЛ|СИМУЛЯЦИИ|ДОПОЛНЕНИЕ|ЖУРНАЛ|КОЛОДА|СПРАВОЧНИК|ПРИМЕР_ИГРЫ|"
                      r"КАНОН|ПАМЯТКА|КОРОТКИЕ|rules|situations|spec|задание|старт_чата|контекст)", re.I)
WEB_EXT = {".html", ".htm", ".js", ".css", ".map"}
ARCHIVE_EXT = {".zip", ".rar", ".gz", ".tar", ".7z", ".tgz"}


def md5sum(path, limit=None):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            if limit is not None:
                h.update(f.read(limit))
            else:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
    except OSError as e:
        return "ERR:" + e.__class__.__name__
    return h.hexdigest()


def walk(root):
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            try:
                st = os.stat(p)
            except OSError:
                continue
            ext = os.path.splitext(fn)[1].lower()
            rows.append({
                "path": rel.replace(os.sep, "/"),
                "bytes": st.st_size,
                "ext": ext,
                "mtime_epoch": st.st_mtime,
                "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "md5": md5sum(p),
            })
    return rows


def dup_groups(rows):
    by_md5 = {}
    for r in rows:
        if r["md5"].startswith("ERR:"):
            continue
        by_md5.setdefault(r["md5"], []).append(r)
    groups = []
    for md5, items in sorted(by_md5.items()):
        if len(items) < 2:
            continue
        # оригинал: без суффикса "(n)" и наибольший mtime
        def key(r):
            base = DUP_SUFFIX.sub("", os.path.basename(r["path"]))
            has_suf = 1 if DUP_SUFFIX.search(os.path.basename(r["path"])) else 0
            return (has_suf, base != os.path.basename(r["path"]), -r["mtime_epoch"], r["path"])
        items_sorted = sorted(items, key=key)
        keep = items_sorted[0]["path"]
        groups.append({"md5": md5, "bytes": items[0]["bytes"], "keep": keep,
                       "drop": [i["path"] for i in items_sorted[1:]]})
    return groups


def classify(rows, groups):
    dropset = set()
    for g in groups:
        dropset.update(g["drop"])
    out = {}
    for r in rows:
        p, ext, size = r["path"], r["ext"], r["bytes"]
        name = os.path.basename(p)
        top = "/" not in p
        cls, why = None, None
        if p in dropset:
            cls, why = "duplicates", "md5-dup, drop per keep-rule"
        elif ext in ARCHIVE_EXT or (ext == ".gz" and name.endswith(".tar.gz")):
            cls, why = "zip_archives", f"ext {ext}"
        elif CODE_PY.search(ext):
            cls, why = "code", "python source"
        elif ext in WEB_EXT:
            cls, why = "web_junk", f"ext {ext}"
        elif name in ("package.json", "package-lock.json", ".nojekyll"):
            cls, why = "web_junk", "web artifact by name"
        elif DECK_NUM.match(name) and top:
            cls, why = "deck_data", "numbered deck category file"
        elif ext == ".json" and SIM_NAME.search(name):
            cls, why = "sim_results", "sim json by name pattern"
        elif ext == ".json" and size >= 200000:
            cls, why = "unknown", "big json, needs inspection"
        elif ext in (".log", ".txt") and (name.startswith("log_") or "sample_log" in name):
            cls, why = "logs", "log by name"
        elif ext == ".txt" and size < 4000:
            cls, why = "unknown", "small txt, needs reading"
        elif ext in (".md", ".docx") and RULES_MD.search(name):
            cls, why = "docs_rules", "rules-ish name"
        elif ext in (".md", ".docx") and REPORT_MD.search(name):
            cls, why = "docs_reports", "report-ish name"
        elif ext == ".xlsx":
            cls, why = "deck_data", "spreadsheet deck"
        elif ext == ".pdf":
            cls, why = "unknown", "pdf needs manual view"
        else:
            cls, why = "unknown", f"no rule matched (ext {ext or '-'})"
        out[p] = {"class": cls, "reason": why, "bytes": size, "ext": ext}
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    root = os.path.abspath(root)
    rows = walk(root)
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    with open(os.path.join(root, "data", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    with open(os.path.join(root, "data", "manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "ext", "mtime", "mtime_epoch", "md5"])
        w.writeheader()
        w.writerows(rows)
    groups = dup_groups(rows)
    with open(os.path.join(root, "data", "duplicates.json"), "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=1)
    classes = classify(rows, groups)
    with open(os.path.join(root, "data", "classes.json"), "w", encoding="utf-8") as f:
        json.dump(classes, f, ensure_ascii=False, indent=1)
    summary = {c: 0 for c in CLASSES}
    for v in classes.values():
        summary[v["class"]] += 1
    print(f"root={root}")
    print(f"files_total={len(rows)}  dup_groups={len(groups)}  dup_drop={sum(len(g['drop']) for g in groups)}")
    for c in CLASSES:
        print(f"{c:14s} {summary[c]}")
    print("\n== UNKNOWN (%d) ==" % summary["unknown"])
    for p, v in sorted(classes.items()):
        if v["class"] == "unknown":
            print(f"{p}\t{v['bytes']}\t{v['reason']}")
    print("\n== DUPLICATES drop-list (%d) ==" % summary["duplicates"])
    for g in groups:
        for d in g["drop"]:
            print(f"{d}\t<- keep {g['keep']}\t{g['bytes']}B")


if __name__ == "__main__":
    main()
