# STATE.md — рабочее состояние проекта БЛИЦ БОЙ (обновляется после каждого принятого этапа)

## Задача (текущее сообщение автора)
Реорганизация по Сообщению 1 + дополнения (архивы, CORE_THINK.md, раздел 12 в QWEN.md).

## Текущий шаг
- ШАГ А: inventory.py написан и запущен → data/manifest.json/csv, duplicates.json, classes.json.
  Сводка: файлов всего 409; классы: code 56, deck_data 3, sim_results 21, docs_rules 35,
  docs_reports 11, logs 2, web_junk 39, zip_archives 12, duplicates 145, unknown 85.
- Дополнение 2: scan_archives.py написан и запущен → data/manifest_archives.json.
  workspace.tar.gz содержит sim/ (game_sim.py, sim8.py, sim_n.py, sweep*.py, time_model.py) и v5/final колоды — извлечь в game/legacy/ и data/deck/.
  rar (7 шт.) — status unrar_unavailable (нет unrar), это не ошибка.
- ШАГ Б: unknown прочитаны выборочно; правила сортировки зафиксированы ниже.
- ШАГ В: переносы ещё НЕ выполнены. move_log.csv пустой.

## Следующий шаг
1. Написать tools/reorganize.py (батч-переносы по таблице классов+правил, move_log.csv, delete/archive критерии, извлечение архивов code/deck_data/sim_results/docs_*/logs без дублей по md5).
2. Выполнить git mv канонических файлов: QWEN_MD_ПРАВИЛА_ПРОЕКТА.md→QWEN.md, ЗАДАНИЕ_НА_СИМУЛЯЦИЮ_ББ.md→SPEC.md.
3. Пересоздать манифест, вывести дерево, README.md, коммит "reorg: initial structure".
4. ШАГ Е: прогон bbsim.py сид 1 N=8 (проверить запуск; код не править).

## Ключевые числа
- Корень до реорганизации: 176 записей верхнего уровня, 409 файлов всего, 134 МБ.
- Дубликат-групп 120, к удалению 145 (правило keep: без суффикса (n) + наибольший mtime).
- Ориентиры симуляций (QWEN.md §7): архивная эпоха base N8 end 4.2–4.3; новая эпоха base N8 end 4.76 CI[4.41–5.11].
