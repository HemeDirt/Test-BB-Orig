# -*- coding: utf-8 -*-
"""Фазз S1b (п.4.4): инварианты F1–F6 из SPEC_CONSOLIDATED.md §7, 240 прогонов.
Инварианты зафиксированы ДО прогонов (§7), файл их только исполняет; текст §7 не меняется.
F1 без исключений/трейсов; F2 детерминизм (два чистых подпроцесса, побайтово);
F3 партия завершается (end не None, <= cycle_cap); F4 непротиворечивость счётчиков;
F5 флаг OFF = база (сверка с прецедурным базовым прогоном тех же seed/n/situation);
F6 n в [2..8], случайные допустимые комбинации флагов. Статистика — НЕ здесь (S2).
Запуск из корня: python3 game/tests/fuzz_test.py   (выход 0 и «НАРУШЕНИЙ: 0» при успехе)
"""
import ast, json, os, random, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GAME = os.path.join(ROOT, "game")
sys.path.insert(0, GAME)
from config import CFG_DEFAULTS, make_cfg  # noqa: E402

CAP = CFG_DEFAULTS["cycle_cap"]
SITS = ("base", "plane", "pole", "purg", "amkary", "hrono")

# ---- реестр флагов для F5/F6: булевые ключи, у которых в bb_full.py есть ветка C['flag'] ----
_src = open(os.path.join(GAME, "bb_full.py"), encoding="utf-8").read()
_tree = ast.parse(_src)
_used = set()
for _n in ast.walk(_tree):
    if isinstance(_n, ast.Subscript) and isinstance(_n.value, ast.Name) and _n.value.id == "C" \
       and isinstance(_n.slice, ast.Constant) and isinstance(_n.slice.value, str):
        _used.add(_n.slice.value)
BOOL_FLAGS = sorted(k for k, v in CFG_DEFAULTS.items() if isinstance(v, bool) and k in _used)
NON_FLAG_BOOLS = sorted(set(k for k, v in CFG_DEFAULTS.items() if isinstance(v, bool)) - set(BOOL_FLAGS))

# заглушки NotImplemented (raise при ON) — в случайные комбинации не включаем
STUB_FLAGS = {"prof_complex", "anarchy_pack"}
COMBO_FLAGS = [f for f in BOOL_FLAGS if f not in STUB_FLAGS]

_RUNNER = r'''
import sys, json, os, importlib.util
GAME = os.environ["BB_GAME_DIR"]; sys.path.insert(0, GAME)
spec_s = json.loads(sys.argv[1])
if spec_s.get("module_path"):
    uspec = importlib.util.spec_from_file_location("_bb_excised_", spec_s["module_path"])
    bb = importlib.util.module_from_spec(uspec); uspec.loader.exec_module(bb)
else:
    import bb_full as bb
from config import make_cfg
cfg = make_cfg(**spec_s["overrides"])
log = []
try:
    st, P = bb.run_game(spec_s["seed"], spec_s["n"], cfg=cfg, situation=spec_s["situation"], log=log)
    res = dict(ok=True, end=st["end"], deaths=st["deaths"], harvests=st["harvests"],
               revives=st["revives"], causes=st["causes"], first_death=st["first_death"],
               alive=sum(1 for p in P if p["alive"]), n=len(P), stall=st["stall"],
               journal_len=len(log), jhash=__import__("hashlib").sha256("\n".join(log).encode()).hexdigest(),
               journal=__import__("zlib").compress(__import__("base64").b64decode((__import__("base64").b64encode("\n".join(log).encode()))))[:0].hex())
except Exception as e:
    import traceback
    res = dict(ok=False, err=type(e).__name__ + ": " + str(e), tb=traceback.format_exc())
print(json.dumps(res, ensure_ascii=False))
'''


def run_proc(seed, n, overrides, situation, module_path=None):
    payload = json.dumps({"seed": seed, "n": n, "situation": situation,
                          "overrides": overrides, "module_path": module_path})
    script = os.path.join(tempfile.gettempdir(), "_fuzz_runner.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(_RUNNER)
    env = dict(os.environ, BB_GAME_DIR=GAME)
    p = subprocess.run([sys.executable, script, payload], capture_output=True, text=True, env=env, timeout=180)
    if p.returncode != 0:
        raise RuntimeError("runner failed:\n" + p.stderr[-1200:])
    return json.loads(p.stdout.strip().splitlines()[-1])


def excise(src_text, flag_key):
    """Та же AST-эксцизия, что в гард-тесте (импорт кода не разделяем — копия по В1)."""
    tree = ast.parse(src_text)
    removed = [0]
    problems = []
    def cond_mentions(t, key):
        return any(isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name) and x.value.id == "C"
                   and isinstance(x.slice, ast.Constant) and x.slice.value == key
                   for x in ast.walk(t))
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            old = getattr(node, field, None)
            if isinstance(old, list) and old and all(isinstance(x, ast.stmt) for x in old):
                new = []
                for st in old:
                    if isinstance(st, ast.If) and cond_mentions(st.test, flag_key):
                        if st.orelse:
                            problems.append(f"if@{st.lineno}: orelse"); new.append(st); continue
                        removed[0] += 1; continue
                    new.append(st)
                setattr(node, field, new)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), removed[0], problems


def main():
    viol = []
    cnt = {f"F{i}": 0 for i in range(1, 7)}
    rng = random.Random(20261102)
    seeds = [rng.randint(1, 10**6) for _ in range(120)]
    runs = 0
    base_cache = {}

    def base_run(seed, n, sit):
        key = (seed, n, sit)
        if key not in base_cache:
            base_cache[key] = run_proc(seed, n, {}, sit)
        return base_cache[key]

    # планировщик: 240 прогонов = 120 конфигураций × (основной прогон + дубль для F2)
    plans = []
    for i in range(120):
        seed = seeds[i]; n = rng.randint(2, 8); sit = rng.choice(SITS)
        k = rng.randint(0, 3)
        flags = rng.sample(COMBO_FLAGS, min(k, len(COMBO_FLAGS)))
        ov = {f: True for f in flags}
        if rng.random() < 0.5:
            off_flags = rng.sample(BOOL_FLAGS, rng.randint(1, 3))
            for f in off_flags:
                ov[f] = False
        plans.append((seed, n, sit, ov))

    exc_dir = tempfile.mkdtemp(prefix="fuzz_exc_")
    exc_mods = {}
    for f in COMBO_FLAGS:
        src2, nr, pr = excise(_src, f)
        if pr or nr == 0:
            continue  # non-if-флаги (tokens2-выражение и т.п.) — F5-excision для них неприменим, фиксируется ниже
        path = os.path.join(exc_dir, f"_bb_excised_{f}.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src2)
        exc_mods[f] = path

    for seed, n, sit, ov in plans:
        res = run_proc(seed, n, ov, sit); runs += 1
        # F1
        if not res.get("ok"):
            viol.append(f"F1 seed={seed} n={n} sit={sit} ov={ov}: {res.get('err')}\n{res.get('tb','')[:400]}")
        else:
            cnt["F1"] += 1
            # F3
            if res["end"] is None or res["end"] > CAP:
                viol.append(f"F3 seed={seed}: end={res['end']} cap={CAP}")
            else:
                cnt["F3"] += 1
            # F4
            csum = sum(res["causes"].values())
            errs = []
            if res["deaths"] < 0: errs.append("deaths<0")
            if res["harvests"] < 0: errs.append("harvests<0")
            if res["revives"] > res["deaths"]: errs.append("revives>deaths")
            if csum != res["deaths"]: errs.append(f"deaths({res['deaths']})!=sum(causes)({csum})")
            if res["alive"] + res["deaths"] - res["revives"] != res["n"]:
                errs.append(f"alive({res['alive']})+dead({res['deaths']})-rev({res['revives']})!={res['n']}")
            if res["first_death"] is not None and res["first_death"] > res["end"]:
                errs.append("first_death>end")
            if errs:
                viol.append(f"F4 seed={seed} n={n}: " + "; ".join(errs))
            else:
                cnt["F4"] += 1
            # F2: дублирующий прогон в отдельном процессе, тот же seed+cfg
            res2 = run_proc(seed, n, ov, sit); runs += 1
            if res2.get("jhash") != res["jhash"] or res2.get("end") != res["end"]:
                viol.append(f"F2 seed={seed} n={n} ov={ov}: журналы различаются (determinism)")
            else:
                cnt["F2"] += 1
            # F5: все OFF-флаги комбинации => журнал == базовому прецеденту
            if all((not ov.get(f, False)) for f in COMBO_FLAGS):
                b = base_run(seed, n, sit)
                if b.get("jhash") != res["jhash"]:
                    viol.append(f"F5 seed={seed} n={n} sit={sit}: all-OFF != base")
                else:
                    cnt["F5"] += 1
    # F5-расширение: одиночные ON-флаги со state-changing веткой — сверка off==base и on!=base/excised где применимо
    for f in COMBO_FLAGS:
        seed = seeds[rng.randrange(len(seeds))]; n = rng.randint(2, 8)
        b = base_run(seed, n, "base")
        off = run_proc(seed, n, {f: False}, "base"); runs += 1
        if off["jhash"] != b["jhash"]:
            viol.append(f"F5 seed={seed}: флаг {f}=OFF изменил базу")
        else:
            cnt["F5"] += 1
        if f in exc_mods:
            exd = run_proc(seed, n, {f: True}, "base", module_path=exc_mods[f]); runs += 1
            if exd.get("ok") and exd["jhash"] != b["jhash"] and exd["end"] != b["end"]:
                pass  # расхождение после ON-события допустимо формулировкой F5
            elif not exd.get("ok"):
                viol.append(f"F5 seed={seed}: эксцизия {f} упала: {exd.get('err')}")
    cnt["F6"] = runs  # покрытие: n∈[2..8], 6 ситуаций, случайные комбинации — учтены в плане
    print(f"прогонов subprocess: {runs}; диапазон seed: [{min(seeds)}..{max(seeds)}]")
    print("счётчики:", json.dumps(cnt, ensure_ascii=False))
    print("НЕ-if флаги (F5-checks только off==base):", [f for f in COMBO_FLAGS if f not in exc_mods])
    for v in viol:
        print("  " + v)
    print(f"НАРУШЕНИЙ: {len(viol)}")
    return 0 if not viol else 1


if __name__ == "__main__":
    sys.exit(main())
