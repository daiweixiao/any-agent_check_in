#!/usr/bin/env python3
"""列出全部失败的站点"""
import json

info = json.load(open('site_info.json', 'r', encoding='utf-8'))

fail_sites = []
for k, v in info.items():
    if k == '_meta' or not isinstance(v, dict):
        continue
    if v.get('skip') or v.get('_removed'):
        continue

    accounts = v.get('accounts', {})
    has_success = any(acc.get('checkin_status') == 'success' for acc in accounts.values())

    if not has_success:
        fail_sites.append((k, v))

print(f'全部失败的站点 ({len(fail_sites)}个):')
for k, v in fail_sites[:20]:
    name = v.get('name', k)
    alive = v.get('alive', True)
    status = '不可达' if alive == False else '可达'
    print(f'  - {name} ({status})')
