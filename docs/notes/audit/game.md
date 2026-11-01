# Аудит: game/ (включая game/legacy/) — Сообщение 3, папка 1/8
Дата: 2026-11-02. Файлов в папке: 62 (py 39, json 20, log 1, txt 1, pyc 1). Режим: только чтение.

## Иерархия эпох кода (установлено по докстрингам и импортам)
- ЭПОХА A (архивная, «редакция правил 3.1», колода v5 + бытовой фильтр):
  workspace.tar.gz/game_sim.py (данные+движок 8 игроков) → sim_n.py (N=2..20, варианты ситуаций) → sim8.py (расширения: пул sim1000, профили, 10 новых ситуаций, счётчики T) → sweep*.py (матрицы), time_model.py (длительность), build_pool1000.py, dice_fairness/dice_dist (тесты кубика).
- ЭПОХA B («реестровая сборка», параметризованное ядро): Test-BB-revert-4.../bb_core (1).py (D20/D6 как данные, таблицы полосами) + game_sim.py; tools/bb (1).py = CLI №17 поверх ядра B11 с реестром флагов; bb_events/bb_model/bb_html (вьюер №21); coverage_test, fuzz_test, csv_export, audit_full, verify_any.
- Текущая рабочая копия в game/: game_sim_before_personality.py (прообраз без личностей ботов), validate.py, test_effects.py, tornado_report.py, xpeek.py.

## Карточки файлов (главное)
### game/ (корень папки)
- game_sim_before_personality.py [49 КБ, код] — честный симулятор 8 игроков, ред. колоды 5, play_game(seed) единой точкой входа, SCORE-строка параметров партии. УНИКАЛЬНО: состояние ядра ДО пересадки архетипов (база для сравнения «личности vs без»). Расхождение с каноном №2: не проверялось пока против SPEC.md (ситуации/таблицы читать далее при сверке). Рекомендация: В БАЗУ как кандидат ядра эпохи A/B-гибрид.
- validate.py [2.3 КБ] — наблюдатель-валидатор инвариантов по логу+состоянию (rev/spec/prof счётчики, циклы). Импортирует bb_full (отсутствует в game/ — разорван на осиротевший импорт эпохи B). Рекомендация: В БАЗУ (ЭТАП 1 требует валидатор), восстановить импорт на новый модуль ядра.
- test_effects.py [16.7 КБ] — юнит-тесты веток механик на СИДАХ-СВИДЕТЕЛЯХ (witness_seeds.json). УНИКАЛЬНО: таблица свидетелей «минимальный сид, гарантированно включающий ветку». Рекомендация: В БАЗУ (фазз/регression).
- tornado_report.py [21.7 КБ] — отчёт карты чувствительности: парные прогоны, дельта-метод, |t|<2 = шум. УНИКАЛЬНО: методология парных сидов + SVG. Рекомендация: В ОТЧЁТНИКИ (уровень 2 позже).
- xpeek.py [0.4 КБ] — сниппет просмотра xlsx (openpyxl). Знаний нет. Рекомендация: В АРХИВ/tools-мелочь.
- results/*.json (20 файлов) — числа обеих эпох: plane100_b5 (end/deaths/causes/acts), sweep8_results (2.3 МБ, матрица 58 конфигов×N2..20×120 сидов), time_results (модель длительности), tornado_n8/n12 (парные дельты), reputation, tilt, reserve, pendulum, winrate, from_archive/* (dice_dist(2), final_v5(1), pool_indices(1) — ДУБЛИ по md5, см. ниже), run_seed1_n8.log (доказательный прогон C1). Рекомендация: В БАЗУ как ориентеры калибровки; dубли из from_archive — в список удаления на уровне 3.
- __pycache__/game_sim.cpython-312.pyc — мусор. Рекомендация: удалить (уже вне git? проверить).

### game/legacy/workspace.tar.gz/ (эпоха A)
- game_sim.py — источник данных POOLS/SPECS/TENY/OBMEN + движок; читает src/final_v5.json и sim/pool_indices.json (layout восстановлен копиями).
- sim_n.py — N=2..20, SCHED ситуаций base/plane/tomato/pole/purg/amkary/hrono; STATS=json. УНИКАЛЬНО: расписания раскрытий/РПДС/РПДИ по циклам, forced-финал hrono.
- sim8.py [88 КБ] — надстройка: pool='sim1000' обезличенный; weird-каталоги; spec2/spec3; teny_k; 12 профилей поведения; collect; 10 новых ситуаций (fog timer bounty silent plague market arena conclave heirloom duel...); STATE['T'] счётчики. УНИКАЛЬНО: всё это одним файлом.
- sweep8.py — матрица 58 конфиг×N×120 сидов; sweep_mods/sweep_n/sweep.py — меньшие матрицы.
- time_model.py — модель реальной длительности (калибровка: базовая N8 host=1.0 = 60 мин). УНИКАЛЬНО только здесь.
- build_pool1000.py — генератор обезличенного пула; pool_sim1000.json [130 КБ], src/final_v5.json [200 КБ], sim/pool_indices.json — ДАННЫЕ (источник истины колоды уже продублирован в data/deck/ при извлечении; сверить md5 на шаге AUDIT).
- dice_fairness.json / dice_fair_base.json / (dice_dist в results/from_archive) — тесты честности d20 (chi2, min/max face). УНИКАЛЬНО.
- make_dop_md.py / make_sim8_md.py — генераторы печатных приложений (49/45 КБ). make_web.py — веб-выдох.
- log_360.txt [36 КБ] — лог живой/длинной партии 360? (класс logs, keep по Сообщению 1).

### game/legacy/Test-BB-revert-4-game-file-analysis-b3311/ (эпоха B, этап B1)
- "bb_core (1).py" — ПАРАМЕТРИЗОВАННОЕ ЯДРО: грани/полосы таблиц как данные, D6=конфиг не отдельный код; пороги ОР, Жатва, экономика призраков, расписания — всё ключи. УНИКАЛЬНО: самая близкая к «ядро+флаги» архитектура под ЭТАП 1. Рекомендация: В БАЗУ как архитектурный образец.
- game_sim.py [48 КБ] — версия движка этапа B1 (карты-эффекты счётчиками).
### game/legacy/Test-BB-site/
- game_sim.py [59 КБ] — движок С ЛИЧНОСТЯМИ: ARCH 12 архетипов (aggr/help/neut/theat/thief/chaos векторы + шум ±30%), пересажен из клада main_backup (патчи B21/B22/B25). УНИКАЛЬНО: полный поведенческий слой в одном файле. Рекомендация: во ФЛАГ personality (по приоритету источников п.1.3 Сообщения 4).
### game/legacy/tools/ (эпоха B CLI-слой)
- "bb (1).py" [14.5 КБ] — CLI №17: play/batch(≤100)/matrix/events/view/csv; CFG_KEYS+BOOL_KEYS: blind_kill, queue_reverse, traitor, spec_cycle, escalation, pressure, or_noise, crit_price, pacifist_c1, random_outcome, revive_esc, draft, reputation, tilt, reserve*, fear, rpds/rpdi/lives, dice=D20|D6, ablate=..., harvest_mode=std|off_after_corpse|off_after_death|off|max2|quiet2|late. УНИКАЛЬНО: РЕЕСТР ФЛАГОВ — основа раздела 5 SPEC.md при сшивке.
- bb.py [8 КБ] — более ранняя автономная CLI (play/batch/html/deck) поверх game_sim эпохи A.
- "bb_events (1).py" — event-sourcing: parse_log 72 шаблона say(); каталог событий. УНИКАЛЬНО.
- "bb_model (1).py" — модель для вьюера: два прогона сида (лог+снимки), запись перемешиваний ГСЧ.
- "bb_html (1).py" [45 КБ] — HTML-вьюер №21 (веб-обёртка, но содержит карту событий).
- coverage_test (72 шаблона), fuzz_test (случайные конфиги × инварианты, TOGGLES-список), audit_full, verify_any, check_clean, censor/censor_fix/build_v5/build_canon_decks/export_v5_xlsx (колодостроительные), csv_export, md2docx, make_web, one_search, t2.
- "bb (1).py" и др. суффиксы (1) — имена-дубли из архивов; внутри НЕ идентичны безсуффиксным аналогам (размеры различаются) → не удалять молча.

## УНИКАЛЬНЫЕ активы папки (для AUDIT.md)
1) Реестр флагов эпохи B (bb (1).py) — единственный полный CFG/BOOL-словарь.
2) Параметрическое ядро bb_core (D6 как конфиг).
3) 12 архетипов ботов (Test-BB-site/game_sim.py) + 12 профилей sim8.py (разные наборы!).
4) Модель времени time_model.py + time_results.json.
5) Тесты кубика dice_fairness/dice_dist + chi2-числа.
6) Свидетели-сида test_effects/witness_seeds.json.
7) Парная дельта-методология tornado_report.py.
8) 10 новых ситуаций sim8 + forced-ситуации sim_n.
9) Обезличенный пул sim1000 (pool_sim1000.json + build_pool1000.py).

## РАСХОЖДЕНИЯ с каноном печати №2 (предварительно, полная сверка на синтезе)
- Эпоха A: урон/таблицы по ред. 3.1; ситуации SCHED жёстко зашиты — сверять с §4 QWEN.md.
- Эпоха B: harvest_mode off/off_after_* — режимы Жатвы сверх канона → только флаги.
- Личности/профили ботов — авторская переработка карт+РПД не трогать; флаги.
- [НЕ УВЕРЕН] game_sim_before_personality.py vs Test-BB-site/game_sim.py: какой новее — установить diff при сшивке.

## Дубли внутри game/, обнаруженные по md5 (в список на удаление, уровень 3)
- results/from_archive/final_v5 (1).json == src/final_v5.json; pool_indices (1).json == sim/pool_indices.json; dice_dist (2).json (оригинал искать в _archive манифесте).
- legacy/tools/bb.py ≠ "bb (1).py" (не дубль! разные эпохи).

## РЕКОМЕНДАЦИЯ ИТОГО
В базу архитектуры ЭТАПА 1: bb_core (параметрика) + реестр флагов bb (1).py + validate/test_effects/fuzz methodology. Во флаги: личности, профили, harvest_mode*, time_model, situations-extra, pool sim1000, D6. В отчётники: tornado_report, csv_export. Архив/мусор: xpeek.py, __pycache__, pyc.
