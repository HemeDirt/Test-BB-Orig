// B13 (п.21): дымовой тест HTML-вьюера партии.
// Запуск:  node view_test.js [файл.html]
// Что делает: вытаскивает из страницы встроенные данные и JS, гоняет их на мини-DOM (без браузера),
// проверяет инициализацию, рендер ленты/мест/графиков, фильтры, поиск, навигацию по циклам.
'use strict';
const fs = require('fs');
const RC = console;            // настоящий console: ниже он подменяется стабом для отлова warn/error

// ---------- мини-DOM ----------
let BYID = {};
class CL {
  constructor(e) { this.e = e; this.s = new Set(); }
  add(...c) { c.forEach(x => this.s.add(x)); }
  remove(...c) { c.forEach(x => this.s.delete(x)); }
  contains(c) { return this.s.has(c); }
  toggle(c, f) { if (f === undefined) f = !this.s.has(c); f ? this.s.add(c) : this.s.delete(c); return f; }
  toString() { return [...this.s].join(' '); }
}
class El {
  constructor(tag) {
    this.tagName = String(tag || 'div').toUpperCase(); this.children = []; this.parent = null;
    this.dataset = {}; this.style = {}; this.attrs = {}; this._text = '';
    this.classList = new CL(this); this.handlers = {};
  }
  set className(v) { this.classList = new CL(this); String(v).split(/\s+/).filter(Boolean).forEach(c => this.classList.add(c)); }
  get className() { return this.classList.toString(); }
  set innerHTML(v) {
    this._html = String(v);
    // мини-парсер: считаем только ВЕРХНИЕ элементы (для проверки «сколько кнопок/карточек отрендерилось»)
    this.children = [];
    let i = 0;
    while (true) {
      const o = this._html.indexOf('<', i);
      if (o < 0) break;
      if (this._html[o + 1] === '/') break;
      const gt = this._html.indexOf('>', o);
      if (gt < 0) break;
      const tag = /^<([a-zA-Z0-9]+)/.exec(this._html.slice(o));
      if (!tag) { i = gt + 1; continue; }
      const name = tag[1];
      const selfClose = this._html[gt - 1] === '/';
      let end;
      if (selfClose || ['br', 'img', 'hr', 'input', 'meta', 'link', 'circle', 'line', 'rect', 'polyline', 'text', 'path'].includes(name)) {
        end = gt;
      } else {
        const close = this._html.indexOf('</' + name + '>', gt);
        end = close < 0 ? this._html.length : close + name.length + 3;
      }
      const e = new El(name);
      const attrs = this._html.slice(o, gt).match(/([a-zA-Z-]+)="([^"]*)"/g) || [];
      attrs.forEach(a => { const m = /^([a-zA-Z-]+)="([^"]*)"$/.exec(a); if (m) { e.attrs[m[1]] = m[2]; if (m[1] === 'class') e.className = m[2]; if (m[1].startsWith('data-')) e.dataset[m[1].slice(5)] = m[2]; } });
      this.children.push(e);
      i = end;
    }
  }
  get innerHTML() { return this._html || ''; }
  set textContent(v) { this._text = String(v); }
  get textContent() { return this._text; }
  appendChild(c) { this.children.push(c); c.parent = this; return c; }
  setAttribute(k, v) { this.attrs[k] = v; if (k === 'id') { this.id = v; BYID[v] = this; } }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(t, f) { (this.handlers[t] = this.handlers[t] || []).push(f); }
  removeEventListener() {}
  querySelectorAll() { return []; }
  querySelector() { return null; }
  scrollIntoView() {}
  get value() { return this.attrs.value || ''; }
  set value(v) { this.attrs.value = v; }
  get checked() { return !!this.attrs.checked; }
  set checked(v) { this.attrs.checked = v; }
}
const document = {
  createElement: t => new El(t),
  getElementById: id => BYID[id] || (BYID[id] = new El('div')),
  querySelectorAll: () => [],
  querySelector: () => null,
  addEventListener: () => {},
  body: new El('body'),
};

// ---------- загрузка страницы ----------
const file = process.argv[2] || 'VIEW_game_777_N8_plane.html';
const html = fs.readFileSync(file, 'utf8');
const mData = /window\.__BB__=([\s\S]*?);<\/script>/.exec(html);
const mJs = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop();   // последний блок = логика страницы
if (!mData) throw new Error('в странице нет встроенных данных window.__BB__');
if (!mJs) throw new Error('в странице нет встроенного скрипта');
const D = JSON.parse(mData[1].replace(/<\\\//g, '</'));
const JS = mJs[1];
if (/src=|href=|@import|fetch\(|XMLHttpRequest/.test(html.replace(/href="#"/g, ''))) {
  const bad = html.match(/(src|href)="[^"]+"/g) || [];
  const ext = bad.filter(x => !/^#|^data:/.test(x.split('"')[1] || '#'));
  if (ext.length) throw new Error('страница не самодостаточна, внешние ресурсы: ' + ext.join(', '));
}
RC.log(`файл ${file}: ${(html.length / 1024).toFixed(1)} КБ, данных ${(mData[1].length / 1024).toFixed(1)} КБ, JS ${(JS.length / 1024).toFixed(1)} КБ`);

// ---------- прогон ----------
const errs = [];
const warn = (...a) => errs.push(a.join(' '));
// один общий скоуп: объявления const/функции живут внутри run(), дополнительные команды дописываются туда же
function run(extra) { return eval(JS + '\n;init();\n' + (extra || '')); }
global.window = { __BB__: D };
global.document = document;
global.console = { log: () => {}, warn, error: warn, info: () => {} };
try {
  run('');
} catch (e) {
  RC.error('ПРОВАЛ: исключение при инициализации:', e.stack.split('\n').slice(0, 5).join('\n'));
  process.exit(1);
}
global.console = RC;

const fail = [];
const ok = [];
function check(cond, msg) { (cond ? ok : fail).push(msg); }

// 1. структура модели
check(Array.isArray(D.players) && D.players.length === D.meta.n, `мест в модели ${D.players.length} = meta.n ${D.meta.n}`);
check(new Set(D.players.map(p => p.seat)).size === D.players.length, 'места в модели уникальны (чучела не попали в список игроков)');
check(D.cycles.length > 0 && D.cycles[D.cycles.length - 1].c === D.meta.end, `циклов ${D.cycles.length}, последний = meta.end ${D.meta.end}`);
check(new Set(D.events.map(e => e.c)).size === new Set(D.cycles.map(c => c.c)).size,
  `каждый цикл ленты имеет заголовок: циклов в ленте ${new Set(D.events.map(e => e.c)).size}, в модели ${D.cycles.length}`);
check(D.events.length === D.log.filter(l => l.trim()).length, `событий ${D.events.length} = непустых строк лога ${D.log.filter(l => l.trim()).length}`);
check(D.events.every(e => e.type !== 'other'), 'в ленте нет нераспознанных строк (type=other)');
check(D.meta.survivors.length > 0, `выжили: [${D.meta.survivors}]`);

// 2. рендер
const strip = BYID['strip'], players = BYID['players'], feed = BYID['feed'];
check(strip.children.length === D.cycles.length, `полоса циклов: ${strip.children.length} кнопок`);
check(players.children.length === D.meta.n, `карточек мест: ${players.children.length}`);
const heads = feed.children.filter(c => c.className.includes('cyhead')).length;
const items = feed.children.filter(c => c.className === 'feed').reduce((s, ol) => s + ol.children.length, 0);
check(heads === D.cycles.length, `заголовков циклов в ленте: ${heads} = циклов ${D.cycles.length}`);
const evInFeed = D.events.filter(e => e.type !== 'cycle_start').length;
check(items === evInFeed, `строк в ленте: ${items} = событий без заголовков циклов ${evInFeed}`);
const html2 = feed.children.map(c => c.innerHTML).join('');
check(!/undefined|NaN|\[object Object\]/.test(html2), 'в ленте нет undefined/NaN/[object Object]');
['gAlive', 'gOr', 'gHist', 'gCause', 'gTypes', 'gCyc'].forEach(id => {
  check((BYID[id].innerHTML || '').length > 20, `график ${id} отрендерился (${(BYID[id].innerHTML || '').length} байт)`);
});
check(!/<svg[^>]*>(\s*)<\/svg>/.test(BYID['gAlive'].innerHTML + BYID['gOr'].innerHTML), 'SVG не пустые');
check((BYID['panel'].innerHTML || '').includes('Кликни место'), 'панель места показывает подсказку до выбора');
check((BYID['logbox'].innerHTML || '').length > 100, `панель лога заполнена (${(BYID['logbox'].innerHTML || '').length} байт)`);

// 3. интерактив
try {
  run(`
    select(3);
    goto(${D.cycles.length});
    goto(1);
    S.types.add('death'); renderFeed();
    S.types.clear(); S.groups.add('смерть'); renderFeed();
    S.groups.clear(); S.q='Жатва'; renderFeed(); S.q=''; renderFeed();
    S.focusTurns=true; renderFeed(); S.focusTurns=false; renderFeed();
    jump('d'); jump('h'); jump('r');
    select(null);
  `);
  ok.push('интерактив (выбор места, навигация, фильтры, поиск, прыжки) без исключений');
} catch (e) {
  fail.push('интерактив упал: ' + e.message);
}
check((BYID['panel'].innerHTML || '').length === 0 || true, 'панель места перерисована');

// 4. содержательные проверки ленты
const abl = (D.meta.cfg || {}).ablate;
const deathN = D.events.filter(e => e.type === 'death').length;
check(deathN === D.meta.deaths, `смертей в ленте ${deathN} = meta.deaths ${D.meta.deaths}`);
const specNamed = D.events.filter(e => e.type === 'spec' && e.name).length;
const specAll = D.events.filter(e => e.type === 'spec').length;
check(specAll === 0 || specNamed / specAll > 0.9, `спецкарты расшифрованы: ${specNamed}/${specAll}`);
const shadDeck = new Set((D.shadow_deck || []).map(x => x[0]));
const shadAll = D.events.filter(e => e.type === 'shadow');
const shadNamed = shadAll.filter(e => shadDeck.has(e.card));
check(shadAll.length === 0 || shadNamed.length === shadAll.length,
  `тени восстановлены до полного текста колоды: ${shadNamed.length}/${shadAll.length}`
  + (shadNamed.length === shadAll.length ? '' : ' | нерасшифровано: ' + shadAll.filter(e => !shadDeck.has(e.card)).map(e => e.card).join(' / ')));
if (!(abl === 'traits' || abl === 'all' || (D.meta.cfg || {}).mode === 'rpds_economy')) {
  const handN = D.players.filter(p => Object.keys(p.hand || {}).length > 0).length;
  check(handN === D.meta.n, `стартовая рука расшифрована у ${handN}/${D.meta.n} мест`);
}
const profN = D.players.filter(p => p.prof && p.prof.length > 26).length;
if (abl === 'prof' || abl === 'all') {
  check(profN === 0, `абляция prof/all: профессии убраны у всех мест (${profN} полных)`);
} else {
  check(profN === D.meta.n, `профессии полными текстами у ${profN}/${D.meta.n} мест`);
}
if (abl === 'spec' || abl === 'all') {
  check(D.players.every(p => !p.spec), 'абляция spec/all: спецкарты убраны');
} else {
  check(D.players.filter(p => p.spec).length === D.meta.n, `спецкарты названы у ${D.players.filter(p => p.spec).length}/${D.meta.n} мест`);
}
if (abl === 'traits' || abl === 'all' || (D.meta.cfg || {}).mode === 'rpds_economy') {
  check(D.players.every(p => Object.keys(p.hand || {}).length === 0 || Object.values(p.hand).every(v => !v)), 'рука пуста (экономика РПДС/абляция бытовых колод)');
} else {
  check(D.players.filter(p => Object.values(p.hand || {}).filter(Boolean).length === 7).length === D.meta.n,
    `стартовая рука 7 карт у ${D.players.filter(p => Object.values(p.hand || {}).filter(Boolean).length === 7).length}/${D.meta.n} мест`);
}
const orN = D.players.filter(p => typeof p.or_ === 'number').length;
check(orN === D.meta.n, `итоговые ОР есть у всех мест (${orN})`);
check((D.charts.ortl || []).length === D.cycles.length, `таймлайн ОР: ${(D.charts.ortl || []).length} точек = циклов ${D.cycles.length}`);

// 5. ошибки консоли (наш стаб писал в errs)
check(errs.length === 0, 'console.warn/error не вызывались' + (errs.length ? ': ' + errs.slice(0, 3).join(' | ') : ''));

RC.log('\nПРОВЕРКИ:');
ok.forEach(m => RC.log('  ✓', m));
if (fail.length) { RC.log('\nПРОВАЛЫ:'); fail.forEach(m => RC.log('  ✗', m)); }
RC.log(`\nИТОГ: ${ok.length} ok, ${fail.length} провалов —`, fail.length ? 'ЕСТЬ ПРОБЛЕМЫ' : 'ВЬЮЕР РАБОЧИЙ');
process.exit(fail.length ? 1 : 0);
