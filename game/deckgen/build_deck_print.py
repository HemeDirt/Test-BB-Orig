# -*- coding: utf-8 -*-
"""Генератор deck_print.json из канона _archive/blitz1.1/src/canon/.
deck_print.json утрачен, восстановлен по канонным транскрипциям (md5 6f8542a7 + cards_*.md),
статус: ждёт подтверждения автором. Формат — под bb_core.DECK: CATS списки строк;
тени — пары (текст, тег); обмен — теги ОТРАТ/СПАС/ОБМЕН_КАРТА/ОБМЕН_РПД/ОБМЕН_СПЕЦ/ПУСТО
ключевое: тираж decks_canon_print.json = ОТРАТ5/СПАС4/КАРТА3/ОБМЕН_РПД1/ОБМЕН_СПЕЦ2/ПУСТО9 (=5/11/4/3/1 по группам автор+механика); строки canon-файлов с дефисом и без — один текст."""
import json, re, os, hashlib

CANON = '_archive/blitz1.1/src/canon'
CAT_FILES = {'тело':'cards_body.md','разум':'cards_mind.md','способности':'cards_abilities.md',
             'инвентарь':'cards_inventory.md','история':'cards_history.md','знания':'cards_knowledge.md',
             'детали':'cards_details.md'}
def load_md(fname):
    rows=[]
    for line in open(os.path.join(CANON,fname),encoding='utf-8'):
        m=re.match(r'^(\d+)\s+(.*)$',line.strip())
        if m: rows.append((int(m.group(1)),m.group(2)))
    assert len(rows)==24,(fname,len(rows))
    return [t for _,t in sorted(rows)]

DECK={k.lower():load_md(v) for k,v in CAT_FILES.items()}
DECK['профессии']=load_md('cards_professions.md')
DECK['спецкарты']=load_md('cards_spec.md')
# тени с тегами: берём номер карты -> тег из таблицы SH_TAGS bb_core по смыслу; читаем текст
sh_raw=[]
for line in open(os.path.join(CANON,'cards_shadows.md'),encoding='utf-8'):
    m=re.match(r'^(\d+)\s+(.*)$',line.strip())
    if m: sh_raw.append((int(m.group(1)),re.split(r'\s*←',m.group(2))[0].strip()))
assert len(sh_raw)==24,len(sh_raw)
TAGMAP={1:'reveal',2:'tok2',3:'del_closed',4:'tok1',5:'protect',6:'swap',7:'tok3',8:'give_rpd',
        9:'give_spec',10:'tok1',11:'out_turn',12:'+1',13:'+2',14:'-1',15:'-2',16:'del_open',
        17:'close',18:'cancel',19:'last',20:'lethal',21:'no_rpds',22:'redirect',23:'heal_remove',24:'reveal'}
DECK['тени']=[[t,TAGMAP.get(i,'reveal')] for i,t in sorted(sh_raw)]
# обмен: итоговый печатный состав
EXCH=[('ОТРАТ',5),('СПАС',4),('ОБМЕН_КАРТА',3),('ОБМЕН_РПД',1),('ОБМЕН_СПЕЦ',2),('ПУСТО',9)]
texts={'ОТРАТ':'Потратьте неиспользованное РП-действие на себя, чтобы обратить любое РП-действие, направленное на вас',
 'СПАС':'Потратьте неиспользованное РП-действие на себя, чтобы спасти игрока от использования на него РП-действия на игроков',
 'ОБМЕН_КАРТА':'Можно обменять неиспользованные РП действия на любую карту характеристик',
 'ОБМЕН_РПД':'Можно обменять неиспользованные РП действия на другое РП действие',
 'ОБМЕН_СПЕЦ':'Замените неиспользованное РПД или РПДС на взятие новой спецкарты',
 'ПУСТО':'В следующий раз повезет'}
DECK['обмен']=[tag for tag,cnt in EXCH for _ in range(cnt)]
assert len(DECK['обмен'])==24
DECK['_meta']={'source':'_archive/blitz1.1/src/canon (decks.json md5 6f8542a7 + cards_*.md)',
 'status':'deck_print.json утрачен, восстановлен из canon, ждёт подтверждения автором',
 'exchange_tirazh':{'ОТРАТ':5,'СПАС':4,'ОБМЕН_КАРТА':3,'ОБМЕН_РПД':1,'ОБМЕН_СПЕЦ':2,'ПУСТО':9}}
json.dump(DECK,open('game/deck_print.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('OK game/deck_print.json,', {k:len(v) for k,v in DECK.items() if isinstance(v,list)})
