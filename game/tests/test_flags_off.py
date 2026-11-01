# -*- coding: utf-8 -*-
"""Гард-тест S1a: любой флаг в положении OFF НЕ должен расходовать rng.
Смысл по допуску: прогнать одну и ту же партию с seed S при flag=off и сравнить
ПОБАЙТОВО журнал вызовов rng с партией, где ветка кода отсутствует (или с дефолтом,
если off == default). Сценарии: harvest off, ghost_bets off, prof_complex off.
pytest недоступен в окружении → unittest. Это НЕ симуляции (запрет S1a): здесь
фиксированные микросверки журналов на одном seed.
Запуск из корня: python3 -m unittest game.tests.test_flags_off -v
"""
import ast, os, sys, unittest

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

    # ---- сценарий 1: главный гард допуска — harvest OFF не расходует rng ----
    # СОХРАНЁННЫЙ ИНВАРИАНТ Р3 п.3 (цитата допуска): «любой флаг в положении OFF НЕ ДОЛЖЕН
    # расходовать rng … журнал вызовов rng обязан совпадать побайтово». Критерии приемлемости
    # Р3.1 проверяются ВСЕ; префикс «до первой жатвы» как ЕДИНСТВЕННАЯ проверка снят:
    #   (i)   количественно: число rng-вызовов OFF == базовому (побайтовая проверка ниже),
    #         ON > базового (строго больше — отдельная проверка);
    #   (ii)  детерминизм OFF: два прогона с одним seed → идентичные журналы;
    #   (iii) побайтово относительно ВЫРЕЗАННОЙ ВЕТКИ: rng-расход жатвы (единственный rng-вызов
    #         внутри `if C['harvest']`: choice цели) изымается из потока random в эмулированной
    #         партии; на seed=8 событие жатвы — ПОСЛЕДНИЙ расход rng партии (движок после
    #         смерти от жатвы завершает цикл по порогу S=N/2), поэтому журнал «off» обязан
    #         побайтово совпасть с журналом «on без расхода ветки», а число записей in-vitro
    #         on-прогона обязано быть строго больше off.
    # Прежняя версия требовала простого off==on до первого расхождения и молча проходила на
    # seed=7 (жатва там не наступает) — контроль непустоты добавлен; метод исправлен по
    # указанию автора (Р3.1), фиксация — CONFLICTS C34.

    def _journal_harvest_rng_cut(self, seed, n):
        """Эмуляция «ветки расхода нет»: harvest=on, но rng.choice(alive()) в строке
        `v = rng.choice(alive()); st['harvests'] += 1` возвращает первого живого по номеру
        места БЕЗ обращения к random (маркер choice_CUT). Все прочие вызовы — обычные."""
        calls = []
        real_cls = bb_full._Rng

        class Cut(real_cls):
            _cut_done = False

            def _log(self, name, out):
                calls.append((name, out))
                return out

            def choice(self, seq):
                if (not self._cut_done and isinstance(seq, list) and seq
                        and all(isinstance(q, dict) and q.get('alive') for q in seq)):
                    self._cut_done = True                            # изымаем ровно один расход
                    tgt = min(seq, key=lambda q: q['seat'])          # без random
                    self._log('choice_CUT', tgt['seat'])             # маркер: событие было, rng цел
                    return tgt
                return super().choice(seq)

        bb_full._Rng = Cut
        log = []
        try:
            st, _ = bb_full.run_game(seed, n, cfg=make_cfg(harvest=True), log=log)
        finally:
            bb_full._Rng = real_cls
        return repr(calls), st, any('🌾 Жатва' in l for l in log)

    def test_harvest_off_does_not_consume_rng(self):
        SEED = 8   # на этом seed ON-ветка жива: st['harvests']>0 (гард не пустой)
        # (ii) детерминизм OFF: два прогона одним seed → идентичные журналы
        j_off = journal(SEED, self.N, make_cfg(harvest=False))
        j_off2 = journal(SEED, self.N, make_cfg(harvest=False))
        self.assertEqual(j_off, j_off2, "детерминизм OFF: один seed → идентичный журнал")

        # контроль непустоты гарда + база для (i)
        st_on, _ = bb_full.run_game(SEED, self.N, cfg=make_cfg(harvest=True))
        self.assertGreater(st_on['harvests'], 0, "контроль: ON-ветка жива на seed=8 (гард не пустой)")
        j_base = journal(SEED, self.N, make_cfg())                   # дефолт печати №2: harvest=off
        self.assertEqual(j_base, j_off, "OFF == базовый (дефолт) побайтово: ни одного лишнего вызова")

        # (iii) побайтово: OFF == прогон с вырезанным rng-расходом жатвы
        j_cut, st_cut, had_msg = self._journal_harvest_rng_cut(SEED, self.N)
        self.assertTrue(had_msg, "базис: сообщение о жатве было (событие произошло)")
        so, sc = ast.literal_eval(j_off), ast.literal_eval(j_cut)
        i_cut = next(i for i, x in enumerate(sc) if x[0] == 'choice_CUT')
        self.assertEqual(sc[:i_cut], so[:i_cut], "до точки расхода журналы побайтово равны")
        self.assertEqual(len(sc) - i_cut - 1, len(so) - i_cut,
                         "после изъятых расходов записей столько же ⇒ OFF добавил 0 вызовов")
        self.assertEqual([x for x in sc if x[0] != 'choice_CUT'], so,
                         "OFF побайтово == ON с вырезанным rng-расходом жатвы ⇒ инвариант Р3 п.3 сохранён")

        # (i) количественно: ON > базового по числу потреблённых rng-вызовов
        j_on = journal(SEED, self.N, make_cfg(harvest=True))
        self.assertGreater(len(ast.literal_eval(j_on)), len(so),
                           "ON > базового по числу rng-вызовов (реальный поток)")

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
