# make_dop_md.py и make_sim8_md.py — ДАЙДЖЕСТ (49 240 и 45 511 байт в архиве; получены вставкой в чат)
Роль обоих: собрать md-отчёты ИЗ УЖЕ ПОСЧИТАННЫХ json (никаких прогонов внутри). Текст отчётов = строковые литералы (совпадает с docx-версиями, которые у меня есть в extracted/).

## make_dop_md.py → ДОПОЛНЕНИЕ_СИМУЛЯЦИИ_2_20.md
Входы: sim/sweep_n_results.json (N), sweep_mods_results.json (M), harvest_off_duration.json (H), dice_fairness.json (F), verify_dop_results.json (V), event_freq.json (E).
Разделы 5–10. Таблица модов 5.2: ORDER-ключи base_n8, harvest_off_n8, harvest2_n8, rpdi2_n8, rpds_off_n8, s_plus1_n8, s_third_n8, healcap_off_n8, tokens2_n8, revive5_n8, mass_low_n8, obmen_off_n8, teny_off_n8, bets_off_n8, base_n12, s_third_n12, revive5_n12, mass_low_n12; поля M[key]: end_mean, deaths_mean, alive_mean, harvest_pct, revive_pct, mass_pct, bets_pct, blood_pct.
Раздел 6: H[base_N]/[harv_off_N]: end_mean, end_med, p90, mx, stall, deaths, rev; V['endings'] для контрольного stall.
Раздел 7: N[amkary_n12/16], M[amkary2_n8/12/16], V['team'][n] (end_max, teamwin_pct, stall_pct, stall_with_both_teams, stall_alive_mean), N[hrono_n8/16], V['rotation'].
Раздел 8: F: rolls, min_pct/max_pct, min_face/max_face, max_dev_pp, one_sd_pp, chi2 (13.0); N[base_nN].nat1_pct/nat20_pct; E.rolls_per_game.
Раздел 9: E['pct'] (crit_kill, critfail_kill, crit_wound2, fail_self2, croupier, cascade, mass, mass_fail, harvest, avoid, immune, revive_spec, revive_pool, bet_hit, spec_any, steal_empty), E.kills_per_game; V['endings'][n] (games, nowin_pct, blood3_pct), N[purg_n8/n12].forced_pct/nodeath_pct, N[base_n2].
Выводы-литералы = те же, что в extracted/sim_dop_2_20.txt (три рычага; Жатва-предохранитель; пат amkary2 26.3% @16; кубик честный; криты=рутина).

## make_sim8_md.py → СИМУЛЯЦИИ_8ПУНКТОВ.md
Входы: sweep8_results.json (SW['configs'][cfg]['by_n'][n]), time_results.json (TM: by_config, breakdowns, costs_scaled, calibration), report_numbers.json (RN: pool, p1_usage, p3/p3_base, p4, p4_hk_fix, p6_full, p7), sample_log_frag.txt (фрагмент лога в раздел 0).
NS_FULL=2..20, NS_MAIN=[2,4,6,8,10,12,15,20].
Разделы 0–8 + приложения А/Б. Модель времени (раздел 2): стоимости событий ~15 с рассказ, 14 раздумье, 3 бросок, 10 раскрытие, 26 спецкарта, 19 карта мёртвых, 47 спор, 60 перерыв, подготовка 130+19·N; профиль масштабирует think/narrate/chatter/dispute; ведущий fast 0.70 / norm 1.00 / slow 1.45; перекрытие (8/N)^0.9 при N>8; калибровка base@N8 = 60.0 мин (TM['calibration']['scale']); приложение Б = TM['costs_scaled'].
Ключи конфигураций: base, weird, weird_spec2, weird_max, spec2/spec3, tk2/tk3, pool1000, pool1k_weird, prof_all_weird, weird_s2tk2; моды п.3: escalation, dth2, dth4, draft2, spec_any, spec_hot, tokens2, harvest_off, rpdi_plus1, s_third, open_hands, collect, prof_all, weird_max; п.4: collect, hoard_all, collect_only + p4_hk_fix (Жатва ×1/×2/×3 @N12/15/20); п.5: 10 ситуаций (+*_weird); п.6: p6_full по 12 типам (mixed @N12); п.7: preset_* + mixed_weird (top/bottom выживание, disputes).
Выводы-литералы = те же 8 пунктов, что в extracted/sim_8punk.txt.
Значение файлов: доказательство воспроизводимости отчётов («каждая строка таблицы = ключ json») и точный словарь полей json-результатов (пригодится при вердикте для сверки цифр).
