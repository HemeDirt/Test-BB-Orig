#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""БЛИЦ БОЙ — главная точка входа проекта (корневая менюшка).

Запуск из папки blitz/:
  python3 blitz.py play   [--seed N] [--quiet]  — сыграть партию в терминале
  python3 blitz.py batch  [--games N]           — серия партий + статистика
  python3 blitz.py html   [--seed N]            — сохранить страницу партии в viewer/
  python3 blitz.py web    [--seed N]            — обновить живую страницу игры (docs/preview/index.html)
  python3 blitz.py deck                         — показать статистику канонных колод
  python3 blitz.py test                         — прогнать все проверки (нужен node для JS-теста)

Всё, что умеет движок, описано в src/bb.py — здесь только удобная обёртка,
которая сама знает правильные пути. Тебе достаточно набрать одну команду.
"""
import sys, os, runpy

HERE = os.path.dirname(os.path.abspath(__file__))
BB = os.path.join(HERE, 'src', 'bb.py')

HELP = __doc__

if not os.path.exists(BB):
    sys.exit(f'Ошибка: не найден движок {BB}. Проверь, что запускаешь из папки blitz/.')

if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
    print(HELP)
    sys.exit(0)

cmd = sys.argv[1]

# команды, которые bb.py не знает — пробрасываем напрямую
if cmd == 'web':
    sys.argv = [os.path.join(HERE, 'src', 'make_web.py')] + sys.argv[2:]
    runpy.run_path(sys.argv[0], run_name='__main__')
elif cmd == 'test':
    import subprocess
    print('=== ТЕСТ 1: python-движок, 5 партий ===')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'src', 'game_sim.py'), '5', '--quiet'])
    if r.returncode != 0: sys.exit('ПАДЕНИЕ python-движка')
    print('=== ТЕСТ 2: генерация web-страницы ===')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'src', 'make_web.py'), '777'])
    if r.returncode != 0: sys.exit('ПАДЕНИЕ make_web')
    print('=== ТЕСТ 3: интерактивная страница (node, 30 партий) ===')
    has_node = subprocess.run(['node', '--version'], capture_output=True).returncode == 0
    if not has_node:
        print('node не установлен — JS-тест пропущен (не страшно).')
    else:
        r = subprocess.run(['node', os.path.join(HERE, 'src', 'test_game.js')])
        if r.returncode != 0: sys.exit('ПАДЕНИЕ JS-теста')
    print('\nВСЕ ТЕСТЫ ПРОЙДЕНЫ ✓')
else:
    # play / batch / html / deck — внутри bb.py сам всё подключает
    sys.argv = [BB] + sys.argv[1:]
    runpy.run_path(BB, run_name='__main__')
