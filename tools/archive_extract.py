#!/usr/bin/env python3
"""archive_extract.py — дополнение 2.3–2.6: извлечение полезного из архивов.

Классы для извлечения: code, deck_data, sim_results, docs_rules, docs_reports, logs.
Сим-код (sim/, bb_core, bb_full, game_sim, sim_n, sim8, sweep*, time_model, verify_dop,
build_pool*, pool_*) -> game/legacy/<имя_архива>/; прочий код -> game/legacy/tools/.
Запись, чей md5 совпадает с файлом репозитория или уже извлечённой записью, не
извлекается: duplicate_skipped в move_log (from = archive::путь).
Архивы НЕ удаляются; rar без unrar пропускаются (unrar_unavailable в манифесте).
Запуск: python3 tools/archive_extract.py [--dry]
"""
import csv, hashlib, json, os, re, sys, tarfile, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOVE_LOG = os.path.join(ROOT, "data", "move_log.csv")
EXTRACT_CLASSES = {"code", "deck_data", "sim_results", "docs_rules", "docs_reports", "logs"}
SIM_CODE = re.compile(r"(^|/)sim/|bb_core|bb_full|game_sim|sim_n\.py|sim8|sweep|time_model|verify_dop|build_pool|pool_|make_dop|make_sim8|blitz\.py|matrix_b8|batch_stats|integrity_audit|make_fingerprints")

sys.path.insert(0, os.path.join(ROOT, "tools"))
from inventory import classify, walk, dup_groups

def md5b(b): return hashlib.md5(b).hexdigest()

def log_move(frm, to, reason, dry):
    if dry:
        print(f"[dry] {frm} -> {to or ''} ({reason})"); return
    new = not os.path.exists(MOVE_LOG)
    with open(MOVE_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["from", "to", "reason"])
        w.writerow([frm, to, reason])

def iter_records(full):
    low = full.lower()
    if low.endswith(".zip"):
        with zipfile.ZipFile(full) as zf:
            for i in zf.infolist():
                if i.is_dir(): continue
                try: data = zf.read(i)
                except Exception: continue
                yield i.filename, data
    elif low.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(full) as tf:
            for m in tf.getmembers():
                if not m.isfile(): continue
                f = tf.extractfile(m)
                if f is None: continue
                yield m.name, f.read()

def main():
    dry = "--dry" in sys.argv
    rows = walk(ROOT)
    groups = dup_groups(rows)
    repo_md5 = {r["md5"] for r in rows if not r["md5"].startswith("ERR")}
    archives = []
    for cand in (os.path.join(ROOT, ap) for ap in [r["path"] for r in rows]):
        pass
    # B1-fix: ищем архивы где угодно в дереве (после реорганизации они лежат в _archive/),
    # пропуская служебные папки .git и содержимое уже извлечённое.
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            if fn.lower().endswith((".zip", ".tar", ".tar.gz", ".tgz")):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                archives.append(rel)
    archives.sort()
    seen = set(repo_md5)
    legacy_found, n_ex, n_dup, n_skip_class = [], 0, 0, 0
    for ap in archives:
        if "Crome" in ap:      # браузерные бинарники — веб-мусор, не извлекаем (доп. 2.3)
            continue
        full = os.path.join(ROOT, ap)
        arcname = os.path.splitext(os.path.basename(ap))[0]
        for name, data in iter_records(full):
            base = os.path.basename(name.replace("\\", "/"))
            h = md5b(data)
            rec_from = f"archive::{ap}::{name}"
            cls_row = classify([{"path": base, "bytes": len(data), "ext": os.path.splitext(base)[1].lower(),
                                 "mtime_epoch": 0, "mtime": "", "md5": h}], [])
            cls = cls_row[base]["class"]
            if h in seen:
                log_move(rec_from, "", "duplicate_skipped", dry); n_dup += 1; continue
            if cls not in EXTRACT_CLASSES:
                n_skip_class += 1; continue
            if SIM_CODE.search(name) or SIM_CODE.search(base):
                tgt = f"game/legacy/{arcname}/"; legacy_found.append(rec_from)
            elif cls == "code":
                tgt = "game/legacy/tools/"
            elif cls == "deck_data":
                tgt = "data/deck/"
            elif cls == "sim_results":
                tgt = "game/results/from_archive/"
            elif cls == "docs_rules":
                tgt = "docs/rules/from_archive/"
            elif cls == "docs_reports":
                tgt = "docs/reports/from_archive/"
            else:
                tgt = "docs/reports/logs/"
            dst = os.path.join(ROOT, tgt, base)
            if os.path.exists(dst):
                log_move(rec_from, "", "duplicate_skipped:name-collision", dry); n_dup += 1; continue
            if not dry:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f: f.write(data)
            log_move(rec_from, tgt + base, "extract-from-archive class:" + cls, dry)
            seen.add(h); n_ex += 1
    if not dry:
        with open(os.path.join(ROOT, "data", "legacy_found.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(legacy_found))
    print(json.dumps({"archives_scanned": len(archives), "extracted": n_ex,
                      "duplicate_skipped": n_dup, "not_extractable_class": n_skip_class,
                      "legacy_code_files": len(legacy_found)}, ensure_ascii=False))
    for l in legacy_found: print("LEGACY:", l)

if __name__ == "__main__":
    main()
