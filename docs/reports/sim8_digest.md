# sim8.py — СТРУКТУРНЫЙ ДАЙДЖЕСТ (полный код остаётся в истории чата; на диск пишу сжатое изложение)
Роль: надстройка над sim/sim_n.py для «8 пунктов»; ядро правил не тронуто → base бит-в-бит = sim_n.
Импорт: game_sim as G (только данные POOLS, SPECS, TENY, OBMEN); pool_sim1000.json (обезличенные ID).
CLI: python3 sim8.py SEED N [VARIANT] [--quiet] ['{"мод":значение}']; в конце STATS={json}.

## Каталог механик (обезличенный)
PROF_X: PRX-01..14, теги: stealprof, order, speclock, reflect, drawcard, copyspec, idletax, forceswap, veto, safekill, healunlock, extralate, luck2, teamboth. PROF_X_PASSIVE: PRX-15..24 ('none').
SPEC_X (16): swap_hands, ghost_cycle, steal_prof, chaos_swap, reflect, duplicate, veto, reveal_all, debt, shield_ally, transfer, second_life, bounty, time_lock, hoard_bonus, double_turn. SPEC_CYCLE: {swap_hands:2, ghost_cycle:3, steal_prof:2, chaos_swap:4, reflect:3, duplicate:2, veto:3, reveal_all:2, debt:3, shield_ally:2, transfer:4, second_life:0, bounty:2, time_lock:3, hoard_bonus:2, double_turn:4}; legacy-теги: additem2, extra3, immune3, lootdead3+, fullheal4, avoid4, revive5+, autohit5.
TENY_X (10): mass_reveal, token_tax, curse, swap_or, fake_death, silence, harvest_x2, ghost_king, hand_lock, reroll_bad. Legacy-теги карт мёртвых: knock, cold, name, cancel, buff, mirror, eyes, dark, fake, voice, pain, photo, queue; ONCE_TAGS=(cancel,eyes,fake,voice,photo).
OBMEN_X (5): Сделка, Сбор, Щит, Перевод, Торг (тратят неиспользованное РПД). Legacy-обмен: Парамедик, Отмена, Взятка(не юзается), Заначка, Обмен, Второе дыхание, Свидетель, Подстава; вероятности применения 0.8/0.75/0.45/0.55 × obmen_p профиля.
PROFILES (13 ключей = 12 типов + neutral): aggr, hoard, actor, manip, team, turtle, gambler, chaos, medic, marauder, star, lurker, neutral. Поля: w (поправки весов РПДИ), think/narrate/chatter/dispute (множители времени), spec_p, prof_p, obmen_p, target, флаги hoard/bet.
PRESETS (8): party, meat, coop, intrigue, survive, newbie, maxweird, mixed (списки профилей).
DISPUTE_P: crit_fail_kill .75, crit_kill .55, avoid_death .85, cascade .70, veto .80, cancel .70, mass_fail .45, steal_fail .40, humiliate_fail .35, forced_reveal .30, harvest .35, revive .60, weird .50, spec .35, ghost .25, immunity .45, reflect .60, swap .40, prof .25, death .30, vote .45, bounty .30. Споры = матожидание (событие×p×dispute профиля), БЕЗ доп. бросков → воспроизводимость не ломается.
Legacy-профессии: активные 8 (Почтальон+1 карта ИНВЕНТАРЬ, Стример, Водитель, Вор 3 кражи, Медик, Крупье переброс 0.55 при roll<10 раз/цикл, Шизик, Каскадёр перехват 0.4), пассивные 12.

## Ситуации (SCHED: cycle→(раскрытий,РПДС,РПДИ))
base {1:(2,1,1),2:(1,1,1)}; новые: fog{1:(0,2,1)}, timer{6 циклов, раскрытия падают, S−1/цикл}, bounty, silent, plague, market{1:(1,2,1)}, arena{1:(1,0,2)}, conclave, heirloom, duel; legacy: plane, tomato, pole, purg, amkary, amkary2, hrono. FORCED_END={plane,tomato,pole,purg,amkary,timer} (конец 5-го цикла: случайные смерти лишних сверх порога). TEAMVARS={amkary,amkary2} (team=i%2). VNAME — русские названия («Ночь в панельке», «Амкары и Касторама», «Пьяная хронология» и т.д.).

## Числовые ядра механик
S=⌊n/2⌋; tomato/pole при n∈{3,4} → S=2; purg: W=randint(1,n) («мест в раю»). dth=3 (мод dth). draft=1 (мод draft). nspec=1/2/3 (spec2/spec3). teny_k=2..3 карты мёртвых за цикл.
Таблица А УБИЙСТВО: eff≤4 крит-провал (смерть автора через check_death), ≤8 автор+1ОР, ≤12 ничего, ≤16 цель+2ОР, 17+ крит: цель выбывает. РАНЕНИЕ: ≤4 автор+2, ≤8 автор+1, ≤12 ничего, ≤16 цель+1, 17+ цель+2.
Таблица Б: успех = nat20 или (nat≠1 и eff≥15); провал = nat1 или eff≤10; 11–14 ничего.
Таблица В: успех = nat20 или (nat≠1 и eff≥11); провал = nat1 или eff≤9; 10 ничего.
Массовое: 2 цели, порог 18 (mass_low→15), успех = каждой +1ОР, провал = автору +2ОР.
mod_roll: +buff(карта мёртвых), −curse, +luck2, −1 в dark (рпди/mass); nat1→eff=1, nat20→eff=20 (отмена модификаторов).
Смерть: spec_armed(avoid) → ОР=2 и не смерть (не для жатвы); second_life → ОР=1 + debuff(−1 РПДИ); heirloom → закрытые карты убитого убийце.
Призраки: +1 жетон/цикл (tokens2→2); ставки p=0.85, веса [1,5,2] при живых≥6 иначе [2,4,2], ставка 1–2, выплата ×2; магазин: 1 жетон подсмотреть (0.4), 2 жетона принуд. раскрытие (0.25); воскрешение с цикла≥4: общак жетонов ≥ цены 6 (revive5/revive_cost→5) И (Медик живой ИЛИ 0.5), котёл обнуляется, возврат с 0 ОР; ghost_king: вето на воскрешение.
Жатва: c≥2, player_death=False, живых≥2, k=harvest_k (harvest_x2 удваивает), не при harvest_off.
Средовые: pole c2–4 случайный +1ОР («кромка»); hrono c2–4 ротация закрытых рук; plague c≥2 у каждого p=0.35 +1ОР; timer S−1 каждый цикл; conclave голосование: за≥половины → смерть-изгнание; duel пары d20, проигравший +1ОР; market +1 жетон/цикл, покупка карты p=0.5; bounty заказ: ранивший цель тянет карту.
amkary: 85% целей — чужая команда; team_win когда осталась 1 команда; amkary2: порог S не проверяется, игра до последней команды («на уничтожение»).

## Поведение и время
choose_rpdi: базовые веса по циклам c1..c5 (humiliate/wound/steal/skip/heal/kill/marauder/mass) + поправки профиля w + проф-бонусы (Вор +15 steal, Медик +8 heal) + ограничения (arena: heal=0; silent: humiliate=0; no_steal; no_kill; collect_only обнуляет wound/kill/humiliate/mass и даёт collect+40).
Счётчики времени STATE['T'] (модель длительности): rolls, reveals, turns, think_u, narrate_u, chatter_u, disputes_e, discuss_e, cycles, breaks, specs, profs, ghost_cards, bets, bet_hits, shop, revives, immunity, wounds, mass_ok/fail, steal_ok/fail, humiliate_ok/fail, heal_ok/fail, selfheal_ok, collect, collect_fail, obmen, market, duel, vote, plague, timer_tick, veto, dups, weird, acted, act_wasted, skip_turns, table_a/b/v, crit_fail, crit_kill… T() не тратит ГСЧ.
Воспроизводимость: все расширения под гардами (weird/моды) и в выключенном состоянии НЕ расходуют rng (try_veto, prof_phase, spec_gate для neutral → без бросков).

## Вывод run_game
Лимит 12 циклов; stall = end≥12; no_win = живых 0. STATS: end, deaths, roll_dist, max_cycle_deaths, stall, alive, win, harvests, token_revive, spec_revive, avoid, bets_hit, mass, nat1, nat20, first_death, forced, team_win, rotations, field_deaths, S, W, S0, dth, nspec, teny_k, T, spec_uses, prof_uses, ghost_uses, obmen_uses, collect_total, weird_events, reflects, second_lives, hoard_cards, votes, duels, market_buys, plagues, expels, vetoes, dups, timer_ticks, cards_gained/lost, prof_agg (агрегаты по профилям: n/alive/kills/or_sum/gained/lost/specs/profs/collect/obmen/wasted/tokens/revived), seats (построчно).

## Расхождения/пометки
- docstring говорит «12 типов» профилей, в PROFILES 13 ключей (12 типов + neutral) — neutral = базовое поведение без доп. бросков.
- Каталоги сходятся с отчётом: 14 PRX, 16 спецкарт, 10 теней, 5 обменных.
- Для запуска нужны game_sim.py (данные колоды) и pool_sim1000.json — обоих у меня ещё нет.
