# AUDIT.md — сводный аудит знаний проекта БЛИЦ БОЙ (Сообщение 3)
Дата: 2026-11-02. Детали — в docs/notes/audit/{game,data_deck,docs_rules,docs_reports,docs_notes,inbox_archive}.md.
Режим: только чтение; переносов и правок кода не делал.

## 1. Сводная таблица по папкам
| Папка | Файлов | Класс знания | Главное |
|---|---|---|---|
| game/ + legacy/ | 62 | код обеих эпох + результаты | sim_n/sim8/game_sim (эпоха A), bb_core/bb(1)/bb_events (эпоха B), validate/test_effects/tornado_report (инструменты), results/*.json (числа) |
| data/deck/ | 20 | колоды | 11 категорий txt (150 проф/200 спец/100 тени/21 обмен), pool_indices фильтр, xlsx v4/v5, КОЛОДА_ОБМЕНА.md |
| data/results/, data/live/ | 0 | пусто | живых партий для калибровки НЕТ в data |
| docs/rules/ | 22 | каноны | ПРАВИЛА_v3 ред.3.4 = печать №2 (норматив), situations.md с домовыми уточнениями, СПРАВОЧНИК (демон/конкурс d20), примеры партий, протокол |
| docs/reports/ | 9 | дайджесты | внешняя память чатов: семантика модов sim_n/sim8, матрицы sweep8 (65×19×120=148 200, seed=s*7919+n*131), граф отчётников, формат лога |
| docs/notes/ | 7 | хроника+черновики | КОНТЕКСТ_БРИФ (29 разделов: §16 Пьяная хронология РЕД2, §17 живая партия №1, §26 числа новой эпохи, §27 «ничего не подтверждено»), ред4.0, полный отчёт docx |
| _inbox/ | 2 | ждёт автора | SPEC_cardlife (отложено), zadanie_sim (не копия SPEC.md) |
| _archive/ | ~338 | слои вне reach | old_engine: bb_full.py(#HOUSE)+17 патчей b11–b25; data_old: matrix_b7/grudge/abl/batch_100/nsweep; log_showcase; 5 rar НЕ ПРОСМОТРЕНЫ (unrar_unavailable) |

## 2. Уникальные активы (обязательно учесть при синтезе)
1. Реестр флагов эпохи B: bb (1).py CFG_KEYS/BOOL_KEYS (blind_kill, queue_reverse, traitor, spec_cycle, escalation, pressure, or_noise, crit_price, pacifist_c1, random_outcome, revive_esc, draft, reputation, tilt, reserve*, fear, dice=D20|D6, ablate, harvest_mode=std|off_after_corpse|off_after_death|off|max2|quiet2|late).
2. bb_core.py — параметрическое ядро: таблицы полосами, D6 как конфиг. Основа архитектуры ЭТАПА 1.
3. bb_full.py (_archive/old_engine/) — полная игра печати №2 с личностями и пометками #HOUSE — золотой референс домовых трактовок.
4. 17 патчей patch_bXX — документированная история каждого флага с дефолтами (b15 hand_limit канон=None, b16 draft HOUSE default off и т.д.).
5. Поведенческие слои: ARCH 12 архетипов (Test-BB-site + bb_full), PROFILES 13 ключей + PRESETS 8 + DISPUTE_P (sim8).
6. Модель времени time_model.py + time_results.json + попадание предсказания в живую партию №1 (~40 мин @N5).
7. Тесты кубика: dice_fairness.json (chi2=13.0), dice_dist, verify_dop.txt (код).
8. Свидетели-сида веток механик: test_effects.py + witness_seeds.json.
9. Парная дельта-методология tornado_report.py (одинаковые сиды, |t|<2=шум).
10. Ориентиры регрессии: matrix_b7.json дословно end [4.76,4.41,5.11] base N8; архивные 4.2–4.3 (sweep8/sweep_n).
11. Обезличенный пул sim1000 + build_pool1000.py.
12. Ситуации: SCHED+FORCED_END (sim_n), 10 новых ситуаций (sim8), расшифровка 6 печатных + уточнения автора (situations.md, КОНТЕКСТ_БРИФ §14/§16).
13. Живые артефакты: log_360.txt, sample_log_frag.txt, log_showcase.txt, рассказ партии №1 (§17) — ядро калибровки, в data/live/ ничего нет.

## 3. Расхождения с каноном печати №2 (все → CONFLICTS.md, дефолт = печать)
R1. Колода симуляции ≠ запись печати: Судья удалён, +Стекольщик, +Таксидермист, спец 25 (+Отмена Жатвы), обмен повезет×9. Статус: ждёт автора (§27).
R2. Предел «Отмены Жатвы» (harvest off end 8.13 p90 15 — выключает предохранитель). Ждёт автора.
R3. W Чистилища: sim dN−2 vs печать dN. Ждёт автора.
R4. Порог Машины времени при N<10: код 10 vs рекомендация 15; §16 закрыл лишь «≥ требуемого» и сброс рук. Ждёт автора.
R5. Поле: архивное +1ОР в циклах 2–4 отсутствует на печати (situations.md помечает «уточнить»).
R6. Профессии: колода 150 карточек vs 8 активных+12 пассивных в коде эпохи A vs 26 в ревизии R1.
R7. Демон/Вторая личность: механика конкурса d20 есть только в СПРАВОЧНИКЕ; в коде эпох проверить наличие (#HOUSE в bb_full).
R8. verify_dop.txt — python-код в папке отчётов (классификация manifest расходится с фактом).
R9. final_v5.json/pool_sim1000.json живут в game/legacy, а не в data/deck (перенос = уровень 1 по таблице, но аудиторский запрет — заявлено автору).
R10. СИМУЛЯЦИИ_* лежат в docs/rules, хотя это отчёты (раскладка автора — принять как есть).
R11. Docstring sweep8 «58 конфигов» против факта 65 (число партий 148 200 верно).

## 4. Неопознанное / недоступное
- 5 RAR-архивов не просмотрены (нет unrar/rarfile; установка = уровень 3). main_backup.rar вероятностно содержит эталонный bb_full с личностями [ГИПОТЕЗА: подтверждается докстрингом Test-BB-site/game_sim.py и КОНТЕКСТ_БРИФ §11].
- cardlife-слой: реализован ли где-то код под флагом — не найдено нигде, кроме текста спеки; вероятно никогда не писался («нечего выключать») — так и зафиксировано.
- Происхождение rules_print_v3.txt (абзац про патигеймы) — [ГИПОТЕЗА] более ранний срез.
- Что новее: game_sim_before_personality.py или Test-BB-site/game_sim.py — установить diff'ом при сшивке.

## 5. Итоговая рекомендация по сборке эталона (мост в Сообщение 4)
База: bb_core параметрика + правила v3/3.4 + situations с уточнениями автора + состав data/deck.
Флаги (гард default OFF): все режимы из реестра bb(1) (harvest_mode*, blind_kill, queue_reverse, traitor, spec_cycle, escalation, pressure, draft, hand_limit, reputation, tilt, reserve*, fear), personality/profiles, time_model, extra-situations, pool sim1000, dice D6, print_rev2, time_machine_fix.
Инструменты: validate+bb_events(72 шаблона)+test_effects(witness)+fuzz+tornado_report+csv_export; матрицы с sid-трансформацией sweep8; отчётники make_*_md.
Регрессионные ориентиры: архив base N8 4.2–4.3; печать base N8 4.76 CI[4.41–5.11] (matrix_b7.json).
