# -*- coding: utf-8 -*-
"""B13 (п.21 меню): HTML-вьюер партии — одна самодостаточная страница (без сети и библиотек).

Что умеет страница:
  • лента событий по циклам (53 типа, все шаблоны ядра), поиск и фильтр по типам;
  • навигация по циклам: полосы, ←/→, автопрокрутка, «PLAY»;
  • места: карточки игроков (профессия, архетип, повестка, судьба, ОР/жетоны/жизни, счётчики),
    клик = фильтр ленты по месту;
  • панель места: стартовая рука, спецкарта, обменка по циклам, все его события;
  • графики (инлайн-SVG): живые/призраки по циклам, ОР по циклам, гистограмма кубика, причины смертей;
  • выезжающая панель с исходным логом (синхронно с текущим циклом).

Usage:
  import bb_model, bb_html
  m = bb_model.build_model(777, 8, 'plane')
  bb_html.write_page(m, 'game_777.html')
  bb_html.write_page_from_log(open('log.txt', encoding='utf-8').read().splitlines(), 'g.html')
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CAUSE_RU_LOG = None   # подставляется из bb_model в write_page_from_log

CSS = """
:root{--bg:#0e1116;--panel:#161b22;--panel2:#1c2330;--line:#28303c;--tx:#dde5ef;--mut:#8b98a9;
--acc:#f2b544;--dth:#f2736f;--har:#7ee081;--rev:#7fd4f2;--wou:#f2a05c;--rol:#b9a6f5;--card:#8fe3c8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial,sans-serif}
a{color:var(--acc)}
header{position:sticky;top:0;z-index:30;background:linear-gradient(180deg,#12171f,#0e1116);border-bottom:1px solid var(--line);padding:8px 14px}
h1{font-size:16px;margin:0 0 4px;letter-spacing:.6px}
h1 .sub{color:var(--mut);font-weight:400;font-size:12px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0}
.chip{background:var(--panel2);border:1px solid var(--line);border-radius:20px;padding:2px 9px;font-size:12px;color:var(--tx);white-space:nowrap}
.chip b{color:var(--acc);font-weight:600}
.chip.k{color:var(--mut)}
.ctrl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:6px}
button,.btn{background:var(--panel2);border:1px solid var(--line);color:var(--tx);border-radius:7px;padding:4px 10px;font-size:13px;cursor:pointer}
button:hover{border-color:var(--acc);color:#fff}
button.on{background:var(--acc);color:#14181f;border-color:var(--acc);font-weight:600}
input[type=text],select{background:#0b0e13;border:1px solid var(--line);color:var(--tx);border-radius:7px;padding:4px 8px;font-size:13px}
input[type=text]{min-width:190px}
.wrap{display:grid;grid-template-columns:310px minmax(0,1fr) 340px;gap:12px;padding:12px 14px 60px}
@media(max-width:1250px){.wrap{grid-template-columns:290px minmax(0,1fr)}.right{grid-column:1/-1}}
@media(max-width:860px){.wrap{grid-template-columns:minmax(0,1fr)}}
.col{min-width:0}
.block{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:12px}
.block h3{margin:0 0 8px;font-size:12px;letter-spacing:.9px;text-transform:uppercase;color:var(--mut);font-weight:600}
/* полосы циклов */
.strip{display:flex;gap:4px;overflow-x:auto;padding:6px 2px}
.cy{flex:0 0 auto;min-width:34px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;
padding:3px 5px;text-align:center;cursor:pointer;font-size:12px}
.cy b{display:block;font-size:13px}
.cy .mk{font-size:10px;letter-spacing:1px;min-height:12px;color:var(--mut)}
.cy:hover{border-color:var(--acc)}
.cy.cur{background:var(--acc);color:#14181f;border-color:var(--acc)}
.cy.cur .mk{color:#3d3220}
.cy .mk .d{color:var(--dth)}.cy.cur .mk .d{color:#7a1f1c}
/* лента */
.cyhead{display:flex;align-items:baseline;gap:10px;margin:16px 0 6px;padding:6px 10px;background:var(--panel2);
border-left:3px solid var(--acc);border-radius:6px}
.cyhead .n{font-weight:700;font-size:15px;color:var(--acc)}
.cyhead .st{color:var(--mut);font-size:12px}
.cyhead .dl{margin-left:auto;font-size:12px;color:var(--mut)}
ol.feed{list-style:none;margin:0;padding:0}
li.ev{display:grid;grid-template-columns:22px 1fr;gap:8px;padding:3px 8px;border-bottom:1px solid #1a2029;align-items:start}
li.ev:hover{background:#141a23}
li.ev .ic{text-align:center;font-size:13px;line-height:1.5}
li.ev .tx{min-width:0}
li.ev .who{display:inline-block;background:#20283a;border-radius:5px;padding:0 5px;margin-right:4px;font-size:11.5px;cursor:pointer;border:1px solid #2c3648}
li.ev .who:hover{border-color:var(--acc)}
li.ev .raw{color:var(--mut);font-size:11.5px;display:none}
body.showraw li.ev .raw{display:block}
li.ev.dth{background:rgba(242,115,111,.09);border-left:3px solid var(--dth)}
li.ev.har{background:rgba(126,224,129,.07);border-left:3px solid var(--har)}
li.ev.rev{background:rgba(127,212,242,.08);border-left:3px solid var(--rev)}
li.ev.wou{border-left:3px solid var(--wou)}
li.ev.rol{color:#c3b8e8}
li.ev.turn{background:#141a24;border-top:1px solid var(--line);margin-top:6px;padding:6px 8px}
li.ev.hid{display:none}
.turn .hd{font-weight:600}
.turn .tr{color:var(--mut);font-size:11.5px;margin-top:2px}
.turn .tag{display:inline-block;background:#222a3a;border-radius:5px;padding:0 5px;margin-right:4px;font-size:11px}
.turn .ag{color:var(--acc)}
mark{background:#5b4a12;color:#ffe9a8;border-radius:3px;padding:0 2px}
/* места */
.pc{display:grid;grid-template-columns:26px 1fr;gap:8px;padding:6px;border:1px solid var(--line);border-radius:9px;
margin-bottom:6px;cursor:pointer;background:var(--panel2)}
.pc:hover{border-color:var(--acc)}
.pc.sel{border-color:var(--acc);background:#22293a}
.pc.dead{opacity:.62}
.pc .no{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-weight:700;color:#12161d;font-size:12px}
.pc .nm{font-weight:600;font-size:13px}
.pc .pr{color:var(--mut);font-size:11.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pc .stat{display:flex;gap:6px;flex-wrap:wrap;margin-top:3px;font-size:11.5px}
.pc .stat span{background:#131922;border:1px solid var(--line);border-radius:5px;padding:0 5px}
.fate{font-size:11px;padding:0 6px;border-radius:20px;border:1px solid}
.fate.alive{color:#8fe3c8;border-color:#2c5a4c}
.fate.dead{color:#f2736f;border-color:#5c2b29}
.fate.limbo{color:#c9a0f5;border-color:#453261}
.orbar{height:5px;border-radius:3px;background:#232b38;overflow:hidden;margin-top:4px}
.orbar i{display:block;height:100%;background:linear-gradient(90deg,#f2a05c,#f2736f)}
/* панель места */
.kv{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;font-size:12.5px}
.kv .k{color:var(--mut)}
.hand{display:grid;gap:4px;margin-top:6px}
.hand .c{background:#131922;border:1px solid var(--line);border-radius:7px;padding:4px 7px;font-size:12px}
.hand .c i{color:var(--mut);font-style:normal;font-size:11px;display:block}
.hand .c.rev{border-color:#3d6a5c;background:#14211d}
/* графики */
svg{display:block;width:100%;height:auto}
.lgd{display:flex;flex-wrap:wrap;gap:8px;font-size:11.5px;color:var(--mut);margin-top:4px}
.lgd i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px}
.bar{display:grid;grid-template-columns:130px 1fr 34px;gap:6px;align-items:center;font-size:12px;margin-bottom:3px}
.bar .t{height:9px;background:#20283a;border-radius:5px;overflow:hidden}
.bar .t i{display:block;height:100%;background:var(--acc)}
.bar .v{text-align:right;color:var(--mut)}
.tf{display:flex;flex-wrap:wrap;gap:4px}
.tf button{font-size:11.5px;padding:2px 7px;border-radius:20px}
/* лог */
#logbox{display:none;position:fixed;inset:auto 0 0 0;height:52vh;background:#0b0e13;border-top:2px solid var(--acc);
z-index:40;overflow:auto;padding:8px 14px;font:12px/1.5 ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap}
#logbox .ln{color:#b9c4d2}
#logbox .ln.cur{background:#26303f;color:#fff}
#logbox .ln.d{color:#f2736f}
.foot{color:var(--mut);font-size:11.5px;padding:0 14px 24px}
.empty{color:var(--mut);padding:20px;text-align:center}
"""

JS = """
'use strict';
const D=window.__BB__;
function el(t,c,h){const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]))}
const P={};(D.players||[]).forEach(p=>P[p.seat]=p);
const SEATS=(D.players||[]).map(p=>p.seat);
function color(s){const p=P[s];return p?p.color:'#8b98a9'}
function who(arr){return (arr||[]).map(s=>'<span class="who" data-s="'+s+'" style="color:'+color(s)+';border-color:'+color(s)+'55">P'+s+'</span>').join('')}
function one(s){return s?who([s]):''}
function card(s){const c=D.cards||{};return c[s]?esc(c[s]):''}
function nm(s){return esc((s||'').split(' — ')[0])}
function fallback(e){const t=TM[e.type];if(t&&typeof t.r==='function'){const r=t.r(e);if(r&&String(r).trim())return r}return esc((e.raw||e.text||JSON.stringify(e)))}
function hl(t,q){if(!q)return t;try{return t.replace(new RegExp('('+q.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&')+')','gi'),'<mark>$1</mark>')}catch(e){return t}}

/* ---- каталог типов: иконка, метка, категория, окраска, рендер ---- */
const TM={
 cycle_start:{i:'🌀',l:'начало цикла',g:'структура',c:'cyc',r:e=>''},
 final:{i:'🏁',l:'итог партии',g:'структура',c:'dth',r:e=>'конец в цикле <b>'+e.end+'</b>, выжили '+who(e.surv)},
 turn_start:{i:'🧍',l:'ход игрока',g:'структура',c:'turn',r:e=>{
   const p=P[e.seat]||{};const t=[];
   t.push('<span class="tag">агр '+e.aggr+'</span><span class="tag">пом '+e.help+'</span><span class="tag">нейтр '+e.neut+'</span><span class="tag">кров '+e.blood+'</span>');
   if(e.fear!=null)t.push('<span class="tag">страх '+e.fear+'</span>');
   if(e.agenda)t.push('<span class="tag ag">повестка: '+esc((D.agenda_ru||{})[e.agenda]||e.agenda)+'</span>');
   return '<div class="hd">'+who([e.seat])+' ход — '+nm(p.prof||e.prof)+' <span class="raw">(ОР '+e['or']+', '+esc(p.arch_ru||'')+')</span></div><div class="tr">'+t.join('')+'</div>'}},
 skip:{i:'⏭',l:'пропуск хода',g:'структура',r:e=>one(e.seat)+'пропуск (лимбо/заморозка)'},
 limbo:{i:'⏸',l:'лимбо',g:'смерть',c:'rev',r:e=>one(e.seat)+'в лимбо ('+esc(e.kind)+')'},
 doll_idle:{i:'🧸',l:'чучело стоит',g:'профессии',r:e=>'чучело '+one(e.seat)+'стоит без действий (живой груз)'},
 reveal:{i:'🃏',l:'раскрытие карты',g:'карты',c:'card',r:e=>one(e.seat)+'раскрывает <b>['+esc(e.cat)+']</b> «'+esc(e.card)+'»'},
 lose_card:{i:'➖',l:'потеря карты',g:'карты',r:e=>one(e.seat)+'теряет собственную карту ['+esc(e.cat)+']'},
 hand_limit_burn:{i:'🔥',l:'лимит руки: сгорание',g:'карты',r:e=>one(e.seat)+'— рука полна, «'+esc(e.card)+'» сгорает'},
 draft_take:{i:'🃏',l:'драфт из пула',g:'карты',c:'card',r:e=>one(e.seat)+'забирает из пула <b>['+esc(e.cat)+']</b> «'+esc(e.card)+'» (РПДС-драфт)'},
 midturn_stop:{i:'⛔',l:'ход оборван смертью',g:'смерть',c:'dth',r:e=>one(e.seat)+'смерть посреди хода — оставшиеся РПД и обмен сгорают (B17)'},
 chronicler:{i:'📜',l:'летописец вскрывает',g:'профессии',r:e=>'летописец '+one(e.seat)+'вскрывает карту живого'},
 rpds:{i:'🎲',l:'РПДС (заявка)',g:'действия',r:e=>one(e.seat)+'РПДС «'+esc(e.kind)+'»'},
 roll:{i:'🎲',l:'бросок кубика',g:'действия',c:'rol',r:e=>'d'+(D.meta.faces||20)+'=<b>'+e.face+'</b> [таблица '+esc(e.table)+']'+(e.kind?' /'+esc(e.kind):'')+(e.res?' → '+esc(e.res):'')},
 mass_wound:{i:'💥',l:'массовое ранение',g:'действия',c:'wou',r:e=>one(e.seat)+'МАССОВОЕ РАНЕНИЕ по '+who(e.targets)+' d20='+e.face},
 mass_steal:{i:'🎒',l:'масс-кража',g:'действия',r:e=>one(e.seat)+'МАСС-КРАЖА по '+who(e.targets)+' d20='+e.face},
 mass_steal_fail:{i:'🎒',l:'провал масс-кражи',g:'действия',r:e=>'провал масс-кражи: '+one(e.seat)+'отдаёт '+e.cards+' карт'},
 wound:{i:'🩸',l:'ранение (+ОР)',g:'урон',c:'wou',r:e=>one(e.seat)+'<b>+'+e.amt+' ОР</b> → '+e.total},
 heal:{i:'❤️',l:'лечение (−ОР)',g:'урон',r:e=>one(e.seat)+'−'+e.amt+' ОР'},
 life_lost:{i:'💫',l:'потеря жизни',g:'смерть',c:'dth',r:e=>one(e.seat)+'теряет жизнь (осталось '+e.left+')'},
 survive_hit:{i:'🛡',l:'пережил удар',g:'урон',r:e=>one(e.seat)+'переживает удар (ОР='+e.or_+')'},
 beast_save:{i:'🐾',l:'автоспасение Твари',g:'профессии',r:e=>'Тварь '+one(e.seat)+'автоспасение, ОР='+e.or_},
 pressure:{i:'⚖️',l:'давление дуэли',g:'урон',c:'wou',r:e=>'давление дуэли: '+one(e.seat)+'+1 ОР'},
 death:{i:'💀',l:'смерть',g:'смерть',c:'dth',r:e=>one(e.seat)+'<b>умирает</b> ('+esc((D.cause_ru||{})[e.cause]||e.cause)+')'},
 harvest:{i:'🌾',l:'Жатва',g:'смерть',c:'har',r:e=>'Жатва забирает '+one(e.seat)},
 harvest_esc:{i:'🌾',l:'Жатва-эскалация',g:'смерть',c:'har',r:e=>'Жатва-эскалация (k='+e.k+'): '+one(e.seat)},
 harvest_leader:{i:'🌾',l:'Жатва по лидеру',g:'смерть',c:'har',r:e=>'Жатва-лидер: '+one(e.seat)},
 harvest_cancel:{i:'🚫',l:'Жатва отменена',g:'смерть',c:'har',r:e=>'Жатва отменена спецкартой '+one(e.seat)},
 revive_tokens:{i:'✝',l:'воскрешение за жетоны',g:'воскрешение',c:'rev',r:e=>one(e.seat)+'<b>восстаёт</b> за '+e.price+' жетонов'},
 revive_necro:{i:'✝',l:'воскрешение Некромантом',g:'воскрешение',c:'rev',r:e=>'Некромант '+one(e.seat)+'возвращает '+one(e.target)},
 revive_agent:{i:'🚌',l:'возврат Тур. Агентом',g:'воскрешение',c:'rev',r:e=>'Тур. Агент '+one(e.seat)+'оформил путёвку — '+one(e.target)+' возвращается'},
 reincarnate:{i:'☸',l:'реинкарнация Буддиста',g:'воскрешение',c:'rev',r:e=>'Буддист '+one(e.seat)+'авто-реинкарнация с новой рукой'},
 'return':{i:'↔',l:'возврат из изгнания/кика',g:'воскрешение',c:'rev',r:e=>one(e.seat)+'вернулся из '+esc(e.whence)},
 judged:{i:'⚖',l:'суд (выбит навсегда)',g:'смерть',c:'dth',r:e=>'суд: '+one(e.seat)+'выбит навсегда'},
 doll_made:{i:'🧸',l:'чучело из тела',g:'профессии',r:e=>'чучело из '+one(e.seat)+': место занято, владелец не воскреснет'},
 quota_fail:{i:'☠',l:'квота не выполнена',g:'смерть',c:'dth',r:e=>'квота не выполнена: '+one(e.seat)},
 spec:{i:'⚡',l:'спецкарта',g:'карты',r:e=>one(e.seat)+'спецкарта #'+e.idx+(e.name?' — «'+esc(e.name)+'»':'')},
 shadow:{i:'👻',l:'тень (действие мёртвого)',g:'карты',r:e=>one(e.seat)+'тень «'+esc(e.card)+'»'},
 exchange:{i:'🎴',l:'обмен объявлен',g:'карты',r:e=>one(e.seat)+'объявляет обмен «'+esc(e.card)+'» (РПД не тратились)'},
 prof_open:{i:'📖',l:'профессия открыта',g:'профессии',r:e=>one(e.seat)+'профессия открыта: '+esc(e.prof)},
 reflect_stance:{i:'🪞',l:'стойка отражения',g:'профессии',r:e=>one(e.seat)+'стойка отражения объявлена (публично)'},
 reflect:{i:'🪞',l:'отражение Стекольщика',g:'профессии',r:e=>'Стекольщик '+one(e.seat)+'отражение в '+one(e.to)},
 reflect_back:{i:'↩',l:'«обрат» вернул урон',g:'профессии',r:e=>one(e.seat)+'«обрат» возвращает урон'},
 shift:{i:'🔁',l:'Сменщик перевёл итог',g:'профессии',r:e=>'Сменщик '+one(e.seat)+'переводит итог на '+one(e.to)},
 lucky:{i:'🍀',l:'«повезёт» гасит',g:'профессии',r:e=>one(e.seat)+'«повезёт» гасит последствие'},
 for_fun:{i:'🎭',l:'действие по приколу',g:'профессии',r:e=>one(e.seat)+'действие по приколу (без нагрузки)'},
 tilt:{i:'↯',l:'тильт',g:'действия',c:'wou',r:e=>one(e.seat)+'тильт — '+esc(e.dir)+' (temper '+e.temper+', '+esc(e.src)+'), до ц.'+e.until},   // №12/B22
 reserve:{i:'🧊',l:'резерв РПД',g:'карты',c:'card',r:e=>one(e.seat)+'бережёт РПД ради обмена «'+esc(e.card)+'» (угроза '+e.threat+')'},   // №13/B23
 grudge:{i:'💢',l:'обида',g:'действия',c:'wou',r:e=>one(e.seat)+'обида на '+one(e.to)+' (сила '+e.force+') → месть'},   // №14/B25
 heal_void:{i:'🎭',l:'лечение вхолостую',g:'профессии',r:e=>one(e.seat)+'«лечение» вхолостую (скрытая повестка)'},
 anvil_miss:{i:'🔨',l:'наковальня не упала',g:'карты',r:e=>'наковальня не упала'},
 truth:{i:'📜',l:'истина Мудреца',g:'профессии',r:e=>'истина '+one(e.seat)+esc(e.eff)},
 one1:{i:'1️⃣',l:'Один-1 раздаёт эффекты',g:'профессии',r:e=>one(e.seat)+'Один-1 раздаёт эффекты (пропуск своих действий)'},
 deal:{i:'🤝',l:'сделка',g:'социум',r:e=>'сделка: '+one(e.a)+'↔ '+one(e.b)},
 link:{i:'💞',l:'связка',g:'социум',r:e=>'связка: '+one(e.a)+'↔ '+one(e.b)},
 betrayal:{i:'🗡',l:'предательство',g:'социум',c:'dth',r:e=>one(e.by)+'рвёт пакт с '+one(e.whom)},
 traitor_target:{i:'🗡',l:'предатель получил цель',g:'социум',r:e=>'предатель '+one(e.seat)+'новая цель: '+one(e.target)},
 traitors:{i:'🗡',l:'предатели объявлены',g:'социум',r:e=>'предатели '+who(e.who)+'с целями '+who(e.tgt)},
 kick:{i:'🗳',l:'кик',g:'социум',r:e=>'кик '+one(e.seat)},
 film:{i:'🎬',l:'ФИЛЬМ (роли)',g:'социум',r:e=>'ФИЛЬМ: герои '+who(e.heroes)+', злодеи '+who(e.villains)+', остальные второстепенные'},
 film_guard:{i:'🎬',l:'запрет убийства (ФИЛЬМ)',g:'социум',r:e=>'герой '+one(e.seat)+': убийство не-злодея запрещено → ранение'},
 cond_on:{i:'🎯',l:'доп. условие включено',g:'условия',r:e=>'доп. условие включено: '+esc(e.name)},
 cond_sniper:{i:'🎯',l:'косой снайпер',g:'условия',c:'dth',r:e=>'косой снайпер: '+one(e.seat)},
 blind_kill:{i:'🙈',l:'слепое убийство',g:'условия',c:'dth',r:e=>'слепое убийство: цель случайна → '+one(e.seat)},
 blind_empty:{i:'🙈',l:'слепое убийство в пустоту',g:'условия',r:e=>'слепое убийство: живых нет, цель не выбирается'},
 demon_on:{i:'👹',l:'вторая личность внедрена',g:'условия',r:e=>'вторая личность в '+one(e.seat)},
 demon_init:{i:'👹',l:'инициатива личности',g:'условия',r:e=>'инициатива второй личности: '+e.face+' → '+(e.act?'<b>действует</b>':'спит')},
 demon_act:{i:'👹',l:'личность действует',g:'условия',c:'wou',r:e=>'вторая личность '+one(e.seat)+'действует сама: '+esc(e.kind)},
 plane_final:{i:'🎲',l:'финал самолёта',g:'ситуация',c:'dth',r:e=>'финал самолёта: '+one(e.seat)},
 other:{i:'❔',l:'прочее',g:'структура',r:e=>esc(e.text||e.raw||'')}
};
const GROUPS=['структура','действия','урон','смерть','воскрешение','карты','профессии','социум','условия','ситуация'];

/* ---- состояние UI ---- */
const S={cycle:1,seat:null,types:new Set(),groups:new Set(),q:'',play:null,focusTurns:false};
const $=id=>document.getElementById(id);

function seatsOf(e){
 const out=[];
 ['seat','to','target','whom','by','a','b'].forEach(k=>{if(typeof e[k]==='number'&&e[k]>0)out.push(e[k])});
 ['targets','surv','heroes','villains','who','tgt'].forEach(k=>{if(Array.isArray(e[k]))out.push(...e[k])});
 return out;
}
function evSeats(e){if(e._s)return e._s;e._s=seatsOf(e);return e._s}

/* ---- шапка ---- */
function head(){
 const m=D.meta;
 const chips=[['сид',m.seed],['игроков',m.n],['ситуация',m.sit_ru||m.sit],['конец',m.end+' цикл'],
  ['выжили',(m.survivors||[]).map(s=>'P'+s).join(', ')||'—'],['смертей',m.deaths],['Жатв',m.harvests],
  ['воскрешений',m.revives],['первая смерть',m.first_death?('ц.'+m.first_death):'—'],
  ['пат',m.stall?'да':'нет'],['событий',m.events],['строк лога',m.lines]];
 const cfg=Object.entries(m.cfg||{});
 $('chips').innerHTML=chips.map(c=>'<span class="chip">'+esc(c[0])+' <b>'+esc(c[1])+'</b></span>').join('')
  +(cfg.length?'<span class="chip k">cfg: '+cfg.map(c=>esc(c[0])+'='+esc(c[1])).join(', ')+'</span>':'')
  +(m.core?'<span class="chip k">ядро '+esc(m.core)+'</span>':'');
 const cyc=D.cycles||[];
 $('strip').innerHTML=cyc.map(c=>{
   let mk='';
   if(c.deaths)mk+='<span class="d">💀'+c.deaths+'</span>';
   if(c.harvests)mk+=' 🌾';
   if(c.revives)mk+=' ✝';
   return '<div class="cy" data-c="'+c.c+'" title="'+(c.c===0?'пролог':('живых '+c.alive+', призраков '+c.ghosts+', лимбо '+c.limbo))+'"><b>'+(c.c===0?'0':c.c)+'</b><span class="mk">'+mk+'</span></div>'}).join('');
 Array.from($('strip').children).forEach(b=>b.onclick=()=>goto(+b.dataset.c));
}

/* ---- места ---- */
function players(){
 const box=$('players');box.innerHTML='';
 $('dolls').innerHTML=(D.dolls&&D.dolls.length)?'🧸 чучела Таксидермиста (места заняты, владельцы не воскреснут): '
   +D.dolls.map(d=>'P'+d.seat).join(', '):'';
 (D.players||[]).forEach(p=>{
  const fate=p.fate==='alive'?'жив':(p.fate==='limbo'?'лимбо':'умер ц.'+p.dead_c);
  const c=el('div','pc '+p.fate+(S.seat===p.seat?' sel':''));
  c.dataset.s=p.seat;
  const orp=Math.min(100,100*(p.or_||0)/Math.max(1,D.meta.or_death||3));
  c.innerHTML='<div class="no" style="background:'+p.color+'">P'+p.seat+'</div><div>'
   +'<div class="nm">'+esc(p.prof_name||'—')+' <span class="fate '+p.fate+'">'+fate+(p.revived?' ✝':'')+'</span></div>'
   +'<div class="pr">'+esc(p.arch_ru||'')+(p.agenda_ru?' · '+esc(p.agenda_ru):'')+(p.team!=null?' · команда '+(p.team+1):'')+'</div>'
   +'<div class="stat"><span>ОР '+(p.or_||0)+'</span><span>жизни '+(p.lives||0)+'</span><span>жетоны '+(p.tokens||0)+'</span>'
   +'<span>уб. '+(p.kills||0)+'</span><span>спец '+(p.uses?p.uses.spec:0)+'</span><span>тень '+(p.uses?p.uses.shadow:0)+'</span></div>'
   +'<div class="orbar"><i style="width:'+orp+'%"></i></div></div>';
  c.onclick=()=>select(S.seat===p.seat?null:p.seat);
  box.appendChild(c);
 });
}

function panel(){
 const box=$('panel');
 if(!S.seat){box.innerHTML='<div class="empty">Кликни место слева — здесь будет его картотека</div>';return}
 const p=P[S.seat];if(!p){box.innerHTML='';return}
 const rev={};(D.events||[]).forEach(e=>{if(e.type==='reveal'&&e.seat===S.seat)rev[e.cat+'|'+e.card]=e.c});
 const hand=Object.entries(p.hand||{}).map(([k,v])=>v?'<div class="c'+(rev[k+'|'+v]?' rev':'')+'"><i>'+esc(k)+(rev[k+'|'+v]?' · раскрыта в ц.'+rev[k+'|'+v]:' · закрыта')+'</i>'+esc(v)+'</div>':'').join('');
 const exch=(D.cycles||[]).map(c=>{const r=(c.rows||[]).find(x=>x.seat===S.seat);return r&&r.exch?'ц.'+c.c+': '+esc(r.exch):null}).filter(Boolean).join('<br>');
 const ort=(D.charts&&D.charts.ortl||[]).map(([c,m])=>m[String(S.seat)]!=null?(c+':'+m[String(S.seat)]):null).filter(Boolean).join(' ');
 const mine=(D.events||[]).filter(e=>evSeats(e).indexOf(S.seat)>=0).length;
 const kv=[['профессия',esc(p.prof||'—')],['архетип',esc(p.arch_ru||'—')+' <span class="raw">('+esc((p.archs||[]).join('+'))+')</span>'],
  ['повестка',esc(p.agenda_ru||'нет')],['личность','агр '+p.aggr+' · пом '+p.help+' · нейтр '+p.neut+' · кровь '+p.blood+(p.fear!=null?' · страх '+p.fear:'')],
  ['судьба',p.fate==='alive'?'выжил':(p.fate==='limbo'?'лимбо':'умер в цикле '+p.dead_c)+(p.revived?' (воскрешён)':'')],
  ['итоговые ОР',p.or_||0],['жетоны/жизни',(p.tokens||0)+' / '+(p.lives||0)],
  ['убийств / урона нанесено',(p.kills||0)+' / '+(p.dealt_w||0)],
  ['применения','спец '+(p.uses?p.uses.spec:0)+' · тень '+(p.uses?p.uses.shadow:0)+' · обмен '+(p.uses?p.uses.exch:0)+' · профессия '+(p.uses?p.uses.prof:0)],
  ['спецкарта',p.spec?esc(p.spec):'—'],['обмен по циклам',exch||'—'],['ОР по циклам',esc(ort)||'—'],['событий с его участием',mine]];
 box.innerHTML='<h3>P'+S.seat+' — '+esc(p.prof_name||'')+'</h3><div class="kv">'
  +kv.map(r=>'<div class="k">'+r[0]+'</div><div>'+r[1]+'</div>').join('')+'</div>'
  +'<h3 style="margin-top:12px">Стартовая рука</h3><div class="hand">'+(hand||'<div class="empty">рука пуста (rpds_economy/абляция)</div>')+'</div>';
}

/* ---- лента ---- */
function renderFeed(){
 const box=$('feed');box.innerHTML='';
 const q=S.q.trim().toLowerCase();
 const groups=D.cycleGroups||(D.cycleGroups=groupEvents());
 let shown=0;
 groups.forEach(g=>{
  const c=(D.cycles||[]).find(x=>x.c===g.c)||{c:g.c};
  const head=el('div','cyhead');
  head.id='cyc'+g.c;
  head.innerHTML='<span class="n">'+(g.c===0?'ПРОЛОГ':'ЦИКЛ '+g.c)+'</span><span class="st">живых '+(c.alive!=null?c.alive:'?')
   +' · призраков '+(c.ghosts||0)+' · лимбо '+(c.limbo||0)+'</span><span class="dl">💀 '+(c.deaths||0)+' · 🌾 '+(c.harvests||0)
   +' · ✝ '+(c.revives||0)+' · 🎲 '+(c.rolls||0)+'</span>';
  box.appendChild(head);
  const ol=el('ol','feed');
  g.items.forEach(e=>{
   const t=TM[e.type]||TM.other;
   const seats=evSeats(e);
   const li=el('li','ev '+(t.c||'')+(e.type==='turn_start'?' turn':''));
   li.dataset.c=e.c;li.dataset.t=e.type;li.dataset.s=seats.join(',');
   let txt=fallback(e);
   const hay=(txt+' '+(e.raw||'')).toLowerCase();
   let hide=false;
   if(S.seat&&seats.indexOf(S.seat)<0)hide=true;
   if(S.types.size&&!S.types.has(e.type))hide=true;
   if(S.groups.size){const gr=(D.typeGroup||(D.typeGroup=Object.fromEntries(Object.entries(TM).map(([k,v])=>[k,v.g]))))[e.type];if(!S.groups.has(gr))hide=true}
   if(S.focusTurns&&!(e.type==='turn_start'||(S.seat&&seats.indexOf(S.seat)>=0)))hide=true;
   if(q){if(hay.indexOf(q)<0)hide=true;else txt=hl(txt,S.q.trim())}
   if(hide)li.classList.add('hid');else shown++;
   li.innerHTML='<div class="ic">'+t.i+'</div><div class="tx">'+txt
     +(q?'':'<div class="raw">'+esc((e.raw||'').trim())+'</div>')+'</div>';
   ol.appendChild(li);
  });
  box.appendChild(ol);
 });
 $('count').textContent='показано событий: '+shown+' из '+(D.events||[]).length;
 bindWho();
}
function groupEvents(){
 const m=new Map();
 (D.events||[]).forEach(e=>{
   if(e.type==='cycle_start'){if(!m.has(e.c))m.set(e.c,{c:e.c,items:[]});return}
   if(!m.has(e.c))m.set(e.c,{c:e.c,items:[]});
   m.get(e.c).items.push(e)});
 return Array.from(m.values()).sort((a,b)=>a.c-b.c);
}
function bindWho(){
 document.querySelectorAll('.who').forEach(w=>w.onclick=ev=>{ev.stopPropagation();select(+w.dataset.s)});
}

/* ---- фильтры ---- */
function typeFilters(){
 const box=$('types');box.innerHTML='';
 const cnt={};(D.events||[]).forEach(e=>cnt[e.type]=(cnt[e.type]||0)+1);
 const gr={};Object.entries(TM).forEach(([k,v])=>{(gr[v.g]=gr[v.g]||[]).push(k)});
 const gb=el('div','tf');
 GROUPS.forEach(g=>{if(!gr[g])return;const b=el('button',S.groups.has(g)?'on':'',esc(g)+' '+gr[g].reduce((s,k)=>s+(cnt[k]||0),0));
   b.onclick=()=>{S.groups.has(g)?S.groups.delete(g):S.groups.add(g);typeFilters();renderFeed()};gb.appendChild(b)});
 const all=el('button','','сброс');all.onclick=()=>{S.groups.clear();S.types.clear();typeFilters();renderFeed()};
 gb.appendChild(all);box.appendChild(gb);
 const tb=el('div','tf');tb.style.marginTop='6px';
 Object.entries(TM).forEach(([k,v])=>{if(!cnt[k])return;
   const b=el('button',S.types.has(k)?'on':'',v.i+' '+esc(v.l)+' '+cnt[k]);
   b.onclick=()=>{S.types.has(k)?S.types.delete(k):S.types.add(k);typeFilters();renderFeed()};tb.appendChild(b)});
 box.appendChild(tb);
}

/* ---- графики ---- */
function svg(w,h,inner){return '<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" style="height:'+h+'px">'+inner+'</svg>'}
function charts(){
 const ch=D.charts||{};const cyc=D.cycles||[];
 // живые/призраки
 let s='';const W=560,H=120,mx=Math.max(1,D.meta.n);let px=0,pya=0,pyg=0;
 (ch.alive||[]).forEach((r,i)=>{const x=8+i*(W-16)/Math.max(1,(ch.alive||[]).length-1);
   const ya=H-8-(r[1]/mx)*(H-20),yg=H-8-((r[1]+r[2])/mx)*(H-20);
   if(i){s+='<line x1="'+px+'" y1="'+pyg+'" x2="'+x+'" y2="'+yg+'" stroke="#6b7688" stroke-width="1.5" stroke-dasharray="3 3"/>'
          +'<line x1="'+px+'" y1="'+pya+'" x2="'+x+'" y2="'+ya+'" stroke="#7ee081" stroke-width="2"/>'}
   s+='<circle cx="'+x+'" cy="'+ya+'" r="2.6" fill="#7ee081"/>';px=x;pya=ya;pyg=yg;});
 $('gAlive').innerHTML=svg(W,H,s)+'<div class="lgd"><span><i style="background:#7ee081"></i>живые</span><span><i style="background:#6b7688"></i>живые+призраки</span></div>';
 // ОР по циклам
 const O=ch.ortl||[];let s2='';const mxor=Math.max(1,...O.flatMap(r=>Object.values(r[1])));
 (D.players||[]).forEach(p=>{let pts=[];O.forEach((r,i)=>{const v=r[1][String(p.seat)];
    if(v==null)return;const x=8+i*(W-16)/Math.max(1,O.length-1),y=H-8-(v/mxor)*(H-20);pts.push(x+','+y)});
   if(pts.length>1)s2+='<polyline points="'+pts.join(' ')+'" fill="none" stroke="'+p.color+'" stroke-width="1.6" opacity="'+(S.seat&&S.seat!==p.seat?.22:.95)+'"/>'});
 s2+='<line x1="8" y1="'+(H-8)+'" x2="'+(W-8)+'" y2="'+(H-8)+'" stroke="#28303c"/>';
 $('gOr').innerHTML=svg(W,H,s2)+'<div class="lgd"><span>макс. ОР '+mxor+' · линии — места (клик по месту выделяет)</span></div>';
 // гистограмма кубика
 const h=ch.hist||[];const mh=Math.max(1,...h.map(x=>x[1]));const bw=(W-16)/Math.max(1,h.length);
 let s3='';h.forEach((x,i)=>{const bh=(x[1]/mh)*(H-24);const col=(i===0||i===h.length-1)?'#f2736f':'#b9a6f5';
   s3+='<rect x="'+(8+i*bw)+'" y="'+(H-8-bh)+'" width="'+(bw-2)+'" height="'+bh+'" fill="'+col+'" rx="1.5"/>'
     +'<text x="'+(8+i*bw+bw/2)+'" y="'+(H-10-bh)+'" fill="#8b98a9" font-size="8" text-anchor="middle">'+x[1]+'</text>'
     +'<text x="'+(8+i*bw+bw/2)+'" y="'+(H-0)+'" fill="#5d6a7b" font-size="8" text-anchor="middle">'+x[0]+'</text>'});
 $('gHist').innerHTML=svg(W,H,s3)+'<div class="lgd"><span><i style="background:#f2736f"></i>нат.1 / нат.'+(D.meta.faces||20)+'</span><span>бросков '+h.reduce((a,b)=>a+b[1],0)+'</span></div>';
 // причины смертей + типы событий
 const cs=ch.causes||[];const mc=Math.max(1,...cs.map(x=>x[1]));
 $('gCause').innerHTML=cs.length?cs.map(x=>'<div class="bar"><span>'+esc(x[0])+'</span><span class="t"><i style="width:'+(100*x[1]/mc)+'%"></i></span><span class="v">'+x[1]+'</span></div>').join(''):'<div class="empty">смертей не было</div>';
 const ts=(ch.types||[]).slice(0,14);const mt=Math.max(1,...ts.map(x=>x[1]));
 $('gTypes').innerHTML=ts.map(x=>'<div class="bar"><span>'+((TM[x[0]]||{}).i||'')+' '+esc(((TM[x[0]]||{}).l)||x[0])+'</span><span class="t"><i style="width:'+(100*x[1]/mt)+'%;background:#7fd4f2"></i></span><span class="v">'+x[1]+'</span></div>').join('');
 // сводка циклов
 $('gCyc').innerHTML='<div class="bar" style="grid-template-columns:34px 1fr 34px 34px 34px;font-weight:600;color:#8b98a9"><span>цикл</span><span>живых</span><span>💀</span><span>🌾</span><span>✝</span></div>'
  +cyc.map(c=>'<div class="bar" style="grid-template-columns:34px 1fr 34px 34px 34px"><span>'+(c.c===0?'П':c.c)+'</span><span class="t"><i style="width:'+(100*(c.alive||0)/Math.max(1,D.meta.n))+'%;background:#7ee081"></i></span><span class="v">'+(c.deaths||0)+'</span><span class="v">'+(c.harvests||0)+'</span><span class="v">'+(c.revives||0)+'</span></div>').join('');
}

/* ---- лог ---- */
function renderLog(){
 const box=$('logbox');const L=D.log||[];
 const cycOf=[];let cur=0;L.forEach(l=>{const m=/ЦИКЛ (\d+)/.exec(l);if(m)cur=+m[1];cycOf.push(cur)});
 D._cycOf=cycOf;
 box.innerHTML=L.map((l,i)=>'<div class="ln'+(/💀|умирает/.test(l)?' d':'')+'" data-i="'+i+'" data-c="'+cycOf[i]+'">'+esc(l)+'</div>').join('');
}
function syncLog(){
 if($('logbox').style.display!=='block')return;
 const lines=$('logbox').querySelectorAll('.ln');
 lines.forEach(x=>x.classList.toggle('cur',+x.dataset.c===S.cycle));
 const first=$('logbox').querySelector('.ln[data-c="'+S.cycle+'"]');
 if(first)first.scrollIntoView({block:'start'});
}

/* ---- навигация ---- */
function goto(c,silent){
 const cyc=D.cycles||[];if(!cyc.length)return;
 S.cycle=Math.max(1,Math.min(c,cyc[cyc.length-1].c));
 document.querySelectorAll('.cy').forEach(b=>b.classList.toggle('cur',+b.dataset.c===S.cycle));
 const h=document.getElementById('cyc'+S.cycle);
 if(h&&!silent)h.scrollIntoView({behavior:'smooth',block:'start'});
 $('cnum').textContent=S.cycle;syncLog();
}
function select(s){
 S.seat=s;
 document.querySelectorAll('.pc').forEach(c=>c.classList.toggle('sel',+c.dataset.s===s));
 renderFeed();panel();charts();
 $('seatName').textContent=s?('P'+s+' — '+((P[s]||{}).prof_name||'')):'все места';
}
function togglePlay(){
 if(S.play){clearInterval(S.play);S.play=null;$('play').classList.remove('on');$('play').textContent='▶ PLAY';return}
 $('play').classList.add('on');$('play').textContent='⏸ стоп';
 S.play=setInterval(()=>{const last=(D.cycles||[]).length;
   if(S.cycle>=last){togglePlay();return}
   goto(S.cycle+1)},900);
}
function jump(kind){
 const cyc=(D.cycles||[]);
 const any=cyc.filter(c=>(kind==='d'&&c.deaths>0)||(kind==='h'&&c.harvests>0)||(kind==='r'&&c.revives>0));
 const nxt=any.find(c=>c.c>S.cycle)||any[0];
 if(nxt)goto(nxt.c);
}

/* ---- инициализация ---- */
function init(){
 D.cards={};(D.players||[]).forEach(p=>{if(p.spec)D.cards[p.seat]=p.spec});
 D.agenda_ru={};(D.players||[]).forEach(p=>{if(p.agenda)D.agenda_ru[p.agenda]=p.agenda_ru});
 D.cause_ru=D.cause_ru||{};
 head();players();typeFilters();renderFeed();panel();charts();renderLog();
 if((D.cycles||[]).length)goto(1,true);
 $('play').onclick=togglePlay;
 $('prev').onclick=()=>goto(S.cycle-1);
 $('next').onclick=()=>goto(S.cycle+1);
 $('rawbtn').onclick=()=>{document.body.classList.toggle('showraw');$('rawbtn').classList.toggle('on')};
 $('logbtn').onclick=()=>{const b=$('logbox');b.style.display=b.style.display==='block'?'none':'block';$('logbtn').classList.toggle('on');syncLog()};
 $('clear').onclick=()=>{S.seat=null;S.types.clear();S.groups.clear();S.q='';$('q').value='';select(null);typeFilters();renderFeed()};
 $('qd').onclick=()=>jump('d');$('qh').onclick=()=>jump('h');$('qr').onclick=()=>jump('r');
 $('q').oninput=e=>{S.q=e.target.value;renderFeed()};
 $('onlyTurns').onclick=e=>{S.focusTurns=e.target.checked;renderFeed()};
 document.addEventListener('keydown',e=>{
   if(e.target.tagName==='INPUT')return;
   if(e.key==='ArrowRight'){goto(S.cycle+1);e.preventDefault()}
   if(e.key==='ArrowLeft'){goto(S.cycle-1);e.preventDefault()}
   if(e.key===' '){togglePlay();e.preventDefault()}
   if(e.key==='Escape'){select(null)}
 });
}
document.addEventListener('DOMContentLoaded',init);
"""

PAGE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>БЛИЦ БОЙ — партия __TITLE__</title>
<style>__CSS__</style></head>
<body>
<header>
 <h1>БЛИЦ БОЙ · партия __TITLE__ <span class="sub">HTML-вьюер (п.21), самодостаточная страница</span></h1>
 <div class="chips" id="chips"></div>
 <div class="ctrl">
  <button id="prev" title="предыдущий цикл (←)">◀</button>
  <span class="chip">цикл <b id="cnum">1</b></span>
  <button id="next" title="следующий цикл (→)">▶</button>
  <button id="play">▶ PLAY</button>
  <button id="qd" title="к следующей смерти">💀</button>
  <button id="qh" title="к следующей Жатве">🌾</button>
  <button id="qr" title="к следующему воскрешению">✝</button>
  <input type="text" id="q" placeholder="поиск по ленте и логу…">
  <label class="chip"><input type="checkbox" id="onlyTurns"> только ходы</label>
  <button id="rawbtn" title="показывать исходную строку лога под событием">строки лога</button>
  <button id="logbtn">лог</button>
  <button id="clear">сброс фильтров</button>
  <span class="chip k" id="seatName">все места</span>
  <span class="chip k" id="count"></span>
 </div>
 <div class="strip" id="strip"></div>
</header>
<div class="wrap">
 <div class="col left">
  <div class="block"><h3>Места (клик = фильтр)</h3><div id="players"></div><div id="dolls" class="raw"></div></div>
  <div class="block" id="panelBox"><h3>Картотека места</h3><div id="panel"></div></div>
 </div>
 <div class="col center">
  <div class="block"><h3>Фильтры ленты</h3><div id="types"></div></div>
  <div class="block"><h3>Лента событий</h3><div id="feed"></div></div>
 </div>
 <div class="col right">
  <div class="block"><h3>Циклы</h3><div id="gCyc"></div></div>
  <div class="block"><h3>Живые / призраки</h3><div id="gAlive"></div></div>
  <div class="block"><h3>ОР по циклам</h3><div id="gOr"></div></div>
  <div class="block"><h3>Кубик</h3><div id="gHist"></div></div>
  <div class="block"><h3>Причины смертей</h3><div id="gCause"></div></div>
  <div class="block"><h3>Типы событий</h3><div id="gTypes"></div></div>
 </div>
</div>
<div id="logbox"></div>
<div class="foot">БЛИЦ БОЙ · печатная ред. №2 (2026-10) · ядро пересборки __CORE__ · страница не требует интернета:
данные партии встроены, скрипты и стили инлайновые. Горячие клавиши: ← → цикл, пробел — автопрокрутка, Esc — сброс места.</div>
<script>window.__BB__=__DATA__;</script>
<script>__JS__</script>
</body></html>
"""


def _page(model, title):
    data = json.dumps(model, ensure_ascii=False, separators=(',', ':'))
    data = data.replace('</', '<\\/')          # защита от преждевременного </script>
    out = (PAGE.replace('__CSS__', CSS).replace('__JS__', JS)
           .replace('__TITLE__', title).replace('__CORE__', str(model.get('meta', {}).get('core', '?'))))
    return out.replace('__DATA__', data)


def render(model):
    """model (bb_model.build_model) → строка HTML."""
    m = model['meta']
    return _page(model, f"seed {m['seed']} · N{m['n']} · {m['sit']}")


def write_page(model, path):
    html = render(model)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path, len(html)


def write_page_from_log(lines, path, title=None):
    """Страница ТОЛЬКО из сохранённого лога (без снимков: нет карточек мест и графиков ОР)."""
    import bb_events
    ev = bb_events.parse_log(lines)
    seats = sorted({s for e in ev for s in _seats(e)})
    model = dict(
        meta=dict(seed=None, n=len(seats), sit='log', sit_ru='из сохранённого лога', cfg={},
                  core='log-only', faces=20, end=max([e['c'] for e in ev] or [0]),
                  deaths=sum(1 for e in ev if e['type'] == 'death'),
                  harvests=sum(1 for e in ev if e['type'].startswith('harvest') and e['type'] != 'harvest_cancel'),
                  revives=sum(1 for e in ev if e['type'] in ('revive_tokens', 'revive_necro', 'revive_agent', 'reincarnate')),
                  first_death=next((e['c'] for e in ev if e['type'] == 'death'), None),
                  stall=False, nat1=False, nat20=False, limbo_events=0, spec_uses=0, prof_uses=0,
                  shadow_uses=0, exch_uses=0, betrayals=0, deals=0, demon_acts=0, drag=0,
                  survivors=[], thr=None, lines=len(lines), events=len(ev)),
        players=[dict(seat=s, prof='', prof_name='', arch='', arch_ru='', archs=[], agenda='',
                      agenda_ru='', aggr=0, help=0, neut=0, blood=0, fear=None, detach=0, coop=0,
                      team=None, fate='alive', dead_c=None, revived=False, limbo=False, or_=0, lives=0,
                      tokens=0, kills=0, dealt_w=0, dealt_k=0, uses=dict(prof=0, spec=0, shadow=0, exch=0),
                      hand={}, spec=None, spec_i=None,
                      color=__import__('bb_model').PALETTE[(s - 1) % 20]) for s in seats],
        cycles=_cycles_from_events(ev), events=ev, log=lines,
        charts=dict(hist=_hist(ev), alive=[[c['c'], c['alive'], 0, 0] for c in _cycles_from_events(ev)],
                    ortl=[], causes=_causes(ev), types=_types(ev)))
    model['cause_ru'] = CAUSE_RU_LOG
    return write_page(model, path)


def _seats(e):
    import bb_model
    return bb_model.seats_of(e)


def _cycles_from_events(ev):
    out = {}
    for e in ev:
        c = out.setdefault(e['c'], dict(c=e['c'], alive=None, ghosts=0, limbo=0, deaths=0,
                                        harvests=0, revives=0, rolls=0, rows=[]))
        if e['type'] == 'cycle_start':
            c.update(alive=e.get('alive'), ghosts=e.get('ghosts'), limbo=e.get('limbo'))
        elif e['type'] == 'death':
            c['deaths'] += 1
        elif e['type'] in ('harvest', 'harvest_esc', 'harvest_leader'):
            c['harvests'] += 1
        elif e['type'] in ('revive_tokens', 'revive_necro', 'revive_agent', 'reincarnate'):
            c['revives'] += 1
        elif e['type'] == 'roll':
            c['rolls'] += 1
    return [out[k] for k in sorted(out)]


def _hist(ev, faces=20):
    from collections import Counter
    h = Counter(e['face'] for e in ev if e['type'] == 'roll')
    return [[f, h.get(f, 0)] for f in range(1, faces + 1)]


def _causes(ev):
    from collections import Counter
    import bb_model
    c = Counter(e['cause'] for e in ev if e['type'] == 'death')
    return [[bb_model.CAUSE_RU.get(k, k), v] for k, v in c.most_common()]


def _types(ev):
    from collections import Counter
    return list(Counter(e['type'] for e in ev).most_common())


if __name__ == '__main__':
    import sys, bb_model
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 777
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    sit = sys.argv[3] if len(sys.argv) > 3 else 'plane'
    out = sys.argv[4] if len(sys.argv) > 4 else f'VIEW_game_{seed}_N{n}_{sit}.html'
    m = bb_model.build_model(seed, n, sit)
    p, size = write_page(m, out)
    print('вьюер:', p, size, 'байт | событий', m['meta']['events'], '| циклов', len(m['cycles']))
