#!/usr/bin/env python3
"""快速检查签到状态"""
import json

info = json.load(open('site_info.json', 'r', encoding='utf-8'))

# AnyRouter/AgentRouter 状态
print('=== AnyRouter 状态 ===')
anyrouter_acc = info.get('anyrouter', {}).get('accounts', {})
for k, v in anyrouter_acc.items():
    print(f'  {k}: {v.get("checkin_status", "pending")}')

print('\n=== AgentRouter 状态 ===')
agentrouter_acc = info.get('agentrouter', {}).get('accounts', {})
for k, v in agentrouter_acc.items():
    print(f'  {k}: {v.get("checkin_status", "pending")}')

# 站点成功率
print('\n=== 站点成功率 ===')
success_sites = []
fail_sites = []
for k, v in info.items():
    if k == '_meta' or not isinstance(v, dict) or v.get('skip') or v.get('_removed'):
        continue
    accounts = v.get('accounts', {})
    if any(acc.get('checkin_status') == 'success' for acc in accounts.values()):
        success_sites.append(k)
    else:
        fail_sites.append(k)

print(f'有成功记录的站点: {len(success_sites)}/{len(success_sites)+len(fail_sites)}')
print(f'全部失败的站点: {len(fail_sites)}')

# 不可达站点
print('\n=== 不可达站点 ===')
unreachable = [k for k, v in info.items() if k != '_meta' and isinstance(v, dict) and v.get('alive') == False]
print(f'不可达站点数: {len(unreachable)}')
for k in unreachable:
    print(f'  - {info[k].get("name", k)}')

# 失败原因统计
print('\n=== 失败原因分布 ===')
results = json.load(open('checkin_results.json', 'r', encoding='utf-8'))
errors = {}
for r in results:
    if not r.get('checkin_ok'):
        err = r.get('error', '未知')
        errors[err] = errors.get(err, 0) + 1

for k, v in sorted(errors.items(), key=lambda x: x[1], reverse=True)[:8]:
    print(f'  {k}: {v}次')
