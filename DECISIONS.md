# DECISIONS.md — журнал решений проекта БЛИЦ БОЙ

| дата | решение | источник/пометка |
|---|---|---|
| 2026-11-02 | QWEN.md = git mv из QWEN_MD_ПРАВИЛА_ПРОЕКТА.md | прямое слово автора |
| 2026-11-02 | SPEC.md = git mv из ЗАДАНИЕ_НА_СИМУЛЯЦИЮ_ББ.md | прямое слово автора |
| 2026-11-02 | SPEC_cardlife.md и cardlife-файлы → _inbox/, spec_raw.txt → data/deck/ без смены имени | прямое слово автора |
| 2026-11-02 | ПРАВИЛА_БЛИЦ_БОЙ_v3 (md/docx без суффиксов) → docs/rules/ как канон печати; v2/ред4.0/КАНОН/черновики → docs/notes/ | прямое слово автора |
| 2026-11-02 | Архивы не удалять никогда; извлекать только code/deck_data/sim_results/docs_*/logs; дубли по md5 с репозиторием не извлекать (duplicate_skipped) | прямое слово автора, доп. 2.3–2.5 |
| 2026-11-02 | Код симуляции из архивов (sim/, bb_core, bb_full, game_sim, sim_n, sim8) → game/legacy/, не смешивать с текущим кодом | прямое слово автора, доп. 2.6 |
| 2026-11-02 | Delete только: пустые файлы и md5-дубли с суффиксом (n) при оригинале; всё сомнительное → archive/_archive | прямое слово автора, ШАГ В |
| 2026-11-02 | default applied: браузерный мусор @asamuzakjp/@bramus/@csstools и Crome bin and asa.zip (chrome binaries, 1754 записи web) считаются web_junk и НЕ извлекаются из архива; сами перемещаются в _archive/web_junk | правило «не извлекать веб-мусор», автором не оговорено явно |
| 2026-11-02 | default applied: папки site_live, site_live.rar содержимое, main_backup, web_old, viewer_old, src_extra, ws, blitz1.1, dumps, other, old_tests, old_engine, workflows, pages_index.html и т.п. переносятся целиком в _archive с подпапками; ничего не удаляется сверх критериев delete | уровень 1 «перемещать по таблице» + «всё сомнительное в archive» |
| 2026-11-02 | default applied: rules_print_v3.txt/rules_v3.txt/rules_short.txt/zadanie_sim.txt/situations.md/spec_raw.txt/ryukzak_raw.txt/telo_raw.txt/*_raw.txt → data/deck/ и docs/rules/ по признаку содержимого (транскрипции карт и правил) | чтение первых строк подтвердило транскрипции колоды |
| 2026-11-02 | default applied: digest-файлы (sim8_digest.md, sim_n_digest.md, sweeps_digest.md, src_test_digest.md, report_generators_digest.md) → docs/reports/ (выжимки прогонов) | имя+содержимое |
| 2026-11-02 | CORE_THINK.md создан в корне, добавлен раздел 12 в QWEN.md | явное разрешение автора на эту одну правку QWEN.md |
| 2026-11-02 | default applied: извлечение из архивов делает отдельный tools/archive_extract.py (после переносов); сим-код кладёт в game/legacy/<имя_архива>/, прочий код — game/legacy/tools/; дубли по md5 и по имени — duplicate_skipped | выполнение доп. 2.3–2.6; dry-run: extracted 58, duplicate_skipped 616, legacy-файлов 18 |
| 2026-11-02 | default applied: workspace.tar и workspace.tar.gz идентичны по содержимому — второй не извлекается повторно (seen-md5), записи Test-BB-revert zip с суффиксом "(1)" складываются в ту же папку legacy без коллизий имён | наблюдение при dry-run |
