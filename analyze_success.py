#!/usr/bin/env python3
"""统计成功站点"""
import json

info = json.load(open('site_info.json', 'r', encoding='utf-8'))

print('=== 成功站点统计 ===')

success_sites = []
for k, v in info.items():
    if k == '_meta' or not isinstance(v, dict):
        continue
    if v.get('skip') or v.get('_removed'):
        continue

    accounts = v.get('accounts', {})
    has_success = any(acc.get('checkin_status') == 'success' for acc in accounts.values())

    if has_success:
        success_sites.append((k, v))

print(f'成功站点数: {len(success_sites)}/41\n')

print('按成功账号数排序（前20个）:')
site_success_count = []
for k, v in success_sites:
    name = v.get('name', k)
    success_count = sum(1 for acc in v.get('accounts', {}).values() if acc.get('checkin_status') == 'success')
    already_count = sum(1 for acc in v.get('accounts', {}).values() if acc.get('checkin_status') == 'already_checked')
    total_accounts = len([acc for acc in v.get('accounts', {}).values() if not acc.get('_excluded')])
    site_success_count.append((name, success_count, already_count, total_accounts))

for name, success, already, total in sorted(site_success_count, key=lambda x: x[1] + x[2], reverse=True)[:20]:
    status = f"{success}成功 + {already}已签" if already > 0 else f"{success}成功"
    print(f'  {name}: {status}/{total}账号')
