# STATE.md — рабочее состояние проекта БЛИЦ БОЙ (обновляется после каждого принятого этапа)

## Задача (текущее сообщение автора)
Реорганизация по Сообщению 1 + дополнения (архивы, CORE_THINK.md, раздел 12 в QWEN.md).

## Текущий шаг (обновлено 2026-11-02, Подшаг C завершается)
- ПРИНЯТО ранее: ШАГ А инвентаризация (409 файлов), scan_archives (19 архивов), reorganize боевой прогон,
  коммиты «reorg: initial structure», «reorg: layouts per author».
- Подшаг A: reorganize.py исправлен (существование путей), боёвой прогон, манифесты пересозданы. DONE.
- Подшаг B: archive_extract выполнен (extracted 58, duplicate_skipped 616, legacy 18 файлов в game/legacy/);
  точечные раскладки: cardlife→_inbox, spec_raw→data/deck, v3→docs/rules, черновики v2/ред4.0КАНОН→docs/notes.
  Коммит «reorg: archives and layouts» = 62e0b1c. DONE.
- Подшаг C: C1 DONE — рабочий код game/ нет (ядро ещё не собрано, это ЭТАП 1); запускался legacy
  game/legacy/workspace.tar.gz/sim_n.py seed=1 N=8 variant=base, EXIT=0, лог game/results/run_seed1_n8.log,
  STATS end=2 deaths=4 alive=4 win=[2,5,7,8] harvests=0 nat1/nat20=true (одна партия, не среднее!).
  Для запуска восстановлен layout данных внутри legacy-папки (src/final_v5.json, sim/pool_indices.json — копии с тем же md5, move_log дополнен).
  C2 DONE — CORE_THINK.md создан, раздел 12 добавлен в QWEN.md в конце файла (правка санкционирована явно).
  C3 — этот файл обновлён, коммит «reorg: complete».

## Следующий шаг
Жду «принято» по реорганизации. После приёмки — Сообщение 3: ПОЛНЫЙ АУДИТ ЗНАНИЙ по папкам
(game/ + legacy → data/deck → data/results → docs/rules → docs/reports → docs/notes → _inbox → _archive выборочно),
заметки в docs/notes/audit/, финал AUDIT.md + один вопрос.

## Ключевые числа
- Корень до реорганизации: 176 записей верхнего уровня, 409 файлов всего, 134 МБ.
- Дубликат-групп 120, к удалению 145 (правило keep: без суффикса (n) + наибольший mtime).
- Ориентиры симуляций (QWEN.md §7): архивная эпоха base N8 end 4.2–4.3; новая эпоха base N8 end 4.76 CI[4.41–5.11].
