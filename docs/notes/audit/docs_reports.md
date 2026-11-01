# Аудит: docs/reports/ — Сообщение 3, папка 5/8
Дата: 2026-11-02. Файлов: 9.

## Карточки
- sim_n_digest.md — структурный дайджест sim_n.py (создан в прошлом чате при переполнении контекста): SCHED всех ситуаций, FORCED_END={plane,tomato,pole,purg,amkary}, моды s_plus1/s_third/rpds_off/rpdi_extra/tokens2/revive5/mass_low/harvest_off/harvest_k/teny_off/obmen_off..., spec_bits legacy-тайминги, лимит 12 циклов/stall. УНИКАЛЬНО: семантика модов sim_n описана полнее, чем читается из кода (код подтверждает).
- sim8_digest.md — дайджест sim8: каталоги PROF_X PRX-01..14 с тегами, SPEC_X 16 механик, TENY_X 10, OBMEN_X 5, PROFILES 13 ключей (aggr hoard actor manip team turtle gambler chaos medic marauder star lurker neutral), PRESETS 8 (party meat coop intrigue survive newbie maxweird mixed), DISPUTE_P вероятности споров (crit_fail_kill .75 и т.д.). УНИКАЛЬНО: DISPUTE_P и PRESETS — только здесь+код.
- sweeps_digest.md — матрицы: sweep.py подбор зрелищной партии по SCORE; sweep_n base N2..20×240 сидов + ситуационные конфиги; sweep_mods 38×200; sweep8 65 конфигов (docstring устарел «58») ×N2..20×120 = 148 200 партий, СИД-ТРАНСФОРМАЦИЯ seed=s*7919+n*131 (важно для воспроизведения!); agg-метрики ячейки; time_model COST/HOSTED таблицы.
- src_test_digest.md — колодострой: build_v5 (вход final_v5.json → 10 txt категорий), censor_fix таблица замен (кат1:12, кат2:10, кат3:18...), check_clean контроль чистоты всего проекта, export_v5_xlsx, md2docx, audit_full сверка xlsx↔json, one_search движок formulas.
- report_generators_digest.md — make_dop_md/make_sim8_md: генераторы печатных отчётов из готовых json; точный список входов (sweep_n_results, sweep_mods_results, harvest_off_duration, dice_fairness chi2=13.0, verify_dop_results...). УНИКАЛЬНО: граф зависимостей отчётников.
- sim_8punk.txt [46 КБ], sim_dop_2_20.txt [44 КБ] — текстовые версии печатных приложений эпохи A (полные числа).
- verify_dop.txt [7 КБ] — КОД verify_dop.py (доп. проверки: честность кубика на базе, способы окончания, патты командного режима). Класс code, осиротел в reports — noted.
- sample_log_frag.txt — фрагмент лога формата эпохи A (цикл/призраки/ставки/раскрытие KN-095/d20=17 таблица В). УНИКАЛЬНО: эталон ФОРМАТА лога для парсера валидатора.

## РАСХОЖДЕНИЯ
- Числа дайджестов относятся к эпохе A (ред. 3.1) — при регрессии Сообщения 4 использовать их как ориентир архивной эпохи (base N8 end 4.2–4.3).
- verify_dop.txt назван txt, но это python-код — расхождение класса против manifest (unknown→docs при инвентаризации). Не трогать (переносы запрещены), отметить в AUDIT.md.

## РЕКОМЕНДАЦИИ
В БАЗУ знаний: все дайджесты (это внешняя память прошлых чатов, QWEN.md §о контексте). В архив: ничего. При сшивке: Sid-трансформация sweep8 обязательна к сохранению в матрицах новой эпохи.
