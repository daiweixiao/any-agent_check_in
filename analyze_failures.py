#!/usr/bin/env python3
"""分析失败站点详情"""
import json

info = json.load(open('site_info.json', 'r', encoding='utf-8'))
results = json.load(open('checkin_results.json', 'r', encoding='utf-8'))

print('=== 全部失败站点详情 ===\n')

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

for k, v in fail_sites:
    name = v.get('name', k)
    domain = v.get('domain', 'N/A')
    alive = v.get('alive', '未探测')
    client_id = v.get('client_id', '未配置')

    print(f"{name}")
    print(f"  域名: {domain}")
    print(f"  存活: {alive}")
    print(f"  client_id: {client_id}")

    # 统计该站点的失败原因
    site_results = [r for r in results if r.get('site_key') == k or r.get('site') == name]
    if site_results:
        errors = {}
        for r in site_results:
            if not r.get('checkin_ok'):
                err = r.get('error', '未知')
                errors[err] = errors.get(err, 0) + 1

        if errors:
            print(f"  失败原因:")
            for err, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
                print(f"    - {err}: {count}次")

    print()
