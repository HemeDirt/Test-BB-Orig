#!/usr/bin/env python3
"""reorganize.py — ШАГ В+Д: батч-переносы по целевой структуре, delete/archive, извлечение архивов.

Правила взяты из Сообщения 1 и Дополнения 2 автора. Каждый перенос пишется в data/move_log.csv
(from,to,reason); удаление дубликатов/пустых — reason=delete:*; пропуск архивной записи,
совпадающей по md5 с файлом репозитория, — duplicate_skipped (from=archive::путь).
Запуск: python3 tools/reorganize.py [--dry]
"""
import csv, gzip, hashlib, io, json, os, re, shutil, sys, tarfile, zipfile
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DRY = "--dry" in sys.argv
MOVE_LOG = os.path.join(ROOT, "data", "move_log.csv")
DUP_SUFFIX = re.compile(r"\s*\((\d+)\)(?=\.[^.]*$)")
ARCHIVE_EXTRACT_CLASSES = {"code", "deck_data", "sim_results", "docs_rules", "docs_reports", "logs"}
KEEP_ROOT = {"QWEN.md", "SPEC.md", "DECISIONS.md", "STATE.md", "README.md", "CORE_THINK.md", ".gitignore"}

def md5b(b): return hashlib.md5(b).hexdigest()

def load_rules():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from inventory import classify, walk, dup_groups
    rows = walk(ROOT)
    groups = dup_groups(rows)
    classes = classify(rows, groups)
    return rows, groups, classes

def target_for(path, cls, reason):
    """Возвращает (target_dir_rel, kind) где kind in move/delete/archive/inbox/keep."""
    name = os.path.basename(path)
    stem = os.path.splitext(name)[0]
    if path in KEEP_ROOT or path.startswith(("data/", "tools/", "game/", "dist/", "docs/", "_archive/", "_inbox/")):
        return None, "keep"
    if cls == "duplicates":
        return None, "delete"
    if size_zero(path):
        return None, "delete"
    # канонические переименования
    if name == "QWEN_MD_ПРАВИЛА_ПРОЕКТА.md": return ".", "rename:QWEN.md"
    if name == "ЗАДАНИЕ_НА_СИМУЛЯЦИЮ_ББ.md": return ".", "rename:SPEC.md"
    # черновики и прочие редакции правил — в docs/notes (по слову автора)
    if re.search(r"(ПРАВИЛА|КАНОН)", name) and ("v2" in name or "ред" in name.lower() or "4.0" in name):
        return "docs/notes/", "move"
    if name.startswith("ЖУРНАЛ_ЧИСТКИ"): return "docs/notes/", "move"
    if name in ("КОНТЕКСТ_БРИФ.md", "СТАРТ_ЧАТА_С_CODER.md", "БЛИЦ_БОЙ_ПОЛНЫЙ_ОТЧЁТ_ЗА_ВЕСЬ_ЧАТ.docx"):
        return "docs/notes/", "move"
    if name.endswith(".png") or name.endswith(".jpg"): return "_archive/images/", "move"
    if name.endswith(".yml"): return "_archive/web_junk/", "move"
    if name.endswith(".sh"): return "tools_old/", "move"
    # карлайнф посторонний
    if "cardlife" in name.lower(): return "_inbox/", "move"
    if name == "spec_raw.txt": return "data/deck/", "move"
    # колоды категорий
    if re.match(r"^\d{1,2}_.*\.(txt|md|json)$", name): return "data/deck/", "move"
    if name.endswith("_raw.txt") or name in ("decks.json", "final_v5.json"): return "data/deck/", "move"
    if name.endswith(".xlsx") and "карт" in name: return "data/deck/", "move"
    if name in ("карты_v5_по_категориям.md", "карты_настолка_полный_набор.md", "КОЛОДА_ОБМЕНА.md"): return "data/deck/", "move"
    # правила канона печати v3 без суффикса
    if name in ("ПРАВИЛА_БЛИЦ_БОЙ_v3.md", "ПРАВИЛА_БЛИЦ_БОЙ_v3.docx", "rules_print_v3.txt"): return "docs/rules/", "move"
    if cls == "docs_rules": return "docs/rules/", "move"
    if cls == "docs_reports": return "docs/reports/", "move"
    if cls == "logs": return "docs/reports/", "move"
    if name.endswith("_digest.md"): return "docs/reports/", "move"
    if cls == "sim_results": return "game/results/", "move"
    if cls == "code":
        if name.startswith("patch_") or name in ("near.py","t2.py","check.py","check_clean.py","censor.py","censor_fix.py","extract.py","integrity_audit.py","make_fingerprints.py","md2docx.py","md2docx_min.py","build_v5.py","build_canon_decks.py","csv_export.py","coverage_test.py","audit_full.py","verify_any.py","one_search.py","batch_stats.py"):
            return "tools_old/", "move"
        return "game/", "move"
    if cls == "web_junk": return "_archive/web_junk/", "move"
    if cls == "zip_archives": return "_archive/", "move"
    return "_inbox/", "move"

def size_zero(path):
    try: return os.path.getsize(os.path.join(ROOT, path)) == 0
    except OSError: return False

DELETED_LIST = os.path.join(ROOT, "data", "deleted_list.txt")

def log_move(frm, to, reason):
    if DRY:
        print(f"[dry] {frm} -> {to} ({reason})"); return
    new = not os.path.exists(MOVE_LOG)
    with open(MOVE_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["from", "to", "reason", "ts"])
        w.writerow([frm, to, reason, datetime.now().isoformat(timespec="seconds")])

def log_deleted(rel, reason):
    if DRY: return
    with open(DELETED_LIST, "a", encoding="utf-8") as f:
        f.write(f"{rel}\t{reason}\n")

def ensure_dirs():
    for d in ["game", "game/results", "game/legacy", "dist", "data/deck", "data/live",
              "docs/rules", "docs/reports", "docs/notes", "tools", "_archive", "_archive/web_junk", "_inbox"]:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

def move_file(rel, target_dir, reason):
    src = os.path.join(ROOT, rel)
    name = os.path.basename(rel)
    dst = os.path.join(ROOT, target_dir, name)
    if os.path.exists(dst):
        target_dir = "_inbox/"
        dst = os.path.join(ROOT, target_dir, name)
        reason += " | collision->inbox"
    if DRY:
        print(f"[dry] mv {rel} -> {target_dir}{name} ({reason})"); return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    log_move(rel, target_dir + name, reason)

def main():
    rows, groups, classes = load_rules()
    ensure_dirs()
    stats = {"moved": 0, "deleted": 0, "archived_dir": 0, "kept": 0, "skipped_gone": 0}
    # A1: перед каждой операцией проверяем существование пути — устаревший список
    # не приводит к падению; после переноса папки её содержимое пропускается.
    def exists(rel): return os.path.exists(os.path.join(ROOT, rel))
    protected = {"game", "data", "docs", "tools", "dist", "_archive", "_inbox", "results"}
    # 1) папки верхнего уровня -> _archive целиком (кроме служебных новых)
    topdirs = sorted({r["path"].split("/",1)[0] for r in rows if "/" in r["path"]}
                     | {d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)) and not d.startswith(".")})
    for d in topdirs:
        if d in protected or not exists(d): continue
        if not os.path.isdir(os.path.join(ROOT, d)): continue
        move_file(d, "_archive/", "archive:whole-dir")
        stats["archived_dir"] += 1
    # 2) файлы по классам (только те, что лежат в корне на момент обработки)
    for r in sorted(rows, key=lambda x: x["path"]):
        rel = r["path"]
        if "/" in rel:
            continue  # содержимое внешних папок уехало вместе с папкой на шаге 1
        if not exists(rel):
            stats["skipped_gone"] += 1; continue
        cls = classes[rel]["class"]
        tgt = target_for(rel, cls, classes[rel]["reason"])
        if tgt[1] == "keep": stats["kept"] += 1; continue
        if tgt[1] == "delete":
            why = "empty" if size_zero(rel) else "duplicate-suffix"
            if DRY: print(f"[dry] rm {rel}")
            else:
                os.remove(os.path.join(ROOT, rel)); log_move(rel, "", "delete:" + why); log_deleted(rel, "delete:" + why)
            stats["deleted"] += 1; continue

        if tgt[1].startswith("rename:"):
            newname = tgt[1].split(":", 1)[1]
            dstrel = newname
            if DRY: print(f"[dry] git mv {rel} -> {dstrel}")
            else:
                shutil.move(os.path.join(ROOT, rel), os.path.join(ROOT, dstrel))
                log_move(rel, dstrel, "canonical rename per author")
            stats["moved"] += 1; continue
        move_file(rel, tgt[0], "class:" + cls)
        stats["moved"] += 1
    print(json.dumps(stats, ensure_ascii=False))
    # примечание: извлечение из архивов (доп. 2.3–2.6) делает tools/archive_extract.py


if __name__ == "__main__":
    main()
