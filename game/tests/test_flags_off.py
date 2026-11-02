# -*- coding: utf-8 -*-
"""Гард-тест S1a (ревизия Р3.3, ВЕРДИКТ «вариант В»): любой флаг OFF не расходует rng.

Смысл допуска Р3 п.3 (цитата): «прогнать одну и ту же партию с seed S при flag=off
и при ПОЛНОМ ОТСУТСТВИИ ветки кода … журнал вызовов rng обязан совпадать побайтово».

Почему именно эксцизия (вердикт Р3.3; запись C36): жатва — ветка, МЕНЯЮЩАЯ СОСТОЯНИЕ
(bb_full.py строки 636–639: rng.choice + death(v,'harvest')). Изъятие её вызова из
журнала ON-прогона не отменяет смерть — партии расходятся каскадом с первого
срабатывания, побайтовое равенство математически невозможно. Варианты A (формат _Rng)
и B (ослабить до имён+чисел) отклонены координатором. Реализация допуска — буквальная:
AST-эксцизия if-узлов флага во временный модуль _bb_excised_<flag>.py (истинное
отсутствие ветки), прогон в ЧИСТОМ подпроцессе (урок iii), сравнение журналов побайтово.

Инвариант, СОХРАНЁННЫЙ из Р3 п.3 (явная фиксация по требованию Р3.1 п.4):
(а) журнал OFF == журналу EXCISED ПОББАЙТОВО ПО ПОЛНОЙ ДЛИНЕ (В1(1));
(б) количественный критерий (i): число rng-вызовов OFF == базовому (EXCISED),
    ON > базового (В3(д) + отдельный assert);
(в) детерминизм OFF: два чистых подпроцесса, один seed → идентичные журналы (В3(г));
(г) ghost_bets по В5/Р3.2 п.2.2: off==def побайтово; on!=off; первый индекс расхождения
    on/off >= индекса первой смерти; ДЛИНЫ ЖУРНАЛОВ НЕ СРАВНИВАТЬ (assert len убран).
Адресные маркеры В2: обёртка пишет на каждый вызов (method, out, co_name, f_lineno)
через sys._getframe — одного co_name недостаточно (жатва инлайн в run_game). Место
вызова жатвы: функция run_game, линия 637. Прод-код НЕ тронут: никаких хуков в bb_full.py.
CUT-хирургия прежней ревизии (cut_harvest_choice, эвристика «все alive») УДАЛЕНА ЦЕЛИКОМ (В4).
Запуск из корня: python3 -m unittest game.tests.test_flags_off -v
Это НЕ симуляции (запрет S1a): фиксированные микросверки журналов на одном seed.
"""
import ast, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(HERE))
GAME_DIR = os.path.join(ROOT_DIR, 'game')
sys.path.insert(0, GAME_DIR)
from config import CFG_DEFAULTS     # noqa: E402

SEED, NPLAY, SIT = 11, 8, 'base'

# ---------------- AST-эксцизия (В1) ----------------
def cond_mentions(node_test, flag_key):
    for sub in ast.walk(node_test):
        if (isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name)
                and sub.value.id == 'C' and isinstance(sub.slice, ast.Constant)
                and sub.slice.value == flag_key):
            return True
    return False


def strip_body(body, flag_key, removed, problems):
    out = []
    for st in body:
        if isinstance(st, ast.If) and cond_mentions(st.test, flag_key):
            if st.orelse:
                problems.append(f'if@{st.lineno}: непустой orelse/elif — STOP по вердикту В1')
                out.append(st)
                continue
            removed[0] += 1
            continue                       # истинное отсутствие ветки
        out.append(st)
    return out


def excise(src_text, flag_key):
    """Удалить ВСЕ узлы ast.If с подпиской C[flag_key] в условии.
    Возвращает (new_src, n_removed, problems)."""
    tree = ast.parse(src_text)
    removed = [0]
    problems = []
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            old = getattr(node, field, None)
            if isinstance(old, list) and old and all(isinstance(x, ast.stmt) for x in old):
                new = []
                for st in old:
                    if isinstance(st, ast.If) and cond_mentions(st.test, flag_key):
                        if st.orelse:
                            problems.append(f'if@{st.lineno}: непустой orelse/elif — STOP по вердикту В1')
                            new.append(st)
                            continue
                        removed[0] += 1
                        continue
                    new.append(st)
                setattr(node, field, new)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree), removed[0], problems


# ---------------- раннер подпроцесса (В1(д), В2, В6) ----------------
_RUNNER = r'''
import sys, json, os, importlib.util
GAME = os.environ["BB_GAME_DIR"]
sys.path.insert(0, GAME)
spec_s = json.loads(sys.argv[1])
if spec_s.get("module_path"):                       # временный эксцизированный модуль
    uspec = importlib.util.spec_from_file_location("_bb_excised_", spec_s["module_path"])
    bb = importlib.util.module_from_spec(uspec); uspec.loader.exec_module(bb)
else:
    sys.path.insert(0, os.path.join(GAME, "tests"))
    import bb_full as bb
from config import make_cfg
cfg = make_cfg(**spec_s["overrides"])
calls = []
real_cls = bb._Rng

ENGINE_MARKS = ("bb_full", "_bb_excised_")   # файл движка или его эксцизированной копии
def _is_engine(fn):
    fn = fn or ""
    return any(m in fn for m in ENGINE_MARKS)

DEATH_MARK = {"n": None}
_orig_run = bb.run_game
import types as _t

class Patched(real_cls):
    def _log(self, name, out):
        fr = ("?", 0); hln = 0                       # В2: адрес вызова (co_name, f_lineno)
        f = sys._getframe(1)                        # обходим стек до кадров движка
        while f is not None:
            if _is_engine(f.f_code.co_filename):
                fr = (f.f_code.co_name, f.f_lineno)
                if fr[0] == "run_game":             # НЕСУЩИЙ кадр run_game — это линия места вызова
                    hln = f.f_lineno                # (для жатвы — 637 на HEAD; inner-хелперы дают run_game-кадр выше)
            f = f.f_back
        calls.append([name, repr(out), fr[0], fr[1], hln])
        return out
bb._Rng = Patched

_first_death_at = {"n": None}
def _tracer(frame, event, arg):
    if frame.f_code.co_name == "death" and _first_death_at["n"] is None:
        _first_death_at["n"] = len(calls)           # rng-вызовов к моменту входа в первую смерть
        return None
    return _tracer if _first_death_at["n"] is None else None
sys.settrace(_tracer)
try:
    st, P = bb.run_game(spec_s["seed"], spec_s["n"], cfg=cfg, situation=spec_s["situation"])
    sys.settrace(None)
    res = dict(calls=calls, end=st["end"], deaths=st["deaths"], harvests=st["harvests"],
               first_death=st["first_death"], bets=st["bets"],
               death_journal_len=_first_death_at["n"])
except NotImplementedError as e:
    sys.settrace(None)
    res = dict(error=type(e).__name__+": "+str(e), calls=calls, end=None, deaths=None, harvests=None,
               first_death=None, bets=None)
print(json.dumps(res, ensure_ascii=False))
'''


def run_proc(overrides, module_path=None):
    payload = json.dumps({"seed": SEED, "n": NPLAY, "situation": SIT,
                          "overrides": overrides, "module_path": module_path})
    script = os.path.join(tempfile.gettempdir(), "_guard_runner.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(_RUNNER)
    env = dict(os.environ, BB_GAME_DIR=GAME_DIR)
    p = subprocess.run([sys.executable, script, payload], capture_output=True,
                       text=True, env=env, timeout=180)
    if p.returncode != 0:
        raise RuntimeError("runner failed:\n" + p.stderr[-1500:])
    return json.loads(p.stdout.strip().splitlines()[-1])


def journal_of(res):
    return [(c[0], c[1]) for c in res["calls"]]     # пары (method, out) — без маркеров


HARVEST_CALLER = "run_game"                          # В2: имя функции места вызова жатвы


def harvest_line_in_src():
    """Точная линия места вызова rng жатвы в bb_full.py.
    Ревизия S1b (KT-4, разрешение «пересчёт констант номеров строк»): после добавления
    harvest_mode/base-ветки выбор жертвы и счётчик живут на ДВУХ соседних строках:
        v = rng.choice(pool_a)          <- искомая линия (маркер вызова rng)
        st['harvests'] += 1            <- следующая строка
    Старый якорь (одна строка с rng.choice(alive()) и st['harvests']) более не существует;
    паттерн намеренно узкий: rng.choice(pool_a) встречается только в базовой ветке жатвы
    (leader — rng.choice(ld), extra — rng.choice(lv2) — другие имена пулов). Не найдено — падение."""
    with open(os.path.join(GAME_DIR, "bb_full.py"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
        for i, l in enumerate(lines, 1):
            if "rng.choice(pool_a)" in l and i < len(lines) and "st['harvests']" in lines[i]:
                return i
    raise AssertionError("место вызова жатвы не найдено в bb_full.py — молчаливый проход запрещён")


def harvest_marks(res, line):
    """В2: ДВОЙНОЙ адресный фильтр: co_name==run_game И f_lineno==линия жатвы.
    Раздача рук (shuffle/sample) и выборы из хелперов (act/turn/death/ghost_phase) отсекаются
    по линии; выбор цели мародёрства призраком (прежний FAIL idx 70) — по co_name ghost_phase."""
    return [i for i, c in enumerate(res["calls"])
            if c[0] == "choice" and c[2] == HARVEST_CALLER and c[4] == line]


def write_excised(flag_key):
    """В1(г): временный модуль ИМЕННО в game/ — чтобы ROOT и импорты решались как у bb_full."""
    with open(os.path.join(GAME_DIR, "bb_full.py"), encoding="utf-8") as fh:
        src = fh.read()
    new_src, n_removed, problems = excise(src, flag_key)
    if problems:
        raise AssertionError("ЭКСЦИЗИЯ НЕТРИВИАЛЬНА (стоп по В1): " + "; ".join(problems))
    path = os.path.join(GAME_DIR, "_bb_excised_%s.py" % flag_key)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_src)
    return path, n_removed


class TestFlagsOff(unittest.TestCase):
    _exc_paths = []

    @classmethod
    def tearDownClass(cls):                           # В1(г): временный файл удалить в finally-гаранте
        for pth in cls._exc_paths:
            try:
                os.unlink(pth)
            except OSError:
                pass
        cls._exc_paths = []

    # ---------- harvest: В1(1)-(2) + В3 ----------
    def test_harvest_off_equals_excised_bytewise(self):
        exc_path, n_removed = write_excised("harvest"); self._exc_paths.append(exc_path)
        self.assertGreaterEqual(n_removed, 1,
            "паттерн разъехался: узлов C['harvest'] не найдено — молчаливый проход запрещён (В1(в))")
        base = run_proc({}, module_path=exc_path)    # EXCISED: ветви нет физически
        off = run_proc({"harvest": False})           # флаг off
        on = run_proc({"harvest": True})             # флаг on
        self.assertEqual(journal_of(off), journal_of(base),
                         "гард Р3 п.3: журнал OFF обязан побайтово == EXCISED по полной длине")
        self.assertNotEqual(journal_of(on), journal_of(base), "ON должен отличаться от базы")
        # (2) контроль непустоты
        self.assertEqual(off["harvests"], 0); self.assertEqual(base["harvests"], 0)
        self.assertGreaterEqual(on["harvests"], 1)
        # В3(а): в OFF-журнале ноль маркированных записей жатвы (адрес: кадр run_game + choice)
        hl = harvest_line_in_src()                  # 637 на HEAD
        bad = harvest_marks(off, hl)
        self.assertEqual(bad, [], "OFF-прогон коснулся rng-места жатвы: индексы %r" % bad[:4])
        # контроль непустоты фильтра: в EXCISED тоже ноль (жатвы физически нет)
        self.assertEqual(harvest_marks(base, hl), [], "эксцизия не убрала rng жатвы")
        # контроль работы фильтра: ON обязан дать метки (иначе фильтр разъехался бы молча)
        mark_idx = harvest_marks(on, hl)
        self.assertTrue(mark_idx, "в ON-журнале нет ни одной маркированной жатвы — фильтр разъехался")
        k = mark_idx[0]
        # В3(б'): OFF == префиксу ON СТРОГО ДО первой маркированной записи жатвы (без неё:
        # сама запись жатвы существует только в ON-ветке — включать её нельзя, это не «до»)
        self.assertEqual(journal_of(off)[:k], journal_of(on)[:k],
                         "расхождение OFF/ON раньше первой жатвы")
        # В3(в): индекс первого расхождения OFF/ON == индексу первой маркерной записи жатвы
        jo, jn = journal_of(off), journal_of(on)
        diff = min(len(jo), len(jn))
        for i in range(min(len(jo), len(jn))):
            if jo[i] != jn[i]:
                diff = i; break
        self.assertEqual(diff, k, "первое расхождение смещено относительно маркера жатвы")
        # В3(д): полные журналы ON != OFF
        self.assertNotEqual(jn, jo)
        # количественный критерий (i): число вызовов OFF == базе, ON > базы
        self.assertEqual(len(off["calls"]), len(base["calls"]))
        self.assertGreater(len(on["calls"]), len(base["calls"]))

    def test_determinism_off_two_subprocesses(self):
        a = run_proc({"harvest": False}); b = run_proc({"harvest": False})
        self.assertEqual(journal_of(a), journal_of(b), "детерминизм OFF нарушен (В3(г))")

    # ---------- ghost_bets: В1(3) + В5 ----------
    def test_ghost_bets_off_equals_default_and_excised(self):
        self.assertIs(CFG_DEFAULTS["ghost_bets"], False, "дефолт печати №2: ghost_bets off")
        exc_path, n_removed = write_excised("ghost_bets"); self._exc_paths.append(exc_path)
        self.assertGreaterEqual(n_removed, 2, "ожидается ≥2 узла C['ghost_bets'] (~511 и ~538)")
        base = run_proc({})                          # дефолтный прогон (ghost_bets off)
        off = run_proc({"ghost_bets": False})
        on = run_proc({"ghost_bets": True})
        self.assertEqual(journal_of(off), journal_of(base), "off-журнал побайтово == базовому")
        exc = run_proc({}, module_path=exc_path)
        self.assertEqual(journal_of(base), journal_of(exc),
                         "эксцизия ghost_bets: база == EXCISED побайтово (В1(3))")
        self.assertNotEqual(journal_of(on), journal_of(base), "on != базе")
        # первый индекс расхождения on/off >= индекса первой СМЕРТИ в том же журнале (OFF-база);
        # длины НЕ сравнивать (вердикт Р3.2 п.2.2)
        fd = off["first_death"]
        self.assertIsNotNone(fd, "в этом сценарии должна быть хотя бы одна смерть (иначе тест пуст)")
        joff, jon = journal_of(off), journal_of(on)
        diverge = min(len(joff), len(jon))
        for i in range(min(len(joff), len(jon))):
            if joff[i] != jon[i]:
                diverge = i; break
        # индекс первой СМЕРТИ в той же шкале журнала: число rng-вызовов к моменту first_death
        # (first_death снимается в подпроцессе ровно перед append записи journal_of)
        idx_death = off.get("death_journal_len")
        self.assertIsNotNone(idx_death, "раннер не вернул метку времени первой смерти")
        self.assertGreaterEqual(diverge, idx_death,
            "расхождение on/off (%d) раньше первой смерти (%d) — ставки призраков расходуют rng до смерти"
            % (diverge, idx_death))

    # ---------- prof_complex: заглушка (В5) ----------
    def test_prof_complex_off_stub(self):
        off = run_proc({"prof_complex": False})
        self.assertIsNotNone(off["end"], "при prof_complex off партия идёт штатно")
        on = run_proc({"prof_complex": True})
        self.assertIn("NotImplementedError", on.get("error") or "",
                      "prof_complex=True обязан падать NotImplemented (лист автора отдельно)")
        self.assertEqual(journal_of(on), journal_of(off)[:len(journal_of(on))],
                         "до падения prof_complex rng-поток совпадает с off (заглушка нейтральна)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
