#!/usr/bin/env python3
"""获取所有站点的 API Key、额度、模型、使用量，输出 Markdown 报告"""
import json, os, httpx
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_FILE = os.path.join(SCRIPT_DIR, 'sites.json')
SITE_INFO_FILE = os.path.join(SCRIPT_DIR, 'site_info.json')
OUTPUT_JSON = os.path.join(SCRIPT_DIR, 'api_keys.json')
OUTPUT_MD = os.path.join(SCRIPT_DIR, 'api_keys.md')

HIGHLIGHT_MODELS = ['claude', 'gpt-4o', 'gpt-4.5', 'o1', 'o3', 'o4', 'gemini', 'deepseek', 'codex']


def fmt_quota(raw, unit=500_000):
	if raw is None:
		return '-'
	d = raw / unit
	if d >= 1000:
		return f'{d/1000:.1f}K$'
	if d >= 1:
		return f'{d:.2f}$'
	return f'{d:.4f}$'


def fmt_expire(ts):
	if ts == -1:
		return '永不过期'
	return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')


def api_get(client, domain, path, session, user_id):
	try:
		r = client.get(f'{domain}{path}',
			cookies={'session': session},
			headers={'User-Agent': 'Mozilla/5.0', 'New-Api-User': str(user_id)})
		return r.json()
	except Exception:
		return {}


def classify_models(models_data):
	all_models = set()
	if isinstance(models_data, dict):
		for group_models in models_data.values():
			if isinstance(group_models, list):
				all_models.update(group_models)
	elif isinstance(models_data, list):
		for m in models_data:
			all_models.add(m.get('id', '') if isinstance(m, dict) else str(m))
	highlighted = [m for m in sorted(all_models) if any(kw in m.lower() for kw in HIGHLIGHT_MODELS)]
	return highlighted, len(all_models)


def main():
	with open(SITES_FILE, 'r', encoding='utf-8') as f:
		sites = json.load(f)
	with open(SITE_INFO_FILE, 'r', encoding='utf-8') as f:
		info = json.load(f)

	now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	all_json = []
	quota_rows = []
	quota_total = defaultdict(float)
	keys_by_site = {}  # site_key → [(label, name, group, key, quota, expire)]
	model_rows = []
	log_rows = defaultdict(list)  # label → [(site_name, model, pt, ct, cost, ts)]

	# 一次遍历，收集所有数据
	with httpx.Client(timeout=6, verify=False, follow_redirects=True) as c:
		for site_key, site_cfg in sites.items():
			if site_cfg.get('skip') or site_cfg.get('provider'):
				continue
			domain = site_cfg['domain']
			site_name = site_cfg.get('name', site_key)
			accounts = info.get(site_key, {}).get('accounts', {})
			if not accounts:
				continue

			print(f'  {site_name}...', end=' ', flush=True)
			models_fetched = False

			for label, acc_data in accounts.items():
				session = acc_data.get('session', '')
				user_id = acc_data.get('user_id', '')
				if not session or not user_id:
					continue

				# 1) 额度
				d = api_get(c, domain, '/api/user/self', session, user_id)
				u = d.get('data', {})
				if u:
					quota = u.get('quota', 0)
					used = u.get('used_quota', 0)
					req = u.get('request_count', 0)
					group = u.get('group', 'default')
					quota_rows.append((site_name, label, fmt_quota(quota), fmt_quota(used), req, group))
					quota_total[label] += quota / 500_000

				# 2) Keys
				td = api_get(c, domain, '/api/token/?p=0&page_size=100', session, user_id)
				keys_data = []
				for it in td.get('data', {}).get('items', []):
					if it.get('status') != 1:
						continue
					key = f'sk-{it["key"]}'
					name = it.get('name', '')
					grp = it.get('group', 'default')
					kquota = '无限' if it.get('unlimited_quota') else fmt_quota(it.get('remain_quota', 0))
					expire = fmt_expire(it.get('expired_time', -1))
					keys_by_site.setdefault(site_key, []).append((label, name, grp, key, kquota, expire))
					keys_data.append({'name': name, 'group': grp, 'key': key, 'quota': kquota, 'status': 1, 'expire': expire})
				if keys_data:
					all_json.append({'site': site_name, 'domain': domain, 'account': label, 'keys': keys_data})

				# 3) 模型（每站只查一次）
				if not models_fetched:
					md_data = api_get(c, domain, '/api/models', session, user_id)
					highlighted, total = classify_models(md_data.get('data', {}))
					if highlighted:
						models_str = ', '.join(highlighted[:15])
						if len(highlighted) > 15:
							models_str += f' +{len(highlighted)-15}'
						model_rows.append((site_name, total, models_str))
					models_fetched = True

				# 4) 使用量
				ld = api_get(c, domain, '/api/log/self/?p=0&page_size=5', session, user_id)
				for it in ld.get('data', {}).get('items', [])[:3]:
					model = it.get('model_name', '')
					pt = it.get('prompt_tokens', 0)
					ct = it.get('completion_tokens', 0)
					cost = fmt_quota(it.get('quota', 0))
					ts = datetime.fromtimestamp(it.get('created_at', 0)).strftime('%m-%d %H:%M') if it.get('created_at') else '-'
					log_rows[label].append((site_name, model, pt, ct, cost, ts))

			print('OK', flush=True)

	# 生成 Markdown
	md = [f'# 站点信息汇总报告\n', f'> 更新时间: {now}\n']

	# 1. 额度汇总
	md.append('\n## 1. 额度汇总\n')
	md.append('| 站点 | 账号 | 余额 | 已用 | 请求数 | 分组 |')
	md.append('|------|------|------|------|--------|------|')
	for sn, lb, q, u, r, g in quota_rows:
		md.append(f'| {sn} | {lb} | {q} | {u} | {r} | {g} |')
	md.append(f'\n**账号额度合计:**\n')
	for label in ['ZHnagsan', 'caijijiji', 'CaiWai', 'heshangd']:
		if label in quota_total:
			md.append(f'- {label}: {quota_total[label]:.2f}$')

	# 2. API Keys
	md.append('\n## 2. API Keys\n')
	md.append('| 站点 | 账号 | 名称 | 分组 | Key | 额度 | 过期 |')
	md.append('|------|------|------|------|-----|------|------|')
	total_keys = 0
	seen_quota = set()  # (site_key, label) → 额度只显示一次
	for site_key, site_cfg in sites.items():
		if site_key not in keys_by_site:
			continue
		rows = keys_by_site[site_key]
		total_keys += len(rows)
		site_name = site_cfg.get('name', site_key)
		for account, name, group, key, quota, expire in rows:
			pair = (site_key, account)
			if pair not in seen_quota:
				seen_quota.add(pair)
				md.append(f'| {site_name} | {account} | {name} | {group} | `{key}` | {quota} | {expire} |')
			else:
				md.append(f'| {site_name} | {account} | {name} | {group} | `{key}` | | |')
	md.append(f'\n共 {total_keys} 个令牌\n')

	# 3. 可用模型对比
	md.append('\n## 3. 可用模型对比\n')
	md.append('| 站点 | 模型总数 | 主要模型 |')
	md.append('|------|----------|----------|')
	for sn, total, models_str in model_rows:
		md.append(f'| {sn} | {total} | {models_str} |')

	# 4. 使用量
	md.append('\n## 4. 近期使用量\n')
	for label in ['ZHnagsan', 'caijijiji', 'CaiWai', 'heshangd']:
		if label not in log_rows:
			continue
		md.append(f'\n### {label}\n')
		md.append('| 站点 | 模型 | Tokens(入/出) | 花费 | 时间 |')
		md.append('|------|------|---------------|------|------|')
		for sn, model, pt, ct, cost, ts in log_rows[label]:
			md.append(f'| {sn} | {model} | {pt}/{ct} | {cost} | {ts} |')

	md.append(f'\n---\n生成时间: {now}\n')
	md_content = '\n'.join(md)

	with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
		f.write(md_content)
	with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
		json.dump(all_json, f, indent=2, ensure_ascii=False)

	print(md_content)
	print(f'\n已保存: {OUTPUT_MD} / {OUTPUT_JSON}')


if __name__ == '__main__':
	main()
