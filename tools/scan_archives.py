#!/usr/bin/env python3
"""scan_archives.py — просмотр содержимого архивов без распаковки в корень (дополнение 2.1-2.2).

Для каждого файла-архива (.zip/.rar/.tar/.tar.gz/.tgz/.gz) строит список записей:
имя, размер, md5 (где возможно прочитать), классификация той же сетью правил,
что и для файлов репозитория; отметка dup_of_repo если md5 совпадает с файлом в data/manifest.json.
Вывод: data/manifest_archives.json. rar без unrar -> status="unrar_unavailable" (не ошибка).
Запуск: python3 tools/scan_archives.py [ROOT]
"""
import gzip, hashlib, io, json, os, re, subprocess, sys, tarfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inventory import classify, walk, dup_groups, ARCHIVE_EXT  # те же правила классов

def md5b(b): return hashlib.md5(b).hexdigest()

def list_zip(p):
    out = []
    with zipfile.ZipFile(p) as zf:
        for i in zf.infolist():
            if i.is_dir(): continue
            try:
                data = zf.read(i)
                h = md5b(data)
            except Exception:
                h = "unreadable"
            out.append({"name": i.filename, "bytes": i.file_size, "md5": h})
    return out

def list_tar(p):
    out = []
    with tarfile.open(p) as tf:
        for m in tf.getmembers():
            if not m.isfile(): continue
            f = tf.extractfile(m)
            data = f.read() if f else b""
            out.append({"name": m.name, "bytes": m.size, "md5": md5b(data)})
    return out

def list_gz_single(p):
    with gzip.open(p, "rb") as f:
        data = f.read()
    inner = os.path.basename(p)[:-3]
    return [{"name": inner, "bytes": len(data), "md5": md5b(data)}]

def probe_rar(p):
    for tool in ("unrar", "bsdtar", "7z"):
        if subprocess.call(["which", tool], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            return tool
    return None

def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    rows = walk(root)
    repo_md5 = {r["md5"] for r in rows}
    groups = dup_groups(rows)
    result = []
    for r in rows:
        p = os.path.join(root, r["path"])
        ext = r["ext"]
        if ext not in ARCHIVE_EXT and not r["path"].endswith(".tar.gz"):
            continue
        entry = {"archive": r["path"], "bytes": r["bytes"], "status": "ok", "records": []}
        try:
            low = r["path"].lower()
            if low.endswith(".zip"):
                recs = list_zip(p)
            elif low.endswith((".tar.gz", ".tgz", ".tar")):
                recs = list_tar(p)
            elif low.endswith(".gz"):
                recs = list_gz_single(p)
            elif low.endswith(".rar"):
                tool = probe_rar(p)
                if tool is None:
                    entry["status"] = "unrar_unavailable"
                    recs = []
                elif tool == "bsdtar":
                    recs = list_tar(p)  # bsdtar читает rar через tarfile? нет: пробуем как есть
                else:
                    recs = []
                    entry["status"] = f"tool_present_not_wired:{tool}"
            elif low.endswith(".7z"):
                recs = []
                entry["status"] = "sevenzip_unsupported"
            else:
                recs = []
                entry["status"] = "unknown_format"
        except Exception as e:
            entry["status"] = f"error:{type(e).__name__}:{e}"
            recs = []
        classes = classify([{"path": q["name"], "ext": os.path.splitext(q["name"])[1].lower(),
                             "bytes": q["bytes"], "mtime_epoch": 0, "mtime": "", "md5": q["md5"]}
                            for q in recs], groups)
        for q in recs:
            c = classes.get(q["name"], {"class": "unknown", "reason": "n/a"})
            q["class"] = c["class"]
            q["dup_of_repo"] = q["md5"] in repo_md5
        entry["records"] = recs
        result.append(entry)
    out = os.path.join(root, "data", "manifest_archives.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"wrote {out}")
    for e in result:
        n = len(e["records"]); nd = sum(1 for q in e["records"] if q["dup_of_repo"])
        kinds = {}
        for q in e["records"]:
            kinds[q["class"]] = kinds.get(q["class"], 0) + 1
        print(f"{e['archive']}: status={e['status']} records={n} dup_of_repo={nd} classes={kinds}")

if __name__ == "__main__":
    main()
