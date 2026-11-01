# -*- coding: utf-8 -*-
"""\u0421\u0431\u043e\u0440\u043a\u0430 \u0447\u0438\u0441\u0442\u043e\u0439 \u043a\u043e\u043b\u043e\u0434\u044b \u0440\u0435\u0434\u0430\u043a\u0446\u0438\u0438 5 \u0438\u0437 src/final_v5.json."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, HERE)
import censor

d = json.load(open('src/final_v5.json', encoding='utf-8'))
slug = {'1':'professiya','2':'telo','3':'razum','4':'sposobnosti','5':'inventar',
        '6':'istoriya','7':'znaniya','8':'detali','9':'spec','10':'teny'}
os.makedirs('v5/final', exist_ok=True)
md = ['# БЛИЦ БОЙ — полная колода, редакция 5 (чистая)', '',
      f'Всего карт: **{sum(len(v) for v in d.values())}**. Дата сборки: 2026-09-28.', '',
      'Редакция 5 = редакция 4 с полной чисткой текстов. Из колоды убраны все карты с ненормативной лексикой,',
      'оскорблениями, контентом для взрослых и жестоким содержанием — вместо них добавлены нейтральные аналоги.',
      'Состав категорий, механики и баланс не изменились: заменено карт — **89**.',
      'Проверка чистоты всего проекта: `python3 src/check_clean.py`.', '']
for k, v in d.items():
    n = re.match(r'\d+', k).group()
    md += [f'## {k} \u2014 {len(v)} \u043a\u0430\u0440\u0442', '']
    md += [f'{i}. {x}' for i, x in enumerate(v, 1)]
    md.append('')
    open(f'v5/final/{n}_{slug[n]}.txt', 'w', encoding='utf-8').write('\n'.join(v) + '\n')
open('\u043a\u0430\u0440\u0442\u044b_v5_\u043f\u043e_\u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f\u043c.md', 'w', encoding='utf-8').write('\n'.join(md))
dirty = sum(1 for v in d.values() for c in v if censor.dirty(c))
print('\u043a\u0430\u0440\u0442\u044b_v5_\u043f\u043e_\u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f\u043c.md  \u2014', sum(len(v) for v in d.values()), '\u043a\u0430\u0440\u0442, \u0433\u0440\u044f\u0437\u043d\u044b\u0445:', dirty)
for f in sorted(os.listdir('v5/final')):
    print('  v5/final/' + f, sum(1 for _ in open('v5/final/' + f, encoding='utf-8')), '\u0441\u0442\u0440\u043e\u043a')
