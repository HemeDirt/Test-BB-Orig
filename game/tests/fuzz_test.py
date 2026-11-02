# -*- coding: utf-8 -*-
"""Фазз S1b (п.4.4; фиксы вердикта Р8 а/б/в): инварианты F1–F6 из SPEC_CONSOLIDATED.md §7, 240 прогонов.
Фикс (а): эксцизии пишутся в game/_bb_excised_<flag>.py (как в гард-тесте), а не в tempfile.mkdtemp —
иначе подпроцесс резолвит ROOT от __file__ и не находит data/deck (FileNotFoundError).
Фикс (б): сравнение OFF==база заменено на гардовый инвариант OFF == EXCISED побайтово (для harvest_k
равенство журналов ложно даже при корректном флаге — параметр читается в активную ветку жатвы).
Фикс (в): F4 — событийные инварианты (§7 + C41): alive<=n; deaths>=n-alive; revives<=deaths; end<=cap.
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
CHAIN_PATHS = []
_chain_cache = {}
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


def branch_rng_calls(src_text, flag_key):
    """Статический разбор: число rng-вызовов в теле ветки if C[flag] и есть ли ранний выход
    (return/continue/break) ДО первого rng-вызова. Для guard-флагов (`if not C[f]: ... return`)
    OFF не расходует rng тогда и только тогда, когда ранний выход есть — динамический счётчик с
    monkey-patch random.Random здесь неприменим (движок вызывает методы экземпляра random.Random,
    глобальная подмена класса их не перехватывает; diag Р8)."""
    tree = ast.parse(src_text)
    total = 0
    early_exit = False
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            keys = {x.slice.value for x in ast.walk(node.test)
                    if isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name)
                    and x.value.id == "C" and isinstance(x.slice, ast.Constant)
                    and isinstance(x.slice.value, str)}
            if flag_key in keys:
                first_rng = None
                for sub in ast.walk(node.body[0] if node.body else node):
                    pass
                # первый rng-вызов в теле (по строке)
                lines = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                       and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "rng":
                        lines.append(sub.lineno)
                if lines:
                    total += len(lines)
                    fr = min(lines)
                    for sub in ast.walk(node):
                        if isinstance(sub, (ast.Return, ast.Continue, ast.Break)) and getattr(sub, "lineno", 10**9) < fr:
                            early_exit = True
    return total, early_exit


def count_marked_calls(module_path, seed, n, overrides, situation, flag_key):
    """Число rng-вызовов внутри ветвей flag под процессом (счётчик по адресным маркерам)."""
    payload = json.dumps({"seed": seed, "n": n, "situation": situation,
                          "overrides": overrides, "module_path": module_path, "count_flag": flag_key})
    script = os.path.join(tempfile.gettempdir(), "_fuzz_counter.py")
    runner = r'''
import sys, json, os, ast, importlib.util
GAME = os.environ["BB_GAME_DIR"]; sys.path.insert(0, GAME)
spec_s = json.loads(sys.argv[1])
mp = spec_s["module_path"]
uspec = importlib.util.spec_from_file_location("_bb_count_", mp)
mod = importlib.util.module_from_spec(uspec); uspec.loader.exec_module(mod)
from config import make_cfg
src = open(mp, encoding="utf-8").read()
tree = ast.parse(src)
marks = set()
for node in ast.walk(tree):
    if isinstance(node, ast.If) and any(isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name)
            and x.value.id == "C" and isinstance(x.slice, ast.Constant) and x.slice.value == spec_s["count_flag"]
            for x in ast.walk(node.test)):
        first = None
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
               and isinstance(sub.func.value, ast.Name) and sub.func.value.id == "rng":
                first = sub.lineno; break
        if first is not None: marks.add(first)
calls = [0]
import random as _r
_BASE = _r.Random  # захват оригинала ДО подмены (иначе self._mark рекурсии)
class Tracer(_BASE):
    def _mark(self, f):
        fr = sys._getframe()
        while fr is not None:
            if os.path.basename(fr.f_code.co_filename) == os.path.basename(mp) and fr.f_lineno in marks:
                calls[0] += 1; return
            fr = fr.f_back
    def choice(self, *a, **k): self._mark("choice"); return _BASE.choice(self, *a, **k)
    def randint(self, *a, **k): self._mark("randint"); return _BASE.randint(self, *a, **k)
    def randrange(self, *a, **k): self._mark("randrange"); return _BASE.randrange(self, *a, **k)
    def random(self, *a, **k): self._mark("random"); return _BASE.random(self, *a, **k)
    def shuffle(self, *a, **k): self._mark("shuffle"); return _BASE.shuffle(self, *a, **k)
_r.Random = Tracer
cfg = make_cfg(**spec_s["overrides"])
st, P = mod.run_game(spec_s["seed"], spec_s["n"], cfg=cfg, situation=spec_s["situation"], log=[])
print(json.dumps({"count": calls[0], "marks": sorted(marks)}))
'''
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(runner)
    env = dict(os.environ, BB_GAME_DIR=GAME)
    p = subprocess.run([sys.executable, script, payload], capture_output=True, text=True, env=env, timeout=180)
    if p.returncode != 0:
        raise RuntimeError("counter failed:\n" + p.stderr[-800:])
    return json.loads(p.stdout.strip().splitlines()[-1])


def chain_module(module_paths):
    """Цепочная AST-эксцизия всех выключенных if-флагов в один физический модуль (в game/)."""
    key = tuple(module_paths)
    if key not in _chain_cache:
        t = _src
        for pth in module_paths:
            flag = os.path.basename(pth)[len("_bb_excised_"):-len(".py")]
            t, nr, pr = excise(t, flag)
        cpath = os.path.join(GAME, "_bb_excised_chain_%d.py" % (len(_chain_cache) + 1))
        with open(cpath, "w", encoding="utf-8") as fh:
            fh.write(t)
        _chain_cache[key] = cpath
        CHAIN_PATHS.append(cpath)
    return _chain_cache[key]


def run_excised_all(seed, n, situation, module_paths):
    """all-OFF против all-EXCISED: цепочная AST-эксцизия (истинное отсутствие ветвей)."""
    return run_proc(seed, n, {}, situation, module_path=chain_module(module_paths))


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

    # Фикс (а) по вердикту Р8: временный модуль ИМЕННО в game/ (каталог в .gitignore: game/_bb_excised*.py),
    # как в гард-тесте write_excised (test_flags_off.py:202) — иначе ROOT движка resolves в /tmp и deck не находится.
    exc_dir = GAME
    exc_mods = {}
    _cleanup = []
    # классификация if-найденных флагов (diag Р8): IF_GATED — у флага есть собственная ast.If-ветка
    # (полное отсутствие == OFF побайтово); GUARD_ONLY — флаг встречается только в guard-условиях
    # «if not C[f]: continue» / составных условиях (эксцизия такого if удаляет и соседние проверки —
    # журнал-равенству не подлежит, проверка переносится на rng-чистоту по маркерам).
    _tree_g = ast.parse(_src)
    IF_GATED, GUARD_ONLY = set(), set()
    for _node in ast.walk(_tree_g):
        if isinstance(_node, ast.If):
            _keys = {_sub.slice.value for _sub in ast.walk(_node.test)
                     if isinstance(_sub, ast.Subscript) and isinstance(_sub.value, ast.Name)
                     and _sub.value.id == "C" and isinstance(_sub.slice, ast.Constant)
                     and isinstance(_sub.slice.value, str)}
            _is_guard = len(_node.body) == 1 and isinstance(_node.body[0], (ast.Continue, ast.Pass))
            for _g in _keys:
                if _is_guard or len(_keys) > 1:
                    GUARD_ONLY.add(_g)   # общий if или ранний выход — эксцизия != OFF
                else:
                    IF_GATED.add(_g)     # собственный if-гейт флага с телом
    IF_GATED -= GUARD_ONLY               # флаг с хотя бы одним общим/guard-if не подлежит EXCISED-равенству
    for f in COMBO_FLAGS:
        src2, nr, pr = excise(_src, f)
        if pr or nr == 0:
            continue  # non-if-флаги (tokens2-выражение и т.п.) — F5-excision для них неприменим, фиксируется ниже
        path = os.path.join(exc_dir, f"_bb_excised_{f}.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src2)
        exc_mods[f] = path
        _cleanup.append(path)

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
            # F4 (фикс в по вердикту Р8; расхождение формулировки §7 → C41)
            csum = sum(res["causes"].values())
            errs = []
            if res["deaths"] < 0: errs.append("deaths<0")
            if res["harvests"] < 0: errs.append("harvests<0")
            if res["revives"] > res["deaths"]: errs.append("revives>deaths")
            if csum != res["deaths"]: errs.append(f"deaths({res['deaths']})!=sum(causes)({csum})")
            if res["alive"] > res["n"]: errs.append(f"alive({res['alive']})>n({res['n']})")
            if res["deaths"] < res["n"] - res["alive"]:
                errs.append(f"deaths({res['deaths']})<n-alive({res['n']-res['alive']})")
            if res["end"] > CAP: errs.append(f"end({res['end']})>cycle_cap({CAP})")
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
            # F5 (фикс б по вердикту Р8): all-OFF сверяется с all-EXCISED побайтово, НЕ с базой:
            # флаги harvest/special_cards/soul_cards/prof_simple имеют дефолт ON, поэтому all-OFF
            # ОБЯЗАН отличаться от базы — сравнение с базой здесь методологически неверно.
            off_set = [f for f in COMBO_FLAGS if ov.get(f) is False]
            if off_set:
                # сравнимость журнала побайтово только при полностью if-гейтованном наборе (см. C41/diag:
                # гейды `if not C[f]: continue` — это НЕ ast.If-ветка флага, эксцизия их не снимает)
                gated = [f for f in off_set if f in IF_GATED]
                if len(gated) == len(off_set):
                    mods = [exc_mods[f] for f in gated]
                    exall = run_excised_all(seed, n, sit, mods); runs += 1
                    if exall.get("ok") and exall.get("jhash") != res.get("jhash"):
                        viol.append(f"F5 seed={seed} n={n} sit={sit}: all-OFF != all-EXCISED")
                    elif not exall.get("ok"):
                        viol.append(f"F5 seed={seed}: all-excision упала: {exall.get('err')}")
                    else:
                        cnt["F5"] += 1
                else:
                    # смешанный набор: журнал-эквивалент EXCISED неприменим — статическая проверка
                    # rng-чистоты guard-флагов (ранний выход до первого rng в ветке)
                    clean = True
                    for f in off_set:
                        if f in IF_GATED:
                            continue
                        tot, early = branch_rng_calls(_src, f)
                        if tot and not early:
                            clean = False
                            viol.append(f"F5 seed={seed}: флаг {f}=OFF может расходовать rng в ветке ({tot} вызовов, нет раннего выхода)")
                    if clean:
                        cnt["F5"] += 1
    # F5-расширение (фикс б по вердикту Р8): корректный инвариант — как в гарде: OFF == EXCISED побайтово
    # (сверка OFF с базой неприменима для флагов с дефолтом ON: harvest, special_cards, soul_cards, prof_simple).
    for f in COMBO_FLAGS:
        seed = seeds[rng.randrange(len(seeds))]; n = rng.randint(2, 8)
        if f in IF_GATED:
            off = run_proc(seed, n, {f: False}, "base"); runs += 1
            exd = run_proc(seed, n, {f: True}, "base", module_path=exc_mods[f]); runs += 1
            if not exd.get("ok"):
                viol.append(f"F5 seed={seed}: эксцизия {f} упала: {exd.get('err')}")
            elif off.get("ok") and off["jhash"] != exd["jhash"]:
                viol.append(f"F5 seed={seed}: флаг {f}: OFF != EXCISED побайтово")
            else:
                cnt["F5"] += 1
        elif f in GUARD_ONLY:
            # guard-only: журнал-равенство с EXCISED методологически неприменимо (эксцизия снимает весь if,
            # в т.ч. соседние проверки; diag Р8: prof_simple/spec_cycle/soul_cards/special_cards) —
            # корректная проверка: OFF не расходует rng (статика: ранний выход до первого rng-вызова ветки)
            off = run_proc(seed, n, {f: False}, "base"); runs += 1
            tot, early = branch_rng_calls(_src, f)
            if not off.get("ok"):
                viol.append(f"F5 seed={seed}: off-прогон {f} упал: {off.get('err')}")
            elif tot and not early:
                viol.append(f"F5 seed={seed}: флаг {f}=OFF может расходовать rng в ветке ({tot}, нет раннего выхода)")
            else:
                cnt["F5"] += 1
        else:
            off = run_proc(seed, n, {f: False}, "base"); runs += 1
            if not off.get("ok"):
                viol.append(f"F5 seed={seed}: off-прогон {f} упал: {off.get('err')}")
            else:
                cnt["F5"] += 1
    cnt["F6"] = runs  # покрытие: n∈[2..8], 6 ситуаций, случайные комбинации — учтены в плане
    print(f"прогонов subprocess: {runs}; диапазон seed: [{min(seeds)}..{max(seeds)}]")
    print("счётчики:", json.dumps(cnt, ensure_ascii=False))
    print("НЕ-if флаги (F5-checks только off==base):", [f for f in COMBO_FLAGS if f not in exc_mods])
    for v in viol:
        print("  " + v)
    for pth in _cleanup + CHAIN_PATHS:
        try:
            os.unlink(pth)
        except OSError:
            pass
    print(f"НАРУШЕНИЙ: {len(viol)}")
    return 0 if not viol else 1


if __name__ == "__main__":
    sys.exit(main())
