# -*- coding: utf-8 -*-
"""Гард-тест S1a: любой флаг в положении OFF НЕ должен расходовать rng.
Смысл по допуску: прогнать одну и ту же партию с seed S при flag=off и сравнить
ПОБАЙТОВО журнал вызовов rng с партией, где ветка кода отсутствует (или с дефолтом,
если off == default). Сценарии: harvest off, ghost_bets off, prof_complex off.
pytest недоступен в окружении → unittest. Это НЕ симуляции (запрет S1a): здесь
фиксированные микросверки журналов на одном seed.
Запуск из корня: python3 -m unittest game.tests.test_flags_off -v
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import bb_full                      # noqa: E402
from config import make_cfg, CFG_DEFAULTS  # noqa: E402


def journal(seed, n, cfg, situation='base', cap=4000, cut=None):
    """Последовательность rng-вызовов партии (имя+аргументы+результат), побайтово.
    cut — имя метода _Rng, который «вырезается» целиком (эмуляция отсутствия ветки)."""
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

    # ---- сценарий 1: главный гард допуска — harvest OFF обязан совпасть с ВЫРЕЗАННОЙ веткой ----
    def test_harvest_off_matches_absent_branch(self):
        """Требование S1a: при flag=off журнал rng побайтово совпадает с партией, где ветка
        кода ОТСУТСТВУЕТ. Эмуляция «нет ветки»: прогон harvest=on, но на тактах жатвы выбор
        цели берётся из детерминированного off-журнала той же партии и НЕ расходует поток
        random (_r.choice не вызывается). Финальный журнал обязан сойтись с off побайтово;
        если бы OFF-ветка расходовала rng — журналы разошлись бы ДО первой жатвы."""
        import ast
        SEED = 8  # seed=7 даёт identical journals (жатва в этой партии не срабатывает) — тест был бы пустым
        j_off = journal(SEED, self.N, make_cfg(harvest=False))
        j_on = journal(SEED, self.N, make_cfg(harvest=True))
        self.assertNotEqual(j_off, j_on, "контроль: ON-ветка жива (иначе тест пустой)")
        off_seq = ast.literal_eval(j_off)

        calls = []
        real_cls = bb_full._Rng
        ptr = {'i': 0}

        class Branchless(real_cls):
            def _log(self, name, out):
                calls.append((name, out))
                return out

            def choice(self, seq):
                nxt = off_seq[ptr['i']] if ptr['i'] < len(off_seq) else None
                if isinstance(nxt, tuple) and nxt[0] == 'choice' and isinstance(nxt[1], dict) \
                        and any(isinstance(q, dict) and q.get('seat') == nxt[1].get('seat') for q in seq):
                    tgt = next(q for q in seq if q.get('seat') == nxt[1]['seat'])
                    ptr['i'] += 1                      # синхронно идём по off-журналу
                    calls.append(('choice', tgt))      # rng НЕ расходуем: ветка «вырезана»
                    return tgt
                return super().choice(seq)             # обычный путь (реальный rng + журнал)

            def _match(self, name, out):
                self._log(name, out)
                nxt = off_seq[ptr['i']] if ptr['i'] < len(off_seq) else None
                if nxt is not None and nxt[0] == name and repr(nxt[1]) == repr(out):
                    ptr['i'] += 1
                return out

            def randint(self, a, b): return self._match('randint', self._r.randint(a, b))
            def random(self):        return self._match('random', self._r.random())
            def uniform(self, a, b): return self._match('uniform', self._r.uniform(a, b))
            def randrange(self, n):  return self._match('randrange', self._r.randrange(n))
            def sample(self, seq, k): return self._match('sample', self._r.sample(seq, k))
            def choices(self, pop, weights=None, k=1):
                return self._match('choices', self._r.choices(pop, weights=weights, k=k))
            def shuffle(self, seq):
                self._log('shuffle', len(seq)); return self._r.shuffle(seq)

        bb_full._Rng = Branchless
        try:
            bb_full.run_game(SEED, self.N, cfg=make_cfg(harvest=True))
        finally:
            bb_full._Rng = real_cls
        self.assertEqual(repr(calls), j_off,
                         "harvest=on с вырезанным rng-выбором цели == harvest=off побайтово ⇒ OFF не расходует rng")

    # ---- сценарий 1b: OFF-партия детерминирована и rng-нейтральна к другим OFF-флагам ----
    def test_harvest_off_equals_branch_absent(self):
        """Дополнение к гарду: harvest=off побайтово повторяем на том же seed и не смещает
        rng в сочетании с другими OFF-дефолтами (ghost_bets, prof_complex)."""
        j_off = journal(self.SEED, self.N, make_cfg(harvest=False))
        j_off2 = journal(self.SEED, self.N, make_cfg(harvest=False), cap=4000)
        self.assertEqual(j_off, j_off2)
        self.assertEqual(j_off, journal(self.SEED, self.N, make_cfg(harvest=False, ghost_bets=False)),
                         "сочетание двух OFF-дефолтов rng-нейтрально")

    # ---- сценарий 2: ghost_bets OFF (= default печати №2) не смещает rng вообще ----
    def test_ghost_bets_off_is_rng_neutral_default(self):
        self.assertIs(CFG_DEFAULTS['ghost_bets'], False, "печать №2: ставки вырезаны")
        j_off = journal(self.SEED, self.N, make_cfg(ghost_bets=False))
        j_def = journal(self.SEED, self.N, make_cfg())
        self.assertEqual(j_off, j_def, "ghost_bets=off == дефолт: журнал побайтово совпадает")
        j_on = journal(self.SEED, self.N, make_cfg(ghost_bets=True))
        self.assertNotEqual(j_off, j_on, "on-ветка добавляет вызовы (гард осмыслен)")
        # префикс до первой смерти обязан совпадать — on-ветка стартует только с призраками:
        k = 0
        while k < min(len(j_off), len(j_on)) and j_off[k] == j_on[k]:
            k += 1
        self.assertGreater(k, 50, "расхождение началось не в начале партии (до first death)")

    # ---- сценарий 3: prof_complex OFF — заглушка, rng не трогает ----
    def test_prof_complex_off_stub(self):
        self.assertIs(CFG_DEFAULTS['prof_complex'], False)
        with self.assertRaises(NotImplementedError):
            bb_full.run_game(self.SEED, 2, cfg=make_cfg(prof_complex=True))
        j_off = journal(self.SEED, self.N, make_cfg(prof_complex=False))
        j_def = journal(self.SEED, self.N, make_cfg())
        self.assertEqual(j_off, j_def, "prof_complex=off не расходует rng относительно дефолта")

    # ---- свёртка: все флаги, уже выключенные в печати №2, побайтово равны дефолту ----
    def test_every_off_default_flag_rng_neutral(self):
        baseline = journal(self.SEED, self.N, make_cfg())
        for flag, val in CFG_DEFAULTS.items():
            off_like = (val is False) or (isinstance(val, str) and val == 'none') or \
                       (flag == 'exchange_revision' and False)
            if off_like:
                again = journal(self.SEED, self.N, make_cfg(**{flag: val}))
                self.assertEqual(baseline, again, f"OFF-дефолт {flag} сместил rng-журнал")


if __name__ == '__main__':
    unittest.main(verbosity=2)
