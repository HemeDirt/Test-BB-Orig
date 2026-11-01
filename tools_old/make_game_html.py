# -*- coding: utf-8 -*-
"""Собирает game.html — автономную браузерную версию БЛИЦ БОЙ из канонных данных."""
import json

decks = json.load(open('canon/decks.json', encoding='utf-8'))
CATS = ['ТЕЛО','РАЗУМ','СПОСОБНОСТИ','ИНВЕНТАРЬ','ИСТОРИЯ','ЗНАНИЯ','ДЕТАЛИ']

NAMES = ['Валера','Зинка','Петрович','Саня','Ленка','Эдик','Маринка','Толик']
PROFS = [
 ['Почтальон','Получает в инвентарь посылку с рандомным предметом'],
 ['Стример','Может вести стрим и собирать донаты'],
 ['Водитель','Получает любую машину на выбор'],
 ['Вор','Может украсть одну вещь за цикл, работает 3 раза'],
 ['Медик','Может воскресить другого игрока'],
 ['Крупье','Может перебросить кубик 1 раз за цикл'],
 ['Шизик','Немного поехавший, но на удивление везучий'],
 ['Каскадёр','Принимает чужое РП-действие на себя (до броска)'],
]
SPECS = [
 ['extra','Добавляется одно любое РП действие'],
 ['immune','Игнорировать любое воздействие на себя от другого игрока на один цикл'],
 ['fullheal','Вылечить любого игрока полностью от всего'],
 ['avoid','Даёт возможность избежать смерти (использовать до смерти)'],
 ['lootdead','Может украсть у мёртвого игрока всё, что захочет'],
 ['additem','Добавить характеристику себе (крупный инвентарь)'],
 ['revive','Вернуть игрока из мёртвых с дебафом −1 РП-действие'],
 ['autohit','Одно РП-действие со 100% вероятностью'],
]
TENY = decks['ТЕНЬ']
OBMEN = decks['ОБМЕН']

def J(x): return json.dumps(x, ensure_ascii=False)

DATA = f"""const CATS={J(CATS)};
const DECKS={{{', '.join(f'{J(c)}:{J(decks[c][:24])}' for c in CATS)}}};
const NAMES={J(NAMES)};
const PROFS={J(PROFS)};
const SPECS={J(SPECS)};
const TENY={J(TENY)};
const OBMEN={J(OBMEN)};"""

HTML = """<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>БЛИЦ БОЙ — рабочая игра</title>
<style>
:root{--bg:#14161c;--card:#1e2129;--acc:#e0b34d;--red:#e05d5d;--gr:#6dc36d;--mut:#8a8f9d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#e8eaf0;font-family:system-ui,Segoe UI,Roboto,sans-serif;line-height:1.45}
.wrap{max-width:820px;margin:0 auto;padding:14px}
h1{color:var(--acc);font-size:24px;margin:6px 0 2px}
.sub{color:var(--mut);font-size:13px;margin-bottom:12px}
button{background:var(--acc);border:0;color:#14161c;font-size:15px;font-weight:700;padding:10px 16px;border-radius:10px;cursor:pointer;margin:4px 6px 4px 0}
button.sec{background:#2a2e3a;color:#e8eaf0;font-weight:400}
.panel{background:var(--card);border-radius:14px;padding:14px;margin:10px 0;border:1px solid #2a2e3a}
.seats{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin:8px 0}
.seat{background:#222632;border-radius:10px;padding:8px 10px;font-size:13px;border:1px solid #2e3342}
.seat.dead{opacity:.4}.seat.cur{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}
.or{color:var(--red);font-weight:700}
.log{font-size:13px;white-space:pre-wrap;max-height:46vh;overflow-y:auto;background:#101218;border-radius:10px;padding:10px;margin-top:8px}
.log .d{color:var(--red)}.log .g{color:var(--gr)}.log .y{color:var(--acc)}.log .m{color:var(--mut)}
select,input[type=text]{background:#222632;color:#e8eaf0;border:1px solid #2e3342;border-radius:8px;padding:8px;font-size:14px}
.tag{display:inline-block;background:#2a2e3a;border-radius:6px;padding:1px 7px;font-size:12px;margin:2px}
.small{font-size:12px;color:var(--mut)}
h3{margin:4px 0 8px;color:var(--acc);font-size:15px}
.hand{font-size:12px}.hand .tag{background:#26313f}
.revs{font-size:12px;color:#9fb3d9}
</style></head><body><div class="wrap">
<h1>⚡ БЛИЦ БОЙ</h1>
<div class="sub">Рабочий билд v1 · правила v3 · канонные колоды 24×7 · 8 игроков · «Ночь в панельке» · S=4 · ОР-порог 3</div>
<div id="menu" class="panel">
<h3>Режим</h3>
<button onclick="startGame(false)">▶ Партия с ботами</button>
<button onclick="startGame(true)">🎮 Я играю за Валеру (P1), остальные — боты</button>
<div style="margin-top:8px">
<select id="variant">
<option value="base">Базовые правила v3</option>
<option value="harvest_off">БЕЗ Жатвы</option>
<option value="or5">Порог смерти 5 ОР (тест длинной партии)</option>
<option value="fast">Порог смерти 2 ОР (тест быстрой партии)</option>
</select>
<input type="text" id="seedInp" placeholder="seed (пусто = случайный)" size="14">
</div>
<div style="margin-top:6px"><button class="sec" onclick="showDecks()">📋 Колоды (канон 24)</button>
<button class="sec" onclick="showRules()">📖 Краткие правила</button></div>
</div>
<div id="decks" class="panel" style="display:none"></div>
<div id="game" class="panel" style="display:none">
<div id="status"></div>
<div class="seats" id="seats"></div>
<div id="action"></div>
<div class="log" id="log"></div>
<button class="sec" onclick="location.reload()">⬅ В меню</button>
</div>
</div>
<script>
"use strict";
__DATA__
/* ================= ядро (порт game_sim.py) ================= */
let S=null,HUMAN=false,VARIANT="base",seed=0,rnd=Math.random;
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
const R=()=>rnd(),RI=n=>Math.floor(R()*n)+1,pick=a=>a[Math.floor(R()*a.length)];
function pickW(pairs){let t=pairs.reduce((s,x)=>s+x[1],0),x=R()*t;for(const[v,w]of pairs){x-=w;if(x<=0)return v}return pairs[0][0]}
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(R()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
const thr=()=>VARIANT==="fast"?2:(VARIANT==="or5"?5:3);
const harvestOn=()=>VARIANT!=="harvest_off";
function log(s,cls){const el=document.getElementById("log");if(!el)return;const d=document.createElement("div");if(cls)d.className=cls;d.textContent=s;el.appendChild(d);el.scrollTop=el.scrollHeight}
const alive=()=>S.P.filter(p=>p.alive);
const ghosts=()=>S.P.filter(p=>!p.alive);
function bySeat(n){return S.P[n-1]}
function closed(p){const o=[];for(const k of CATS)for(const c of p.hand[k])o.push([k,c]);return o}
function cardText(c){return Array.isArray(c)?c[1]:c}
function cardName(c){return Array.isArray(c)?c[0]:String(c).split(" — ")[0]}
function reveal(p,n){for(let i=0;i<n;i++){const cc=closed(p);if(!cc.length)return;const[k,c]=pick(cc);p.hand[k].splice(p.hand[k].indexOf(c),1);p.revealed.push([k,c]);log(`  ${p.name} раскрывает [${k}] «${cardText(c)}»`)}}
function wound(p,amt,src){if(!p.alive||amt<=0)return false;
 if(p.immune===S.cycle&&src!=="self"){log(`  ${p.name}: невосприимчив (спецкарта) — ${amt} ОР не проходит`,"m");return false}
 p.or+=amt;S.lastWound=[p.seat,amt];log(`  ${p.name}: +${amt} ОР → ${p.or}`+(src?` (${src})`:""),"d");
 if(p.or>=thr())death(p,"ранения",src);return true}
function death(p,cause,src){if(!p.alive)return;
 if(p.specArmed){p.specArmed=false;p.usedSpec=true;p.or=thr()-1;log(`  !!! ${p.name} уходит от смерти: спецкарта «избежать смерти», ОР → ${p.or}`,"y");return}
 p.alive=false;p.died=S.cycle;S.deaths++;if(S.firstDeath===null)S.firstDeath=S.cycle;
 if(cause==="жатва")log(`  💀 ${p.name} (место ${p.seat}) УМИРАЕТ от ЖАТВЫ`,"d");
 else{S.playerDeath=true;log(`  💀 ${p.name} (место ${p.seat}) УМИРАЕТ (${cause}${src?", источник: "+src:""})`,"d")}
 p.obmen=null}
function modRoll(p,m,kind){if(p.buff){m+=p.buff;p.buff=0;log("    (+1 невидимый напарник)","m")}if(S.dark&&(kind==="рпди"||kind==="mass"))m--;return m}
function croupier(p,eff,kind){const cr=S.P.find(q=>q.alive&&q.prof[0]==="Крупье"&&q!==p&&q.crCycle!==S.cycle);
 if(cr&&eff<10&&R()<0.55){cr.crCycle=S.cycle;const r2=RI(20);log(`  КРУПЬЕ ${cr.name} перебрасывает кубик: ${eff} → ${r2}`,"y");return r2}return eff}
function tableA(p,declared,t){const nat=RI(20);let eff=modRoll(p,nat,"рпди");const kill=declared==="УБИЙСТВО";
 log(`  ${p.name}: заявлено ${declared}${t?" против "+t.name:""}, d20=${nat}${eff!==nat?" (с мод. "+eff+")":""}`);
 eff=croupier(p,eff,"рпди");
 if(kill){if(eff<=4){log("    КРИТ-ПРОВАЛ: удар возвращается в автора","d");death(p,"крит-провал убийства",p.name)}
  else if(eff<=8)wound(p,1,"свой провал");else if(eff<=12)log("    ничего не произошло","m");
  else if(eff<=16){if(t)wound(t,2,p.name)}
  else{log("    КРИТ: цель умирает сразу","d");if(t){p.kills++;death(t,"крит убийства",p.name)}}}
 else{if(eff<=4)wound(p,2,"self");else if(eff<=8)wound(p,1,"self");
  else if(eff<=12)log("    ничего не произошло","m");else if(eff<=16){if(t)wound(t,1,p.name)}
  else{log("    КРИТ: +2 ОР цели","d");if(t)wound(t,2,p.name)}}}
function tableB(p,label,onS,onF,kind){const nat=RI(20);let eff=modRoll(p,nat,kind||"рпди");
 log(`  ${p.name}: ${label}, d20=${nat}${eff!==nat?" (с мод. "+eff+")":""}`);eff=croupier(p,eff,kind||"рпди");
 if(nat===20||eff>=15)onS();else if(nat===1||eff<=10)onF();else log("    ничего не произошло (11–14)","m")}
function tableV(p,label,onS,onF){const nat=RI(20);const eff=modRoll(p,nat,"рпдс");
 log(`  ${p.name}: ${label}, d20=${nat}${eff!==nat?" (с мод. "+eff+")":""}`);
 if(nat===20||eff>=11)onS();else if(nat===1||eff<=9)onF();else log("    ничего не произошло (10)","m")}
function pickTarget(p){const cs=S.P.filter(q=>q.alive&&q!==p&&!q.noTarget);const alt=S.P.filter(q=>q.alive&&q!==p);
 return pick(cs.length?cs:alt.length?alt:[p])}
function cascade(p,t){const cs=S.P.filter(q=>q.alive&&q.prof[0]==="Каскадёр"&&q!==t&&q!==p);
 if(cs.length&&R()<0.4){const c=cs[0];log(`  КАСКАДЁР ${c.name} принимает удар на себя!`,"y");return c}return t}
function steal(p,v){tableB(p,`кража у ${v.name} вслепую`,()=>{const cc=closed(v);
 if(!cc.length){log("    у цели пусто — красть нечего","m");return}
 const[k,c]=pick(cc);v.hand[k].splice(v.hand[k].indexOf(c),1);p.hand[k].push(c);
 log(`    УСПЕХ: ${p.name} забирает [${k}] «${cardText(c)}»`,"g")},()=>{const cc=closed(p);
 if(cc.length){const[k,c]=pick(cc);p.hand[k].splice(p.hand[k].indexOf(c),1);v.hand[k].push(c);
 log(`    ПРОВАЛ: ${v.name} тянет у ${p.name} карту [${k}] «${cardText(c)}»`,"d")}else log("    ПРОВАЛ: рука открыта, позор без механики","m")})}
function healAct(p,t){if(t.healTaken>=1){log(`  лимит лечения ${t.name} исчерпан — действие сгорает`,"m");return}
 tableB(p,`помощь/лечение ${t.name}`,()=>{t.or=Math.max(0,t.or-1);t.healTaken++;log(`    УСПЕХ: ${t.name} −1 ОР → ${t.or}`,"g")},
 ()=>{log("    ПРОВАЛ: неумелая помощь","d");wound(p,1,"self")})}
function humiliate(p,t){tableB(p,`унижение ${t.name}`,()=>{const cc=closed(t);
 if(cc.length){const[k,c]=pick(cc);t.hand[k].splice(t.hand[k].indexOf(c),1);t.revealed.push([k,c]);log(`    УСПЕХ: ${t.name} раскрывает [${k}] «${cardText(c)}»`,"g")}
 else{t.obmen=null;log(`    УСПЕХ: ${t.name} публично унижен, сбрасывает карту обмена`,"g")}},
 ()=>{const cc=closed(p);if(cc.length){const[k,c]=pick(cc);p.hand[k].splice(p.hand[k].indexOf(c),1);p.revealed.push([k,c]);log(`    ПРОВАЛ: осмеян сам ${p.name}, раскрывает [${k}] «${cardText(c)}»`,"d")}
 else log(`    ПРОВАЛ: ${p.name} опозорился (без механики)`,"m")})}
function rpdsWorld(p){tableV(p,"РПДС: взаимодействие с миром",()=>{const cat=pick(CATS);
 if(S.draw[cat].length){const c=S.draw[cat].pop();p.hand[cat].push(c);log(`    УСПЕХ: найдено [{cat}] «${cardText(c)}»`,"g")}},
 ()=>log("    ПРОВАЛ: мир не дал ничего (обратный эффект narrativный)","m"))}
function rpdsHeal(p){tableV(p,"РПДС: самолечение",()=>{p.or=Math.max(0,p.or-1);p.healTaken++;log(`    УСПЕХ: −1 ОР → ${p.or}`,"g")},
 ()=>{p.healTaken++;log("    ПРОВАЛ: стало хуже","d");wound(p,1,"self")})}
function rpdsStream(p){tableV(p,"РПДС+профессия «Стример»: донаты",()=>{if(S.draw["ИНВЕНТАРЬ"].length){const c=S.draw["ИНВЕНТАРЬ"].pop();p.hand["ИНВЕНТАРЬ"].push(c);log(`    УСПЕХ: донаты → [ИНВЕНТАРЬ] «${cardText(c)}»`,"g")}},
 ()=>log("    ПРОВАЛ: стрим забанили","m"))}
function useObmen(p,st){const[name,txt]=p.obmen;const needRpdi=["Обмен","Свидетель","Подстава"].includes(name);
 if(needRpdi&&!st.rpdi)return st;
 log(`  🃏 ${p.name} применяет карту обмена «${name}»: ${txt}`,"y");p.obmen=null;
 if(st.rpdi)st.rpdi--;else st.rpds--;
 if(name==="Парамедик"){const q=p.or>=1?p:alive().find(x=>x.or>=1)||p;q.or=Math.max(0,q.or-1);q.healTaken++;log(`    ${q.name}: −1 ОР → ${q.or}`,"g")}
 else if(name==="Отмена"){if(S.lastWound){const[s,a]=S.lastWound;const q=bySeat(s);q.or=Math.max(0,q.or-a);S.lastWound=null;log(`    последствие отменено: ${q.name} → ${q.or} ОР`,"g")}}
 else if(name==="Заначка"){for(let i=0;i<2;i++){const cat=pick(CATS);if(S.draw[cat].length){const c=S.draw[cat].pop();p.hand[cat].push(c);log(`    в руку: [${cat}] «${cardText(c)}»`,"g")}}}
 else if(name==="Обмен"){const t=pickTarget(p);const c1=closed(p),c2=closed(t);
 if(c1.length&&c2.length){const[k1,x1]=pick(c1),[k2,x2]=pick(c2);
  p.hand[k1].splice(p.hand[k1].indexOf(x1),1);t.hand[k2].splice(t.hand[k2].indexOf(x2),1);
  p.hand[k2].push(x2);t.hand[k1].push(x1);log(`    обмен вслепую с ${t.name}: получил [${k2}] «${cardText(x2)}»`,"g")}}
 else if(name==="Свидетель"){const t=pickTarget(p);const cc=closed(t);
 if(cc.length){const[k,c]=pick(cc);t.hand[k].splice(t.hand[k].indexOf(c),1);t.revealed.push([k,c]);log(`    ${t.name} раскрывает [${k}] «${cardText(c)}»`,"g")}}
 else if(name==="Второе дыхание"){st.rpds++;log(`    ${p.name} получает дополнительное РПДС`,"g")}
 else if(name==="Взятка"){st.lastRoll=(st.lastRoll||0)+3}
 else if(name==="Подстава"){const nb=bySeat(p.seat%8+1);nb.or+=1;log(`    последствие переведено на соседа слева ${nb.name}: +1 ОР`,"d");if(nb.or>=thr())death(nb,"подстава",p.name)}
 return st}
function ghostCard(g){if(!g.gcard)return;const[tag,text]=g.gcard;
 if(g.gused.includes(tag)&&["cancel","eyes","fake","voice","photo"].includes(tag)){log(`  👻 ${g.name}: карта «${cardName(text)}» уже использована`,"m");return}
 const lv=alive();if(!lv.length)return;
 log(`  👻 ${g.name} применяет карту мёртвых: «${text}»`,"y");g.gused.push(tag);g.gcard=null;
 if(tag==="knock")lv.forEach(q=>q.noRpds=true);
 else if(tag==="cold"){const q=pick(lv);q.noRpds=true;log(`    ${q.name} теряет РПДС`,"d")}
 else if(tag==="name"){const q=lv.reduce((a,b)=>b.or>a.or?b:a);q.noTarget=true;log(`    ${q.name} нельзя выбрать целью до конца цикла`,"d")}
 else if(tag==="cancel"){if(S.lastWound){const[s,a]=S.lastWound;const q=bySeat(s);q.or=Math.max(0,q.or-a);S.lastWound=null;log(`    время отмотано: ${q.name} → ${q.or} ОР`,"g")}}
 else if(tag==="buff"){const q=pick(lv);q.buff=1;log(`    ${q.name}: +1 к следующему броску`,"g")}
 else if(tag==="mirror"){const q=pick(lv);const cc=closed(q);if(cc.length){const[k,c]=pick(cc);q.hand[k].splice(q.hand[k].indexOf(c),1);q.revealed.push([k,c]);log(`    зеркало: ${q.name} раскрывает [${k}] «${cardText(c)}»`,"d")}}
 else if(tag==="eyes"){const q=pick(lv);q.skipReveal=true;log(`    ${q.name} пропускает следующее раскрытие`,"d")}
 else if(tag==="dark"){S.dark=true;log("    свет гаснет: все РПДИ до конца цикла с −1","d")}
 else if(tag==="fake"){const q=pick(lv);if(S.draw["ИНВЕНТАРЬ"].length){const c=S.draw["ИНВЕНТАРЬ"].pop();q.hand["ИНВЕНТАРЬ"].push(c);log(`    фантомный предмет у ${q.name}: «${cardText(c)}»`,"g")}}
 else if(tag==="voice"){const q=pick(lv);if(q.obmen){q.obmen=null;log(`    ${q.name} сбрасывает карту обмена`,"d")}else{const cc=closed(q);if(cc.length){const[k,c]=pick(cc);q.hand[k].splice(q.hand[k].indexOf(c),1);q.revealed.push([k,c])}}}
 else if(tag==="pain"){const h=lv.filter(q=>q.or>=1&&q.healTaken<1);if(h.length){const q=h.reduce((a,b)=>b.or>a.or?b:a);q.or--;q.healTaken++;log(`    боль уходит: ${q.name} → ${q.or} ОР`,"g")}}
 else if(tag==="photo"){lv.forEach(q=>{const cc=closed(q);if(cc.length){const[k,c]=pick(cc);q.hand[k].splice(q.hand[k].indexOf(c),1);q.revealed.push([k,c]);log(`    фото: ${q.name} раскрывает [${k}] «${cardText(c)}»`,"d")}})}
 else if(tag==="queue"){S.queueShift=true}
 else if(tag==="whisper"){log(`    шёпот для ${pick(lv).name} (чистый вкус)`,"m")}}
function ghostBets(){for(const g of ghosts()){if(g.tokens>=1&&R()<0.85){
 const n=alive().length;const k=n>=6?pickW([[0,1],[1,5],[2,2]]):pickW([[1,2],[2,4],[3,2]]);
 let stake=g.tokens<3?1:pick([1,2]);stake=Math.min(stake,g.tokens);g.tokens-=stake;g.bet=[stake,k];
 log(`  👻 ${g.name} ставит ${stake} жетон(а) на «ровно ${k} смертей в цикле»`,"y")}else g.bet=null}}
function resolveBets(cd){for(const g of ghosts()){if(!g.bet)continue;const[st,k]=g.bet;
 if(k===cd){g.tokens+=st*2;S.betHits++;log(`  👻 СТАВКА СЫГРАЛА: ${g.name} угадал «${k}» → +${st*2} жетонов (итого ${g.tokens})`,"g")}
 else log(`  👻 ставка ${g.name} мимо: было ${cd}, жетоны сгорели`,"m");g.bet=null}}
function ghostShop(){for(const g of ghosts()){const lv=alive();if(!lv.length)continue;
 if(g.tokens>=3&&R()<0.4){g.tokens--;const q=pick(lv);log(`  👻 магазин: ${g.name} подсматривает карты ${q.name} (жетонов ${g.tokens})`,"y")}
 if(g.tokens>=2&&R()<0.25){g.tokens-=2;const q=pick(lv);const cc=closed(q);
 if(cc.length){const[k,c]=pick(cc);q.hand[k].splice(q.hand[k].indexOf(c),1);q.revealed.push([k,c]);log(`  👻 магазин: принудительно раскрыта карта ${q.name}: [${k}] «${cardText(c)}»`,"d")}}}}
function tokenRevive(){const gs=ghosts().filter(g=>g.died!==null&&S.cycle-g.died>=1);if(!gs.length)return;
 const total=gs.reduce((s,g)=>s+g.tokens,0);const medik=alive().some(p=>p.prof[0]==="Медик");
 if(total>=6&&(medik||R()<0.5)){gs.sort((a,b)=>a.died-b.died||a.seat-b.seat);const r=gs[0];
 gs.forEach(g=>g.tokens=0);r.alive=true;r.or=0;r.resurrected=true;S.tokenRevive=true;
 log(`  ✝️ ВОСКРЕШЕНИЕ: призраки скидывают ${total} жетонов (нужно 6) — ${r.name} возвращается с 0 ОР. Лишние жетоны сгорают.`,"g")}}
function useSpec(p,st){if(p.usedSpec)return;const[tag,text]=p.spec;const lv=alive();
 if(tag==="additem"&&S.cycle===2){p.usedSpec=true;if(S.draw["ИНВЕНТАРЬ"].length){const c=S.draw["ИНВЕНТАРЬ"].pop();p.hand["ИНВЕНТАРЬ"].push(c);log(`  ⚡ СПЕЦКАРТА ${p.name}: «${text}» → [ИНВЕНТАРЬ] «${cardText(c)}»`,"y")}}
 else if(tag==="extra"&&S.cycle===3){p.usedSpec=true;st.rpdi++;log(`  ⚡ СПЕЦКАРТА ${p.name}: «${text}» (+1 РПДИ в этом ходу)`,"y")}
 else if(tag==="immune"&&S.cycle===3&&R()<0.8){p.usedSpec=true;p.immune=S.cycle;log(`  ⚡ СПЕЦКАРТА ${p.name}: «${text}»`,"y")}
 else if(tag==="lootdead"&&S.cycle>=3&&ghosts().length){const g=pick(ghosts());const cc=closed(g);
 if(cc.length){p.usedSpec=true;const[k,c]=pick(cc);g.hand[k].splice(g.hand[k].indexOf(c),1);p.hand[k].push(c);
 log(`  ⚡ СПЕЦКАРТА ${p.name}: снимает с трупа ${g.name} карту [${k}] «${cardText(c)}»`,"y")}}
 else if(tag==="fullheal"&&S.cycle===4){const h=lv.filter(q=>q.or>=1);if(h.length){p.usedSpec=true;const q=h.reduce((a,b)=>b.or>a.or?b:a);q.or=0;log(`  ⚡ СПЕЦКАРТА ${p.name}: ${q.name} полностью вылечен (ОР→0)`,"y")}}
 else if(tag==="avoid"&&S.cycle===4){p.usedSpec=true;p.specArmed=true;log(`  ⚡ СПЕЦКАРТА ${p.name}: следующая смерть будет отменена`,"y")}
 else if(tag==="revive"&&S.cycle>=5&&ghosts().length&&!S.specRevive){const r=ghosts().sort((a,b)=>a.died-b.died)[0];
 p.usedSpec=true;r.alive=true;r.or=0;r.debuff=true;r.resurrected=true;S.specRevive=true;log(`  ⚡ СПЕЦКАРТА ${p.name}: воскрешает ${r.name} с дебафом −1 РПД навсегда`,"y")}
 else if(tag==="autohit"&&S.cycle>=5){const cand=lv.filter(q=>q!==p);if(cand.length){p.usedSpec=true;
 const t=cand.reduce((a,b)=>b.or>a.or?b:a);log(`  ⚡ СПЕЦКАРТА ${p.name}: РАНЕНИЕ ${t.name} со 100% (бросок не нужен)`,"y");wound(t,2,p.name)}}}
function massAction(p){const cs=S.P.filter(q=>q.alive&&q!==p&&!q.noTarget);if(cs.length<2)return false;
 const ts=shuffle(cs.slice()).slice(0,2);
 log(`  ${p.name}: МАССОВОЕ РАНЕНИЕ против ${ts[0].name} и ${ts[1].name} (порог 18–20)`);
 const nat=RI(20),eff=modRoll(p,nat,"mass");log(`    d20=${nat}${eff!==nat?" (с мод. "+eff+")":""}`);
 if(eff>=18){ts.forEach(t=>wound(t,1,p.name));log("    УСПЕХ массовки: каждой цели +1 ОР","g")}
 else{log("    ПРОВАЛ массовки: атакующему +2 ОР","d");wound(p,2,"self")}
 S.massDone=true}
function botRPDI(p){const gs=ghosts().length;
 if(S.cycle===1)return pickW([["hum",35],["wound",25],["steal",15],["skip",20],["heal",5]]);
 if(S.cycle===2)return pickW([["wound",30],["kill",25],["steal",12],["hum",13],["heal",10],["skip",10]]);
 if(S.cycle===3)return pickW([["wound",18],["kill",6],["steal",12],["hum",14],["heal",12],["skip",28],["marauder",gs?10:0]]);
 if(S.cycle===4)return pickW([["wound",24],["kill",16],["steal",10],["hum",10],["heal",10],["skip",15],["marauder",gs?10:0],["mass",!S.massDone?10:0]]);
 return pickW([["wound",26],["kill",30],["steal",8],["hum",6],["heal",8],["skip",10],["marauder",gs?12:0]])}
function doRPDI(p,act,st){
 if(act==="skip"){log("    РПДИ сэкономлено","m");st.rpdi--;return true}
 if(act==="mass"){massAction(p);st.rpdi--;return true}
 if(act==="marauder"){const gs=ghosts();if(!gs.length)return false;const g=pick(gs);const cc=closed(g);
  if(!cc.length){log("    на трупе пусто","m");st.rpdi--;return true}
  log(`    РПДИ-мародёрство: тянет карту с трупа ${g.name}`);
  tableB(p,"мародёрство",()=>{const[k,c]=pick(closed(g));g.hand[k].splice(g.hand[k].indexOf(c),1);p.hand[k].push(c);log(`    УСПЕХ: добыча [${k}] «${cardText(c)}»`,"g")},
   ()=>log("    ПРОВАЛ: труп не отдаёт","m"));st.rpdi--;return true}
 if(act==="heal"){const t=alive().filter(q=>q!==p&&q.or>=1&&q.healTaken<1).sort((a,b)=>b.or-a.or)[0];
  if(!t){st.rpdi--;return true}log(`    РПДИ: лечение ${t.name}`);healAct(p,t);st.rpdi--;return true}
 if(act==="steal"){let t=pickTarget(p);if(t===p){st.rpdi--;return true}
  log(`    РПДИ: ${p.name==="Вор"||p.prof[0]==="Вор"?"кража (профессия Вор)":"кража"} у ${t.name} вслепую`);steal(p,t);st.rpdi--;return true}
 if(act==="hum"){let t=pickTarget(p);if(t===p){st.rpdi--;return true}t=cascade(p,t);log(`    РПДИ: унижение ${t.name}`);humiliate(p,t);st.rpdi--;return true}
 let t=pickTarget(p);if(t===p){st.rpdi--;return true}t=cascade(p,t);
 const decl=act==="kill"?"УБИЙСТВО":"РАНЕНИЕ";tableA(p,decl,t);st.rpdi--;return true}
const HUMAN_MAP={"РАНЕНИЕ":"wound","УБИЙСТВО":"kill","КРАЖА":"steal","ПОЗОР":"hum","ЛЕЧЕНИЕ":"heal","МАССОВОЕ":"mass","ПРОПУСК":"skip"};
function turnStart(p){
 log(`\n——— P${p.seat} ${p.name} (${p.prof[0]}), ОР=${p.or} ———`);
 if(p.skipReveal){p.skipReveal=false;log("  раскрытие пропущено (Ладонь на глазах)","m")}else reveal(p,S.cycle===1?2:1);
 const st={rpds:p.noRpds?0:1,rpdi:p.debuff?0:1};
 if(p.noRpds){log("  РПДС недоступно (карта мёртвых)","d");p.noRpds=false}
 return st}
function turnRpds(p,st){if(st.rpds<=0)return Promise.resolve();
 if(p.or>=1&&R()<0.55){log("    РПДС: самолечение");rpdsHeal(p)}
 else if(p.prof[0]==="Стример"&&R()<0.6){log("    РПДС+«Стример»: стрим с донатами");rpdsStream(p)}
 else if(R()<0.75){rpdsWorld(p)}
 else log("    РПДС: сэкономлено (копит на карту обмена)","m")
 st.rpds=0;return Promise.resolve()}
function turnBody(p){ /* весь ход одного игрока как цепочка */
 const st=turnStart(p);
 return turnRpds(p,st).then(()=>{
  useSpec(p,st);
  return new Promise(res=>{
   const loop=()=>{
    if(st.rpdi<=0){ // обменки (боты применяют с вероятностью, как в симуляторе)
     if(p.obmen&&!isHumanSeat(p)){const w=p.obmen[0];
      const needRpdi=["Обмен","Свидетель","Подстава"].includes(w);
      if(!needRpdi||st.rpdi>0){
       const want=(w==="Парамедик"&&p.or>=1&&p.healTaken<1)||(w==="Отмена"&&S.lastWound&&S.lastWound[0]===p.seat&&p.or>=1);
       const maybe=["Заначка","Обмен","Свидетель","Второе дыхание","Подстава"].includes(w)&&R()<0.45;
       if(want||maybe)useObmen(p,st)}}
     res();return}
    if(isHumanSeat(p)){showHumanButtons(p,st,loop)}
    else{const act=botRPDI(p);if(!doRPDI(p,act,st))st.rpdi=0;setTimeout(loop,40)}
   };loop()})}).then(()=>{render()})}
function isHumanSeat(p){return HUMAN&&p.seat===1&&p.alive}
function showHumanButtons(p,st,done){const el=document.getElementById("action");
 const acts=Object.keys(HUMAN_MAP).filter(a=>!(a==="МАССОВОЕ"&&S.massDone));
 el.innerHTML=`<h3>Твой ход: ${p.name} (ОР=${p.or}, РПДИ осталось ${st.rpdi})</h3>`+
 acts.map(a=>`<button onclick="humanAct('${a}')">${a}</button>`).join("");
 window._ha=(act)=>{window._ha=null;el.innerHTML="";if(!doRPDI(p,HUMAN_MAP[act],st))st.rpdi=0;done()}}
window.humanAct=a=>window._ha(a);
function endCycle(){
 log(`  Конец цикла ${S.cycle}: карты обмена и мёртвых уходят в сброс`,"m");
 // ставки призраков считаются ДО жатвы (по смертям от действий игроков), как в симуляторе
 resolveBets(S.cycleDeaths);
 if(S.cycle>=2&&harvestOn()&&!S.playerDeath&&alive().length>=2){
  const v=pick(alive());log(`  🌾 ЖАТВА: никто не умер от игроков — умирает ${v.name} (место ${v.seat})`,"y");
  death(v,"жатва","Жатва");S.harvest=true}
 log(`  Живых после цикла ${S.cycle}: ${alive().length} (цель — довести до 4, S=4)`,"m");
 // условие победы проверяется ПОСЛЕ всех смертей цикла (включая Жатву) — иначе партия не завершится никогда
 if(alive().length<=4){finish();return Promise.resolve(false)}
 if(S.cycle>=10){finish();return Promise.resolve(false)}
 ghosts().forEach(g=>g.gcard=null);S.P.forEach(p=>p.obmen=null);
 S.cycle++;S.idx=0;S.playerDeath=false;S.dark=false;S.lastWound=null;S.queueShift=null;S.cycleDeaths=0;
 S.P.forEach(p=>{p.healTaken=0;p.noTarget=false});
 log(`\n════════ ЦИКЛ ${S.cycle} ════════`,"y");
 log(`  Начало цикла: живых ${alive().length}, призраков ${ghosts().length}`,"m");
 for(const g of ghosts()){g.tokens++;log(`  👻 ${g.name}: +1 жетон (итого ${g.tokens})`,"m");
  if(S.tenyDraw.length){g.gcard=S.tenyDraw.pop();log(`  👻 ${g.name} тянет карту мёртвых: «${cardName(g.gcard[1])}…»`,"m")}}
 ghostBets();ghostShop();ghosts().forEach(ghostCard);
 if(S.cycle>=2)for(const p of alive()){p.obmen=pick(OBMEN);log(`  🎴 ${p.name} тянет карту обмена «${p.obmen[0]}»`,"m")}
 if(S.cycle>=4)tokenRevive();
 // ротация очереди: первый ходящий становится последним
 if(S.queueShift&&alive().length>1){const a=alive().slice();const first=a.shift();a.push(first);S.order=a;
  log("  (очередь сдвинута картой мёртвых «Место в очереди»)","m")}else S.order=null;
 render();return Promise.resolve(true)}
function cycleLoop(){
 if(S.over)return;
 const order=S.order||alive();
 if(S.idx>=order.length){endCycle().then(cont=>{if(cont)setTimeout(cycleLoop,300)});return}
 const p=order[S.idx];
 if(!p.alive){S.idx++;return cycleLoop()}
 S.cur=p;render();
 turnBody(p).then(()=>{S.cur=null;S.idx++;render();setTimeout(cycleLoop,60)})}
function finish(){S.over=true;
 const win=alive().map(p=>`${p.name} (${p.prof[0]}, ОР=${p.or})`).join("; ");
 log(`\n════════ ИТОГ ════════`,"y");
 log(alive().length?`Победили: ${win}`:"Все мертвы — побеждают призраки");
 log(`first_death=${S.firstDeath} end=${S.cycle} harvest=${S.harvest?"была":"не была"} bets_hit=${S.betHits} revive=${S.tokenRevive?"жетонами":"нет"} deaths=${S.deaths}`,"m");
 document.getElementById("action").innerHTML=`<button onclick="location.reload()">🔄 Новая партия</button>`;render()}
function startGame(human){
 HUMAN=human;VARIANT=document.getElementById("variant").value;
 const sInp=document.getElementById("seedInp").value.trim();
 seed=sInp?parseInt(sInp,10):RI(999999);rnd=mulberry32(seed);
 S={cycle:1,idx:0,deaths:0,firstDeath:null,endCycle:null,playerDeath:false,dark:false,lastWound:null,
    harvest:false,betHits:0,tokenRevive:false,specRevive:false,massDone:false,queueShift:null,
    cycleDeaths:0,over:false,cur:null,draw:{},tenyDraw:shuffle(TENY.slice()),P:[],order:null};
 CATS.forEach(c=>S.draw[c]=shuffle(DECKS[c].slice()));
 const specOrder=shuffle(SPECS.slice());
 for(let i=0;i<8;i++){const hand={};CATS.forEach(c=>hand[c]=[S.draw[c].pop()]);
  S.P.push({seat:i+1,name:NAMES[i],prof:PROFS[i],hand,revealed:[],alive:true,or:0,spec:specOrder[i],usedSpec:false,specArmed:false,
   tokens:0,gcard:null,gused:[],bet:null,obmen:null,healTaken:0,noRpds:false,noTarget:false,skipReveal:false,buff:0,debuff:false,
   died:null,resurrected:false,kills:0,immune:-1,crCycle:-1,lastDeaths:0})}
 const post=S.P.find(p=>p.prof[0]==="Почтальон");
 if(post&&S.draw["ИНВЕНТАРЬ"].length)post.hand["ИНВЕНТАРЬ"].push(S.draw["ИНВЕНТАРЬ"].pop());
 S.P.forEach(p=>p.obmen=pick(OBMEN));
 document.getElementById("menu").style.display="none";document.getElementById("game").style.display="block";
 log(`ПАРТИЯ «БЛИЦ БОЙ» — 8 игроков, seed=${seed}, вариант=${VARIANT}${human?" (ты играешь за P1)":" (все — боты)"}`,"y");
 log(`СИТУАЦИЯ: «Ночь в панельке» — раскрытие 1 карта/ход (в 1-м цикле 2), действия 1 РПДС + 1 РПДИ, конец при 4 живых`,"m");
 log(`\n════════ ЦИКЛ 1 ════════`,"y");
 render();setTimeout(cycleLoop,150)}
function render(){
 document.getElementById("status").innerHTML=`<b>Цикл ${S.cycle}</b> · живых ${alive().length}/8 · seed=${seed} · порог ОР=${thr()}${HUMAN?" · ты P1":""}`;
 const el=document.getElementById("seats");el.innerHTML="";
 S.P.forEach(p=>{const d=document.createElement("div");d.className="seat"+(p.alive?"":" dead")+(S.cur===p?" cur":"");
  d.innerHTML=`P${p.seat} <b>${p.name}</b> <span class="small">${p.prof[0]}</span><br>ОР: <span class="or">${p.or}</span>`+
  (p.alive?"":` 👻 жетоны: ${p.tokens}`)+(p.obmen?`<span class="tag">🃏 ${p.obmen[0]}</span>`:"")+
  (p.usedSpec?`<span class="tag">⚡</span>`:"")+
  `<div class="revs">${p.revealed.slice(-3).map(r=>`[${r[0]}] ${cardText(r[1]).slice(0,28)}`).join("<br>")}</div>`;
  el.appendChild(d)})}
function showDecks(){const el=document.getElementById("decks");el.style.display="block";
 el.innerHTML="<h3>Канон: 7 колод × 24 карты + Тень + Обмен</h3>"+CATS.map(c=>`<div class="small"><b>${c}:</b> ${DECKS[c].map(cardText).join(" · ")}</div>`).join("")+
 `<div class="small"><b>Карты мёртвых (Тень):</b> ${TENY.map(t=>t[1].split(" — ")[0]).join(" · ")}</div>`+
 `<div class="small"><b>Карты обмена:</b> ${OBMEN.map(o=>o[0]).join(", ")}</div>`+
 `<div class="small"><b>Профессии:</b> ${PROFS.map(p=>p[0]).join(", ")}</div>`}
function showRules(){const el=document.getElementById("decks");el.style.display="block";
 el.innerHTML=`<h3>Краткие правила (v3)</h3><div class="small">
 8 игроков, колоды 7 категорий × 24 карты. Каждый цикл: каждый живой раскрывает 1 карту (в 1-м цикле 2), делает 1 РПДС (себя/мир) и 1 РПДИ (на других).
 Бросок d20 по таблицам А (РПДИ на цель), Б (кража/лечение/позор: успех 15+, провал ≤10, обратный эффект), В (РПДС: успех 11+, провал ≤9).
 3 ОР = смерть. Если в цикле с цикла 2 никто не умирал от рук игроков — ЖАТВА забирает случайного. Мёртвые становятся призраками: +1 жетон/цикл, тянут карту мёртвых (Тень), ставят на число смертей цикла, покупают эффекты в магазине мёртвых. 6 жетонов общаком = воскрешение (цикл 4+). Игра кончается, когда живых остаётся 4 (S=4) — они побеждают.</div>`}
</script></body></html>"""

out = HTML.replace('__DATA__', DATA)
open('game.html', 'w', encoding='utf-8').write(out)
print('game.html written:', len(out), 'bytes')
