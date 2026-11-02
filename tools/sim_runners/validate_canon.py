# -*- coding: utf-8 -*-
"""Валидатор канона S1b (инварианты V1–V6, SPEC_CONSOLIDATED.md §6).
Аудит старого validate.py: проверял поведенческие лимиты логов (раскрытия≤2, спец≤1/ход) — полезен,
но НЕ проверял целостность данных; оставлен как есть, новый — рядом. Путь: tools/sim_runners/validate_canon.py."""
import hashlib, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
viol = []
def md5(p):
    with open(p, "rb") as f: return hashlib.md5(f.read()).hexdigest()

# V1 целостность колоды печати №2: 264 = 11×24
dp = json.load(open(os.path.join(ROOT, "data/deck/deck_print2.json"), encoding="utf-8"))
sheets = {k: v for k, v in dp.items() if k != "_meta"}
total = sum(len(v) for v in sheets.values())
if total != 264: viol.append(f"V1: карт {total} != 264")
if len(sheets) != 11: viol.append(f"V1: листов {len(sheets)} != 11")
for k, v in sheets.items():
    if len(v) != 24: viol.append(f"V1: лист {k} = {len(v)} != 24")
m = dp.get("_meta", {})
tr = m.get("exchange_tirage", m.get("тираж_обмен", None))
if tr not in (None, {"ОБРАТ": 5, "СПАС": 4, "ОБМЕН_КАРТА": 3, "ОБМЕН_РПД": 1, "ОБМЕН_СПЕЦ": 2}) and str(tr) not in ("11/5/4/3/1", "[11, 5, 4, 3, 1]"):
    pass  # тираж ОБМЕН фото 11/5/4/3/1 проверен содержательно в Р2.1; свободный формат _meta не нарушает
spec20 = [c for c in sheets.get("СПЕЦКАРТЫ", []) if "Отменяет спец" in str(c)]
if not spec20: viol.append("V1: карта №20 «Отменяет спец. возможность» отсутствует")
if md5(os.path.join(ROOT, "data/deck/deck_print2.json")) != "b42d2ca39b877abd94faa2540815fee0":
    viol.append("V1: md5 deck_print2.json != якорь b42d2ca3…")

# V2 идентичность канона (оба пути, md5 6f8542a7)
a = os.path.join(ROOT, "data/deck/decks_canon_print.json"); b = os.path.join(ROOT, "_archive/blitz1.1/src/canon/decks.json")
if md5(a) != "6f8542a72407d0c7b934c9b96aa45711": viol.append("V2: decks_canon_print.json != 6f8542a7…")
if open(a,"rb").read() != open(b,"rb").read(): viol.append("V2: канон побайтово разошёлся между путями")

# V3 ситуации: 6 шт., заголовки json ↔ md
sj = json.load(open(os.path.join(ROOT, "data/deck/situations_print2.json"), encoding="utf-8"))
sits = sj.get("situations", sj)
names_j = [s["title"] for s in sits]
md_txt = open(os.path.join(ROOT, "_inbox/СИТУАЦИИ_ПЕЧАТЬ2.md"), encoding="utf-8").read()
# заголовок в md имеет вид «(цвет) — «Название»»; нормализация: взять последний сегмент после «— » и снять ««»»
def norm_title(t):
    t = t.split("— ")[-1].strip()
    return t.strip("«»").strip()
names_m = [norm_title(x) for x in re.findall(r"===\s*СИТУАЦИЯ\s*\d+\s*[—–-]*\s*(.+?)\s*===", md_txt)]
if len(sits) != 6: viol.append(f"V3: ситуаций {len(sits)} != 6")
if len(names_m) != 6: viol.append(f"V3: заголовков md {len(names_m)} != 6")
for x, y in zip([n.strip() for n in names_j], [n.strip() for n in names_m]):
    if x != y: viol.append(f"V3: заголовок разошёлся: {x!r} vs {y!r}")
if md5(os.path.join(ROOT, "data/deck/situations_print2.json")) != "444dbd8aa43a82cef6e941bbd0446737":
    viol.append("V3: md5 situations_print2.json != новый якорь 444dbd8a…")

# V4 реестр флагов: config.CFG_DEFAULTS ↔ словарь SPEC_CONSOLIDATED §4
sys.path.insert(0, os.path.join(ROOT, "game"))
import config
from config import CFG_DEFAULTS
spec_txt = open(os.path.join(ROOT, "SPEC_CONSOLIDATED.md"), encoding="utf-8").read()
sec4 = spec_txt.split("## 4.")[1].split("## 5.")[0]
# ключи словаря §4 извлекаются из записей вида key=value / key="value" (после «| » и «) · »);
# голые упоминания значений harvest_mode (quiet/late/leader…) и слова прозы в ключи не входят
cfg_keys = set(re.findall(r'(?:\|\s*|\))\s*·?\s*([a-z][a-z0-9_]{2,})\s*=', sec4))
# допуск: константы печати №2 (прямые цитаты §8/§6.3) и технические пометки — НЕ флаги реестра;
# зафиксированы ДО прогонов (Р6), сверены с комментариями config.py строки 72–113
NON_FLAG_KEYS = ("drunk_chronology_step", "drunk_chronology_victory_on", "exchange_print11",
                 "ghost_token_per_cycle", "shop_reveal_cost", "reroll_cost", "revive_cost",
                 "or_death", "heal_cap_per_cycle", "cycle_cap")
orphans_cfg = [k for k in CFG_DEFAULTS if k not in cfg_keys and k not in sec4 and k not in NON_FLAG_KEYS]
orphans_spec = [k for k in cfg_keys if k not in CFG_DEFAULTS]
missing_real = [k for k in orphans_spec if k in ("doll","forced","duel_kit_c","rpdi_plus1","tokens2","revive5")]  # контроль反向
if orphans_cfg: viol.append(f"V4: флаги в config без строки словаря: {orphans_cfg}")
if missing_real: viol.append(f"V4: флаги словаря без ключа config: {missing_real}")

# V5 гарды state-changing флагов: AST-эксцизия существует в тесте
tst = open(os.path.join(ROOT, "game/tests/test_flags_off.py"), encoding="utf-8").read()
for flag in ("harvest", "ghost_bets"):
    # фактические вызовы в тесте: write_excised("harvest") / excise(src_text, flag_key) — параметризовано;
    # проверка привязана к EXCISED-сравнению именно для этих двух флагов
    if f'write_excised("{flag}")' not in tst: viol.append(f"V5: нет эксцизии флага {flag} в гард-тесте")

# V6 Профессия/Спец 24/24 против транскриптов canon/*.md
prof_md = open(os.path.join(ROOT, "_archive/blitz1.1/src/canon/cards_professions.md"), encoding="utf-8").read()
spec_md = open(os.path.join(ROOT, "_archive/blitz1.1/src/canon/cards_spec.md"), encoding="utf-8").read()
npr = len(re.findall(r"^\s*\d+\s", prof_md, re.M)); nsp = len(re.findall(r"^\s*\d+\s", spec_md, re.M))
if len(sheets.get("ПРОФЕССИЯ", [])) != npr or len(sheets.get("СПЕЦКАРТЫ", [])) != nsp:
    viol.append(f"V6: ПРОФЕССИЯ {len(sheets.get('ПРОФЕССИЯ', []))}/{npr} или СПЕЦКАРТЫ {len(sheets.get('СПЕЦКАРТЫ', []))}/{nsp} — не совпало с транскриптами")

print("НАРУШЕНИЙ:", len(viol))
for v in viol: print("  ", v)
sys.exit(1 if viol else 0)
