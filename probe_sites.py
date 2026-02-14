#!/usr/bin/env python3
"""
批量探测站点状态 v2
- 从 sites.json 读取站点列表
- 多路径检测（/, /api/status, /login, /api/user/checkin）
- 20s 超时，asyncio.Semaphore 并发控制
- 与上次结果对比，输出变更摘要
- 6 类分类（configured/pending/needs_work/no_checkin/non_newapi/dead）
- 自动生成 multi_site_checkin.py 配置片段
- logging 模块双输出（控制台 + 日志文件）
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import httpx

# ===================== 常量 =====================
PROBE_PATHS = [
	('/', 'root'),
	('/api/status', 'api_status'),
	('/login', 'login'),
	('/api/user/checkin', 'checkin_get'),
]
TIMEOUT = 20
MAX_CONCURRENT = 20
SITES_FILE = 'sites.json'
RESULTS_FILE = 'site_probe_results.json'
CONFIG_OUTPUT_FILE = 'generated_sites_config.txt'
LOG_DIR = Path('logs')
HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
	'Accept': 'application/json, text/html, */*',
}
CATEGORIES = {
	'configured': '已配置(自动签到就绪)',
	'pending': '待添加(new-api+签到+OAuth+无障碍)',
	'needs_work': '需特殊处理(Turnstile/签到未知/WAF)',
	'no_checkin': '无签到功能',
	'non_newapi': '非new-api/无OAuth',
	'dead': '无法访问',
}

log: logging.Logger = logging.getLogger('probe_sites')


# ===================== 日志配置 =====================
def setup_logging() -> logging.Logger:
	LOG_DIR.mkdir(exist_ok=True)
	ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
	log_file = LOG_DIR / f'probe_{ts}.log'

	logger = logging.getLogger('probe_sites')
	logger.setLevel(logging.DEBUG)

	ch = logging.StreamHandler()
	ch.setLevel(logging.INFO)
	ch.setFormatter(logging.Formatter('%(message)s'))
	logger.addHandler(ch)

	fh = logging.FileHandler(log_file, encoding='utf-8')
	fh.setLevel(logging.DEBUG)
	fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-5s] %(message)s', datefmt='%H:%M:%S'))
	logger.addHandler(fh)

	logger.info(f'日志文件: {log_file}')
	return logger


# ===================== 数据加载 =====================
def load_sites() -> tuple[list[dict], set[str]]:
	with open(SITES_FILE, 'r', encoding='utf-8') as f:
		data = json.load(f)
	configured_keys = set(data.get('configured_keys', []))
	sites = data['sites']
	return sites, configured_keys


def load_previous_results() -> dict[str, dict]:
	try:
		with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
			data = json.load(f)
		if isinstance(data, list):
			return {r['domain']: r for r in data}
		elif isinstance(data, dict) and 'results' in data:
			return {r['domain']: r for r in data['results']}
	except (FileNotFoundError, json.JSONDecodeError):
		pass
	return {}


# ===================== 单路径探测 =====================
async def probe_path(client: httpx.AsyncClient, domain: str, path: str, label: str, sem: asyncio.Semaphore) -> dict:
	url = f'{domain}{path}'
	start = time.monotonic()
	pr = {
		'path': path, 'label': label,
		'status': None, 'content_type': None, 'body_preview': None,
		'redirect': None, 'time_ms': 0, 'error': None,
	}
	async with sem:
		try:
			resp = await client.get(url, timeout=TIMEOUT)
			pr['status'] = resp.status_code
			pr['content_type'] = resp.headers.get('content-type', '')
			body = resp.text[:300]
			if 'html' in pr['content_type'].lower():
				m = re.search(r'<title[^>]*>(.*?)</title>', body, re.I | re.S)
				if m:
					body = f'title="{m.group(1).strip()}"'
				else:
					body = body[:150]
			pr['body_preview'] = body
			if str(resp.url) != url:
				pr['redirect'] = str(resp.url)
		except httpx.ConnectTimeout:
			pr['error'] = '连接超时'
		except httpx.ReadTimeout:
			pr['error'] = f'读取超时({TIMEOUT}s)'
		except httpx.ConnectError as e:
			pr['error'] = f'连接失败: {str(e)[:80]}'
		except Exception as e:
			pr['error'] = f'{type(e).__name__}: {str(e)[:80]}'
		finally:
			pr['time_ms'] = round((time.monotonic() - start) * 1000)

	status_str = str(pr['status']) if pr['status'] else 'ERR'
	err_str = f' | {pr["error"]}' if pr['error'] else ''
	log.debug(f'    {label:15s} {status_str:>5} {pr["time_ms"]:>6}ms{err_str}')
	return pr


# ===================== /api/status 解析 =====================
def parse_api_status(result: dict, path_result: dict):
	try:
		body = path_result.get('body_preview', '')
		if not body or body.startswith('title='):
			return
		data = json.loads(body)
		if data.get('success') and data.get('data'):
			d = data['data']
			result['is_newapi'] = True
			result['system_name'] = d.get('system_name', '')
			result['version'] = d.get('version', '')
			result['linuxdo_oauth'] = d.get('linuxdo_oauth', False)
			result['linuxdo_client_id'] = d.get('linuxdo_client_id', '')
			result['checkin_enabled'] = d.get('checkin_enabled')
			result['turnstile_check'] = d.get('turnstile_check', False)
			result['min_trust_level'] = d.get('linuxdo_minimum_trust_level')
	except (json.JSONDecodeError, TypeError):
		pass


def parse_api_status_from_raw(result: dict, resp_text: str):
	"""从完整响应文本解析 /api/status（当 body_preview 被截断时）"""
	try:
		data = json.loads(resp_text)
		if data.get('success') and data.get('data'):
			d = data['data']
			result['is_newapi'] = True
			result['system_name'] = d.get('system_name', '')
			result['version'] = d.get('version', '')
			result['linuxdo_oauth'] = d.get('linuxdo_oauth', False)
			result['linuxdo_client_id'] = d.get('linuxdo_client_id', '')
			result['checkin_enabled'] = d.get('checkin_enabled')
			result['turnstile_check'] = d.get('turnstile_check', False)
			result['min_trust_level'] = d.get('linuxdo_minimum_trust_level')
	except (json.JSONDecodeError, TypeError):
		pass


# ===================== 单站点多路径探测 =====================
async def probe_site(client: httpx.AsyncClient, site: dict, sem: asyncio.Semaphore) -> dict:
	domain = site['domain']
	name = site['name']
	start_total = time.monotonic()
	log.info(f'  探测 {name} ({domain})...')

	result = {
		'key': site['key'],
		'name': name,
		'domain': domain,
		'alive': False,
		'is_newapi': False,
		'system_name': None,
		'version': None,
		'linuxdo_oauth': False,
		'linuxdo_client_id': None,
		'checkin_enabled': None,
		'turnstile_check': None,
		'min_trust_level': None,
		'error': None,
		'path_results': [],
		'total_time_ms': 0,
		'category': 'dead',
		'changes': [],
	}

	# 先做 /api/status 的完整请求（不截断 body）
	async with sem:
		try:
			resp = await client.get(f'{domain}/api/status', timeout=TIMEOUT)
			if resp.status_code == 200:
				parse_api_status_from_raw(result, resp.text)
		except Exception:
			pass

	# 多路径探测
	path_tasks = [probe_path(client, domain, path, label, sem) for path, label in PROBE_PATHS]
	path_results = await asyncio.gather(*path_tasks)
	result['path_results'] = path_results

	# 从 /api/status 路径结果补充解析（如果完整请求失败了）
	if not result['is_newapi']:
		for pr in path_results:
			if pr['label'] == 'api_status' and pr.get('status') == 200:
				parse_api_status(result, pr)

	# 判断存活：任意路径返回非 5xx 状态码即为存活
	for pr in path_results:
		if pr.get('status') is not None:
			if pr['status'] < 500:
				result['alive'] = True
				break
			elif pr['status'] in (521, 522, 530):
				pass  # CF 错误码仍为死亡
			else:
				result['alive'] = True
				break

	# 从 /login 页面的 title 补充判断 new-api
	if not result['is_newapi'] and result['alive']:
		for pr in path_results:
			if pr['label'] == 'login' and pr.get('status') == 200:
				body = pr.get('body_preview', '')
				if 'New API' in body or 'new-api' in body.lower():
					result['is_newapi'] = True

	# 从 /api/user/checkin 的 401 判断签到存在
	for pr in path_results:
		if pr['label'] == 'checkin_get' and pr.get('status') == 401:
			if result['checkin_enabled'] is None:
				result['checkin_enabled'] = True  # 有签到接口（需登录）

	# 汇总错误
	if not result['alive']:
		errors = [pr.get('error') or f'HTTP {pr.get("status")}' for pr in path_results if pr.get('error') or (pr.get('status') and pr['status'] >= 500)]
		result['error'] = errors[0] if errors else '所有路径均不可达'

	result['total_time_ms'] = round((time.monotonic() - start_total) * 1000)

	status = '存活' if result['alive'] else '死亡'
	api_tag = ' [new-api]' if result['is_newapi'] else ''
	log.debug(f'    => {status}{api_tag} ({result["total_time_ms"]}ms)')
	return result


# ===================== 分类 =====================
def classify_site(result: dict, configured_keys: set[str]) -> str:
	if not result['alive']:
		return 'dead'
	if not result['is_newapi']:
		return 'non_newapi'
	if not result['linuxdo_oauth']:
		if result['checkin_enabled'] is False:
			return 'no_checkin'
		return 'non_newapi'  # new-api 但无 OAuth，归为非标准
	# is_newapi + linuxdo_oauth
	if result['checkin_enabled'] is False:
		return 'no_checkin'
	if result['key'] in configured_keys:
		return 'configured'
	if result.get('turnstile_check'):
		return 'needs_work'
	if result['checkin_enabled'] is None:
		return 'needs_work'
	# is_newapi + oauth + checkin + no turnstile + not configured
	return 'pending'


# ===================== 变更检测 =====================
def detect_changes(new_r: dict, old_r: dict | None) -> list[str]:
	if old_r is None:
		return ['NEW: 首次探测']
	changes = []
	old_alive = old_r.get('alive', False)
	new_alive = new_r.get('alive', False)
	if not old_alive and new_alive:
		changes.append('REVIVED: 从死亡恢复')
	elif old_alive and not new_alive:
		changes.append('DIED: 站点死亡')
	old_v = old_r.get('version')
	new_v = new_r.get('version')
	if old_v and new_v and old_v != new_v:
		changes.append(f'VERSION: {old_v} -> {new_v}')
	old_c = old_r.get('checkin_enabled')
	new_c = new_r.get('checkin_enabled')
	if old_c != new_c:
		changes.append(f'CHECKIN: {old_c} -> {new_c}')
	old_o = old_r.get('linuxdo_oauth', False)
	new_o = new_r.get('linuxdo_oauth', False)
	if old_o != new_o:
		changes.append(f'OAUTH: {old_o} -> {new_o}')
	return changes


# ===================== 配置片段生成 =====================
def generate_config_snippets(results: list[dict]) -> str:
	snippets = []
	for r in results:
		if r.get('category') != 'pending':
			continue
		key = r['key']
		tl = r.get('min_trust_level', 0)
		tl_comment = f'  # 需 TL{tl}' if tl and tl >= 2 else ''
		snippet = (
			f"\t'{key}': {{\n"
			f"\t\t'name': '{r['name']}',\n"
			f"\t\t'domain': '{r['domain']}',\n"
			f"\t\t'client_id': '{r['linuxdo_client_id']}',\n"
			f"\t\t'checkin_path': '/api/user/checkin',{tl_comment}\n"
			f"\t}},"
		)
		snippets.append(snippet)
	if not snippets:
		return ''
	header = (
		f"# 自动生成的 multi_site_checkin.py SITES 配置片段\n"
		f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
		f"# 共 {len(snippets)} 个待添加站点\n"
		f"# 将以下内容粘贴到 SITES = {{ ... }} 字典末尾\n\n"
	)
	return header + '\n'.join(snippets)


# ===================== 输出格式化 =====================
def print_category_results(cat_key: str, cat_results: list[dict]):
	if not cat_results:
		return
	label = CATEGORIES[cat_key]
	log.info(f'\n{"=" * 80}')
	log.info(f'[{cat_key.upper()}] {label}: {len(cat_results)} 个')
	log.info(f'{"=" * 80}')

	for r in cat_results:
		name = r['name']
		domain = r['domain']
		tms = r['total_time_ms']
		changes_str = f' | 变更: {", ".join(r["changes"])}' if r.get('changes') else ''

		if cat_key == 'configured':
			checkin = '有签到' if r['checkin_enabled'] else '签到未知'
			log.info(f'  {name:20s} | {domain:45s} | {checkin} | TL{r.get("min_trust_level", "?")} | {tms}ms{changes_str}')
		elif cat_key == 'pending':
			log.info(f'  {name:20s} | {domain:45s} | TL{r.get("min_trust_level", 0)} | client: {r.get("linuxdo_client_id", "?")[:20]}... | {tms}ms{changes_str}')
		elif cat_key == 'needs_work':
			reason = []
			if r.get('turnstile_check'):
				reason.append('Turnstile')
			if r.get('checkin_enabled') is None:
				reason.append('签到未知')
			log.info(f'  {name:20s} | {domain:45s} | 问题: {", ".join(reason) or "WAF"} | {tms}ms{changes_str}')
		elif cat_key == 'no_checkin':
			log.info(f'  {name:20s} | {domain:45s} | {r.get("system_name", "?")} ({r.get("version", "?")}) | {tms}ms{changes_str}')
		elif cat_key == 'non_newapi':
			err = r.get('error') or '非标准框架'
			log.info(f'  {name:20s} | {domain:45s} | {err} | {tms}ms{changes_str}')
		elif cat_key == 'dead':
			err = r.get('error', '未知')
			log.info(f'  {name:20s} | {domain:45s} | {err} | {tms}ms{changes_str}')


# ===================== 主函数 =====================
async def main():
	global log
	log = setup_logging()
	overall_start = time.monotonic()

	# 加载
	sites, configured_keys = load_sites()
	previous = load_previous_results()

	log.info(f'批量站点探测 v2 - {len(sites)} 个站点')
	log.info(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
	log.info(f'已配置站点: {len(configured_keys)} 个 | 上次记录: {len(previous)} 个')
	log.info(f'检测路径: {", ".join(p for p, _ in PROBE_PATHS)} | 超时: {TIMEOUT}s')
	log.info('=' * 80)

	# 并发探测
	sem = asyncio.Semaphore(MAX_CONCURRENT)
	async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
		tasks = [probe_site(client, site, sem) for site in sites]
		results = await asyncio.gather(*tasks)

	# 分类 + 变更检测
	all_changes = []
	for r in results:
		r['category'] = classify_site(r, configured_keys)
		old = previous.get(r['domain'])
		r['changes'] = detect_changes(r, old)
		if r['changes'] and r['changes'] != ['NEW: 首次探测']:
			all_changes.extend([(r['name'], c) for c in r['changes']])

	# 按分类输出
	for cat_key in CATEGORIES:
		cat_results = [r for r in results if r['category'] == cat_key]
		print_category_results(cat_key, cat_results)

	# 变更摘要
	if all_changes:
		log.info(f'\n{"=" * 80}')
		log.info(f'变更检测（与上次对比）: {len(all_changes)} 项变更')
		log.info(f'{"=" * 80}')
		for name, change in all_changes:
			log.info(f'  {name}: {change}')
	elif previous:
		log.info(f'\n无变更（与上次探测结果一致）')

	# 生成配置片段
	snippets = generate_config_snippets(results)
	if snippets:
		with open(CONFIG_OUTPUT_FILE, 'w', encoding='utf-8') as f:
			f.write(snippets)
		pending_count = sum(1 for r in results if r['category'] == 'pending')
		log.info(f'\n配置片段已生成: {CONFIG_OUTPUT_FILE} ({pending_count} 个待添加站点)')

	# 保存结果
	summary = {}
	for cat_key in CATEGORIES:
		summary[cat_key] = sum(1 for r in results if r['category'] == cat_key)
	output = {
		'probe_time': datetime.now().isoformat(),
		'total_sites': len(results),
		'summary': summary,
		'changes_since_last': [f'{n}: {c}' for n, c in all_changes],
		'results': results,
	}
	with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
		json.dump(output, f, indent=2, ensure_ascii=False)

	# 汇总
	overall_ms = round((time.monotonic() - overall_start) * 1000)
	log.info(f'\n{"=" * 80}')
	log.info(f'汇总')
	log.info(f'{"=" * 80}')
	log.info(f'总耗时: {overall_ms / 1000:.1f}s | 站点: {len(results)} 个')
	for cat_key, cat_label in CATEGORIES.items():
		count = summary[cat_key]
		if count > 0:
			short_label = cat_label.split('(')[0]
			log.info(f'  {short_label:20s} {count:>3} 个')
	log.info(f'\n结果保存到: {RESULTS_FILE}')
	alive_count = sum(1 for r in results if r['alive'])
	log.info(f'存活: {alive_count}/{len(results)} | 死亡: {len(results) - alive_count}/{len(results)}')


if __name__ == '__main__':
	asyncio.run(main())
