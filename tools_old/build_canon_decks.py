# -*- coding: utf-8 -*-
"""Собирает КАНОННЫЕ колоды (по 24 карты каждой категории) из canon/cards_*.md.

Это единственный источник карт по версии пользователя: 7 категорий × 24 карты.
Старый final_v5.json (колоды на сотни карт из xlsx v4) больше НЕ используется.

Выход: canon/decks.json вида {"ТЕЛО": ["1 Ангел...", ...], ..., "ОБМЕН": [...], "ТЕНЬ": [...]}
Профессии и спецкарты берутся прямо из game_sim.py (там они с механиками), но их
списки названий тоже сохраняются для справки/вьюера.
"""
import json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
CANON = os.path.join(ROOT, '..', 'src', 'canon')

CATS = {
    'cards_body.md': 'ТЕЛО',
    'cards_mind.md': 'РАЗУМ',
    'cards_abilities.md': 'СПОСОБНОСТИ',
    'cards_inventory.md': 'ИНВЕНТАРЬ',
    'cards_history.md': 'ИСТОРИЯ',
    'cards_knowledge.md': 'ЗНАНИЯ',
    'cards_details.md': 'ДЕТАЛИ',
}

def load_numbered(fname):
    """Читает md-файл, возвращает список строк вида 'N Текст' (номера 1..24)."""
    out = {}
    with open(os.path.join(CANON, fname), encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^(\d{1,2})\s+(.*\S)\s*$', line.strip())
            if not m:
                continue
            n = int(m.group(1))
            if 1 <= n <= 24 and n not in out:
                # обрезаем пометки вида "← ДУБЛЬ..." только у теней, там они в тексте
                out[n] = f"{n} {m.group(2)}"
    return [out[i] for i in sorted(out)]

decks = {}
for fname, cat in CATS.items():
    cards = load_numbered(fname)
    assert len(cards) == 24, f'{cat}: ожидалось 24 карты, получено {len(cards)}'
    decks[cat] = cards

# Тени (карты мёртвых) — 24, но в файле есть пометки «← ДУБЛЬ...» — чистим хвосты
sh = []
for c in load_numbered('cards_shadows.md'):
    c = re.sub(r'\s*←.*$', '', c)
    c = re.sub(r'\s*\[sic.*$', '', c)
    sh.append(c.strip())
decks['ТЕНЬ'] = sh
assert len(sh) == 24

# Обмен — состав из файла (не нумерованный список, а итоговая раскладка 24 копий)
decks['ОБМЕН'] = (
    ['Потратьте неиспользованное РП-действие на себя, чтобы обратить любое РП-действие, направленное на вас'] * 5 +
    ['Можно обменять неиспользованные РП действия на любую карту характеристик'] * 3 +
    ['Можно обменять неиспользованные РП действия на другое РП действие'] * 1 +
    ['Замените неиспользованное РПД или РПДС на взятие новой спецкарты'] * 2 +
    ['В следующий раз повезет'] * 9 +
    ['Потратьте неиспользованное РП-действие на себя, чтобы спасти игрока от использования на него РП-действия на игроков'] * 4
)
assert len(decks['ОБМЕН']) == 24, len(decks['ОБМЕН'])

json.dump(decks, open(os.path.join(CANON, 'decks.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('OK:', {k: len(v) for k, v in decks.items()})
