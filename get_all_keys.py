#!/usr/bin/env python3
"""获取所有站点的 API Key，输出 Markdown 表格 + JSON"""
import json, os, httpx
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITES_FILE = os.path.join(SCRIPT_DIR, 'sites.json')
SITE_INFO_FILE = os.path.join(SCRIPT_DIR, 'site_info.json')
OUTPUT_JSON = os.path.join(SCRIPT_DIR, 'api_keys.json')
OUTPUT_MD = os.path.join(SCRIPT_DIR, 'api_keys.md')


def format_quota(item):
	if item.get('unlimited_quota'):
		return '无限'
	q = item.get('remain_quota', 0)
	if q >= 1_000_000:
		return f'{q/500_000:.1f}$'
	return str(q)


def format_expire(ts):
	if ts == -1:
		return '永不过期'
	return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')


def main():
	with open(SITES_FILE, 'r', encoding='utf-8') as f:
		sites = json.load(f)
	with open(SITE_INFO_FILE, 'r', encoding='utf-8') as f:
		info = json.load(f)

	all_results = []
	md_lines = [f'# API Keys 汇总\n', f'> 更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n']
	total_keys = 0

	for site_key, site_cfg in sites.items():
		if site_cfg.get('skip') or site_cfg.get('provider'):
			continue

		domain = site_cfg['domain']
		site_name = site_cfg.get('name', site_key)
		accounts = info.get(site_key, {}).get('accounts', {})
		if not accounts:
			continue

		site_rows = []  # (account, name, group, key, quota, expire)

		for label, acc_data in accounts.items():
			session = acc_data.get('session', '')
			user_id = acc_data.get('user_id', '')
			if not session or not user_id:
				continue

			try:
				with httpx.Client(timeout=10, verify=False, follow_redirects=True) as c:
					r = c.get(f'{domain}/api/token/?p=0&page_size=100',
						cookies={'session': session},
						headers={'User-Agent': 'Mozilla/5.0', 'New-Api-User': str(user_id)})
					data = r.json()
			except Exception:
				continue

			keys_data = []
			for it in data.get('data', {}).get('items', []):
				if it.get('status') != 1:
					continue
				key = f'sk-{it["key"]}'
				name = it.get('name', '')
				group = it.get('group', 'default')
				quota = format_quota(it)
				expire = format_expire(it.get('expired_time', -1))

				site_rows.append((label, name, group, key, quota, expire))
				keys_data.append({
					'name': name, 'group': group, 'key': key,
					'quota': quota, 'status': it.get('status'), 'expire': expire,
				})

			if keys_data:
				all_results.append({
					'site': site_name, 'domain': domain,
					'account': label, 'keys': keys_data,
				})

		if site_rows:
			total_keys += len(site_rows)
			md_lines.append(f'\n## {site_name}\n')
			md_lines.append(f'`{domain}`\n')
			md_lines.append('| 账号 | 名称 | 分组 | Key | 额度 | 过期 |')
			md_lines.append('|------|------|------|-----|------|------|')
			for account, name, group, key, quota, expire in site_rows:
				md_lines.append(f'| {account} | {name} | {group} | `{key}` | {quota} | {expire} |')

	md_lines.append(f'\n---\n共 {total_keys} 个令牌\n')
	md_content = '\n'.join(md_lines)

	with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
		f.write(md_content)
	with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
		json.dump(all_results, f, indent=2, ensure_ascii=False)

	print(md_content)
	print(f'\n已保存: {OUTPUT_MD} / {OUTPUT_JSON}')


if __name__ == '__main__':
	main()
