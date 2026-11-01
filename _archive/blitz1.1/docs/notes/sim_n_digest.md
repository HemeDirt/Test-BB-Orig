# sim_n.py — ДАЙДЖЕСТ (sim/sim_n.py, 36 503 байт в архиве; получен вставкой в чат)
Роль: обобщённый симулятор N=2..20, ситуации и МОДЫ; «механики идентичны game_sim.py (редакция правил 3.1), лог компактнее». Ядро, с которым sim8 сверяется бит-в-бит. Данные: import game_sim as G (POOLS, SPECS, TENY, OBMEN).
CLI: sim_n.py SEED N [VARIANT] [--quiet] ['{моды}']; в конце STATS={json}.
VARIANT: base | plane | tomato | pole | purg | amkary | amkary2 | hrono.
SCHED (cycle→(раскрытий,РПДС,РПДИ)): base {1:(2,1,1),2:(1,1,1)}; plane {1:(1,1,0),2:(2,1,1),3:(3,1,1),4:(0,0,1),5:(1,0,1)}; tomato {1:(2,1,0)...}; pole {1:(3,1,0)...}; purg {1:(3,0,1),3:(1,1,2)...}; amkary/amkary2 {1:(2,1,0),2:(2,1,1),3:(2,1,1),4:(0,0,1),5:(1,1,1)}; hrono {1:(2,0,2),4:(2,1,2),5:(1,1,2)}.
FORCED_END={plane,tomato,pole,purg,amkary} (финал 5-го цикла: случайные смерти лишних сверх порога). VNAME — названия ситуаций.
Моды (словарём в argv): s_plus1, s_third, rpds_off, rpdi_extra, tokens2, revive5, mass_low, harvest_off, harvest_k, teny_off, obmen_off, bets_off, healcap_off.
setup: профессии PROF_ALL (8 активных+12 пассивных) ШАФЛЯТСЯ (в game_sim — по местам), specs/obmen шафлятся; team=i%2 для amkary*; S=⌊n/2⌋, tomato/pole n∈{3,4}→S=2, s_plus1 +1, s_third ⌊n/3⌋; purg: W=randint(1,n); Почтальон +1 ИНВЕНТАРЬ.
Механики = game_sim: таблицы А/Б/В те же полосы; Крупье 0.55 при roll<10; Каскадёр 0.4; призраки (+1 жетон, tokens2→2; ставки; магазин; воскрешение с c≥4 за 6/5); Жатва c≥2 тихий цикл (harvest_k жертв); pole: c2–4 случайный +1 ОР «кромка»; hrono: ротация рук c2–4; amkary2: порог S не проверяется до последней команды.
spec_bits: legacy-тайминги спецкарт (additem c2, extra c3, immune c3 0.8, lootdead c≥3, fullheal c4, avoid c4, revive c≥5, autohit c≥5).
choose_rpdi: те же базовые веса по циклам, что game_sim/sim8.
Лимит 12 циклов; stall=end≥12; no_win=живых 0.
STATS: end, deaths, roll_dist, max_cycle_deaths, no_win, stall, alive, win, harvests, token_revive, spec_revive, avoid, bets_hit, mass, nat1, nat20, first_death, forced, team_win, rotations, field_deaths, S, W.
Отличия от sim8: нет профилей/времени T/weird-каталогов/ситуаций исследования; sim8 = sim_n + гарды-расширения. Отличия от game_sim: N произвольное, профессии шафлятся, есть моды и ситуации, нет имён/SCORE.
