#!/usr/bin/env python3
"""Воспроизводимое восстановление маршрутов из учебного журнала; Python 3, стандартная библиотека."""
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
with (ROOT / 'students.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
cases = defaultdict(list)
for row in rows:
    cases[row['ProcessInstanceId']].append(row)
assert rows and len({r['EventId'] for r in rows}) == len(rows), 'Повтор EventId или пустой журнал'
for case_id, events in cases.items():
    events.sort(key=lambda r: int(r['EventIndex']))
    assert [int(r['EventIndex']) for r in events] == list(range(1, len(events) + 1)), case_id
    assert events[0]['EventType'] == 'process_started' and events[-1]['EventType'] == 'process_completed', case_id
    assert all(r['EventType'] == 'task_completed' for r in events[1:-1]), case_id
routes = {case: tuple(r['ActivityName'] for r in events) for case, events in cases.items()}
variants = Counter(routes.values())
edges = Counter((a, b) for route in routes.values() for a, b in zip(route, route[1:]))
ordered = sorted(variants.items(), key=lambda x: (-x[1], x[0]))
with (ROOT / 'variants.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f); writer.writerow(['Variant', 'Route', 'NumberOfCases', 'Share'])
    for i, (route, n) in enumerate(ordered, 1):
        writer.writerow([f'V{i}', ' > '.join(route), n, f'{n / len(cases):.6f}'])
with (ROOT / 'student_transitions.csv').open('w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f); writer.writerow(['SourceActivity', 'TargetActivity']); writer.writerows(sorted(edges))
assert sum(variants.values()) == len(cases)
assert sum(edges.values()) == len(rows) - len(cases)
print(f'Экземпляров: {len(cases)}; событий: {len(rows)}; вариантов: {len(variants)}; пар переходов: {len(edges)}')
print('Активность | событий | экземпляров')
for name, count in Counter(r['ActivityName'] for r in rows).most_common():
    print(f'{name} | {count} | {sum(name in route for route in routes.values())}')
print('\nПереходы:')
for (a, b), n in edges.most_common(): print(f'{a} -> {b}: {n}')
print('\nВарианты и примеры:')
for i, (route, n) in enumerate(ordered, 1):
    example = next(case for case, r in routes.items() if r == route)
    print(f'V{i}: {n}, {example}')
