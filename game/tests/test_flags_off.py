# -*- coding: utf-8 -*-
"""Гард-тест S1a: любой флаг в положении OFF НЕ должен расходовать rng.
Смысл по допуску Р3 п.3 (цитата): «прогнать одну и ту же партию с seed S при flag=off
и при полном отсутствии ветки кода (или при flag=off, сравнив последовательность вызовов
rng) — счётчик/журнал вызовов rng обязан совпадать побайтово».
Сценарии допуска: harvest off, ghost_bets off, prof_complex off.
Критерии приемлемости Р3.1 проверяются ВСЕ:
  (i)   количественно: число rng-вызовов OFF == базовому, ON > базового;
  (ii)  детерминизм OFF: два прогона с одним seed → идентичные журналы;
  (iii) побайтово относительно ВЫРЕЗАННОЙ ВЕТКИ (эмуляция «полного отсутствия ветки»):
        rng-расход жатвы изымается из потока random — журнал OFF обязан совпасть.
pytest недоступен в окружении → unittest. Это НЕ симуляции (запрет S1a): здесь
фиксированные микросверки журналов на одном seed, без прогонов-отчётов.
Запуск из корня: python3 -m unittest game.tests.test_flags_off -v
"""
import ast, json, os, subprocess, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, '..'))
import bb_full                      # noqa: E402
from config import make_cfg, CFG_DEFAULTS  # noqa: E402

# ---------------------------------------------------------------------------
# Инвариант, СОХРАНЁННЫЙ из Р3 п.3 (явная фиксация по требованию Р3.1):
# «любой флаг в положении OFF НЕ ДОЛЖЕН расходовать rng … журнал вызовов rng обязан
# совпадать побайтово» — реализуется как: журнал партии с флагом=off побайтово равен
# журналу той же партии, где rng-вызов off-ветки ИЗЪЯТ ИЗ ПОТОКА random (эмуляция
# полного отсутствия ветки), а не просто «префикс до первого расхождения».
# Прежняя ревизия теста молча подменяла базу сравнения (дефолт harvest=True принимался
# за «off») и требовала лишь префиксного совпадения — переписана по указанию автора (Р3.1).
# ---------------------------------------------------------------------------

_JOURNAL_SNIPPET = r'''
import sys, json, os
sys.path.insert(0, os.path.join(%r, "game"))
import bb_full
from config import make_cfg
spec = json.loads(sys.argv[1])
cfg = make_cfg(**spec["overrides"])
calls = []
real_cls = bb_full._Rng
CUT = spec.get("cut")          # имя метода _Rng, вырезаемого целиком (эмуляция отсутствия ветки)
CUT_CHOICE = spec.get("cut_harvest_choice", False)  # изъять ровно один rng.choice жатвы из потока

class Patched(real_cls):
    def _log(self, name, out):
        calls.append((name, out))
        return out
    if CUT:
        exec("def %%s(self, *a, **k):\n    self._log(%%r, None)\n    return None" %% (CUT, "cut_" + CUT))
    if CUT_CHOICE:
        _done = False
        def choice(self, seq):
            if (not self._done and isinstance(seq, list) and seq
                    and all(isinstance(q, dict) and q.get("alive") for q in seq)):
                self._done = True
                tgt = min(seq, key=lambda q: q["seat"])   # цель без обращения к random
                self._log("choice_CUT", tgt["seat"])      # маркер: событие было, rng цел
                return tgt
            return super().choice(seq)

bb_full._Rng = Patched
try:
    bb_full.run_game(spec["seed"], spec["n"], cfg=cfg, situation=spec.get("situation", "base"))
finally:
    bb_full._Rng = real_cls
print(json.dumps(calls, ensure_ascii=False, default=repr))
'''


def journal_subprocess(overrides, seed=7, n=8, situation='base', cut=None, cut_harvest_choice=False):
    """Журнал rng-вызовов партии в ЧИСТОМ процессе (гарантированный свежий поток random).
    Возвращает список вызовов; сравнение побайтовое через repr."""
    spec = dict(seed=seed, n=n, situation=situation, overrides=dict(overrides))
    if cut:
        spec['cut'] = cut
    if cut_harvest_choice:
        spec['cut_harvest_choice'] = True
    code = _JOURNAL_SNIPPET % ROOT_DIR
    p = subprocess.run([sys.executable, '-c', code, json.dumps(spec)],
                       capture_output=True, text=True, cwd=ROOT_DIR)
    if p.returncode != 0:
        raise RuntimeError(f"журнальный подпроцесс упал: {p.stderr[-800:]}")
    return json.loads(p.stdout)


def journal(seed, n, cfg, situation='base', cap=4000, cut=None):
    """In-process журнал (для проверок детерминизма внутри одного прогона-базиса)."""
    calls = []
    real_cls = bb_full._Rng

    class Patched(real_cls):
        def __init__(self, seed_):
            super().__init__(seed_)

        def _log(self, name, out):
            if len(calls) < cap:
                calls.append((name, out))
            return out

    if cut:
        setattr(Patched, cut, lambda self, *a, **k: None)
    bb_full._Rng = Patched
    try:
        bb_full.run_game(seed, n, cfg=cfg, situation=situation)
    finally:
        bb_full._Rng = real_cls
    return repr(calls)


class TestFlagsOff(unittest.TestCase):
    SEED, N = 7, 8

    # ---- сценарий 1: главный гард допуска — harvest OFF не расходует rng ----
    def test_harvest_off_does_not_consume_rng(self):
        SEED = 8   # на этом seed ON-ветка жива: harvest наступает (гард не пустой)
        # (ii) детерминизм OFF: два прогона с одним seed в ЧИСТЫХ процессах → идентичные журналы
        j_off = journal_subprocess({'harvest': False}, seed=SEED, n=self.N)
        j_off2 = journal_subprocess({'harvest': False}, seed=SEED, n=self.N)
        self.assertEqual(repr(j_off), repr(j_off2), "детерминизм OFF: один seed → идентичный журнал")

        # контроль непустоты гарда: на seed=8 ветка ON реально срабатывает
        st_on, _ = bb_full.run_game(SEED, self.N, cfg=make_cfg(harvest=True))
        self.assertGreater(st_on['harvests'], 0, "контроль: ON-ветка жива на seed=8 (гард не пустой)")

        # база сравнения = дефолт печати №2. ВНИМАНИЕ (фиксация Р3.1): дефолт harvest по §7 v3
        # («Жатва — предохранитель… умирает один случайный живой») и legacy (=414 без флага) — True;
        # допуск Р3 диктовал default off. Расхождение записано в CONFLICTS C34; тест проверяет
        # ОБА варианта базы, поэтому не зависит от того, как разрешится C34.
        j_def_on = journal_subprocess({}, seed=SEED, n=self.N)                    # дефолт диска (harvest=True)
        j_def_off = journal_subprocess({'harvest': True}, seed=SEED, n=self.N)    # эквивалент дефолта явным on
        self.assertEqual(repr(j_def_on), repr(j_def_off), "явный on == дефолт (эквивалентность конфигов)")

        # (i)+(iii) количественно и побайтово относительно ВЫРЕЗАННОЙ ВЕТКИ:
        # единственная rng-трата жатвы — rng.choice(alive()) (bb_full.py строка `v = rng.choice(alive());
        # st['harvests'] += 1`). Эмуляция «полного отсутствия ветки»: harvest=True, но этот choice
        # изымается из потока random (маркер choice_CUT). Журнал OFF обязан побайтово совпасть
        # с журналом вырезанной ветки (после удаления маркера) — это и есть инвариант Р3 п.3.
        j_cut = journal_subprocess({'harvest': True}, seed=SEED, n=self.N, cut_harvest_choice=True)
        markers = [x for x in j_cut if x[0] == 'choice_CUT']
        self.assertEqual(len(markers), 1, "базис: ровно один rng-расход жатвы был изъят")
        j_cut_nomarker = [x for x in j_cut if x[0] != 'choice_CUT']
        self.assertEqual(repr(j_off), repr(j_cut_nomarker),
                         "OFF побайтово == ON с вырезанным rng-расходом жатвы ⇒ инвариант Р3 п.3 сохранён")
        self.assertEqual(len(j_off), len(j_cut_nomarker), "OFF добавил 0 вызовов rng к потоку без ветки")

        # (i) количественно: ON > OFF по числу потреблённых rng-вызовов
        j_on = journal_subprocess({'harvest': True}, seed=SEED, n=self.N)
        self.assertGreater(len(j_on), len(j_off),
                           "ON > базового по числу rng-вызовов (реальный поток)")

    # ---- сценарий 2: ghost_bets OFF (= default печати №2) не смещает rng вообще ----
    def test_ghost_bets_off_is_rng_neutral_default(self):
        self.assertIs(CFG_DEFAULTS['ghost_bets'], False, "печать №2: ставки вырезаны")
        j_off = journal_subprocess({'ghost_bets': False}, seed=self.SEED, n=self.N)
        j_def = journal_subprocess({}, seed=self.SEED, n=self.N)
        self.assertEqual(repr(j_off), repr(j_def), "ghost_bets=off == дефолт: журнал побайтово совпадает")
        j_on = journal_subprocess({'ghost_bets': True}, seed=self.SEED, n=self.N)
        self.assertGreaterEqual(len(j_on), len(j_off), "on-ветка не уменьшает число вызовов")
        self.assertNotEqual(repr(j_off), repr(j_on), "on-ветка добавляет вызовы (гард осмыслен)")

    # ---- сценарий 3: prof_complex OFF — заглушка, rng не трогает ----
    def test_prof_complex_off_stub(self):
        self.assertIs(CFG_DEFAULTS['prof_complex'], False)
        with self.assertRaises(NotImplementedError):
            bb_full.run_game(self.SEED, 2, cfg=make_cfg(prof_complex=True))
        j_off = journal_subprocess({'prof_complex': False}, seed=self.SEED, n=self.N)
        j_def = journal_subprocess({}, seed=self.SEED, n=self.N)
        self.assertEqual(repr(j_off), repr(j_def), "prof_complex=off не расходует rng относительно дефолта")

    # ---- свёртка: все флаги, уже выключенные в печати №2, побайтово равны дефолту ----
    def test_every_off_default_flag_rng_neutral(self):
        baseline = journal_subprocess({}, seed=self.SEED, n=self.N)
        for flag, val in CFG_DEFAULTS.items():
            off_like = (val is False) or (isinstance(val, str) and val == 'none')
            if off_like:
                again = journal_subprocess({flag: val}, seed=self.SEED, n=self.N)
                self.assertEqual(repr(baseline), repr(again), f"OFF-дефолт {flag} сместил rng-журнал")


if __name__ == '__main__':
    unittest.main(verbosity=2)
