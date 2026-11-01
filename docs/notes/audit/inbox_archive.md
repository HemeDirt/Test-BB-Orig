# Аудит: _inbox/ + _archive/ (выборочно по manifest_archives.json) — Сообщение 3, папки 7–8/8
Дата: 2026-11-02.

## _inbox/ (2 файла)
- SPEC_cardlife.md [4.7 КБ] — спецификация «ЖИВАЯ КАРТА» (отложено автором B24 2026-10-16, статус «пока офф»): карты живут вне хода в рамках цикла; флаг cardlife OFF; ОТРАТ/ПУСТО из руки в ответ на вредный акт; СПАС гасит удар по союзнику (первый потребитель флага save_ally — в каноне у СПАС нет потребителя!); слой mood = per-card ценность × per-archetype × угроза; леджеры cardlife_watch/play/decline/gate_blocked; обвязка: 72-й шаблон парсера, CFG_KEYS+BOOL_KEYS, fuzz TOGGLES и пр. УНИКАЛЬНО: единственный текст этой механики; НЕ переносить в базу без решения автора.
- zadanie_sim.txt [28 КБ] — не копия SPEC.md (md5 f091f56e ≠ d9ec7d9e); черновик задания симуляции; ждёт решения автора (в _inbox по его слову).

## _archive/: что вскрыл manifest + прямой просмотр
### Знания вне reach извлечения (важно!)
1. RAR-архивы (docs.rar, main_backup.rar, site_live.rar, site_v9_final.rar, site_v11.rar) — status unrar_unavailable: содержимое НЕ просканировано и НЕ извлечено. В КОНТЕКСТ_БРИФ §11 и game/legacy/Test-BB-site докстринге прямо сказано: архетипы ботов «пересажены из клада main_backup: bb_full.py + патчи B21/B22/B25». Значит main_backup.rar содержит ЭТАЛОННУЮ версию bb_full с полными личностями. УСТАНОВКА rarfile/unrar = уровень 3 — вопрос автору.
2. _archive/old_engine/ — ЦЕЛИЙ СЛОЙ ЭПОХИ B, не извлекавшийся (папка, не архив): bb_full.py (полная игра печати №2: личности ARCH, профессии/спец/тени/обмен полностью, домовые трактовки помечены #HOUSE — золотой источник для SPEC_CONSOLIDATED!) + 16 patch_bXX.py = история роста ядра: b11, b13_snap (снимки), b14_blindguard/events (слепые убийства), b15_handlimit/b/c (потолок руки, канон None), b16_draft (драфт раскрытых, HOUSE default off), b17_deadstop, b18_trio, b21_reputation, b21b_agentrevive, b22_tilt, b23_reserve/b23b_reservegate, b25_grudge (месть). Каждый патч = описание конфига+дефолта → готовая документация флагов. РЕКОМЕНДАЦИЯ: при синтезе включить bb_full.py как референс #HOUSE-пометок; патчи оставить в _archive (справочник).
3. _archive/data_old/ — ЧИСЛА НОВОЙ ЭПОХИ сверх скопированных: batch_100.json (100 партий: median end 4.0, harvest_rate 0.8, revive 0.17, first_death_dist{2:92,1:8}), matrix_b7.json (sit_base end [4.76,4.41,5.11], p90 7, harvest 70%, revive 35% — ОРИЕНТИР регрессии Сообщения 4 дословно здесь), grudge.json (1500 партий, arms OFF/DECAY/WINDOW/DECAY+REP/WINDOW+REP × N8/12/16), nsweep_current.json (N4 2.91 … N20 9.86), handlimit.json, matrix_abl.json (абляция систем!), matrix_sits_ro.json, batch_canon24.json, pendulum/reputation/reserve/tilt/tornado/winrate/witness_seeds (дубли текущих game/results — md5 сверить), карты_настолка_v4.xlsx (дубль v4).
4. _archive/experiments/log_showcase.txt — «зрелищная» партия, подобранная sweep.py под SCORE (кандидат в ПРИМЕР лога).
5. _archive/viewer_old/*.html — HTML-вьюера конкретных сидов (grudge, reserve, tilt, draft, traitor, handlimit7, plane, tornado) — артефакты эпохи B, знания в параметрах заголовков имён.
6. _archive/src_extra/*.js, other/*index*.html, site-зипы — веб-мусор (класс web_junk), знаний нет.
### Дубли-группы манифеста
workspace.tar ≡ workspace.tar.gz (оба дают те же 62 knowledge-записи; извлечение сделано один раз, дубль помечен duplicate_skipped в move_log) — ок. Test-BB-revert zip лежит дважды (корень+dumps) — идентичны.

## ИТОГ по _archive
Знания, которых НЕТ в основных папках: bb_full.py+#HOUSE, 17 патчей истории флагов, grudge/matrix_abl/handlimit/batch_100/nsweep числа, log_showcase, вьюера-параметры, и НЕПРОСМОТРЕННОЕ в 5 rar. Всё остальное продублировано.
