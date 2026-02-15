#!/usr/bin/env python3
"""
多站点自动登录 + 签到
- 5 个 LinuxDO 账号 x N 个站点
- 自动 OAuth 登录，自动签到
- 输出详细结果报告
- logging 模块双输出（控制台 + 日志文件）
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import httpx

IS_LINUX = platform.system() == 'Linux'


def detect_chrome():
	"""自动检测 Chrome/Chromium 路径"""
	if not IS_LINUX:
		return r'C:\Program Files\Google\Chrome\Application\chrome.exe'
	for name in ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium']:
		path = shutil.which(name)
		if path:
			return path
	return 'google-chrome'


CHROME_EXE = detect_chrome()
DEBUG_PORT = 9222
OAUTH_AUTHORIZE_URL = 'https://connect.linux.do/oauth2/authorize'
RESULTS_FILE = 'checkin_results.json'
LOG_DIR = Path('logs')

log: logging.Logger = logging.getLogger('checkin')


# ===================== 日志配置 =====================
def setup_logging() -> logging.Logger:
	LOG_DIR.mkdir(exist_ok=True)
	ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
	log_file = LOG_DIR / f'checkin_{ts}.log'

	logger = logging.getLogger('checkin')
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


@contextmanager
def timer(label: str):
	"""计时上下文管理器，自动记录耗时到日志"""
	start = time.monotonic()
	yield
	elapsed = time.monotonic() - start
	log.debug(f'  [TIMER] {label}: {elapsed:.1f}s')

# ===================== 站点配置 =====================
SITES_FILE = 'sites.json'
SITE_INFO_FILE = 'site_info.json'


def load_sites():
	"""从 sites.json 加载站点配置"""
	try:
		with open(SITES_FILE, 'r', encoding='utf-8') as f:
			sites = json.load(f)
		for key, cfg in sites.items():
			cfg.setdefault('name', key)
			cfg.setdefault('checkin_path', '/api/user/checkin')
		return sites
	except FileNotFoundError:
		print(f'[ERROR] 站点配置文件不存在: {SITES_FILE}')
		sys.exit(1)
	except json.JSONDecodeError as e:
		print(f'[ERROR] 站点配置文件格式错误: {e}')
		sys.exit(1)


SITES = load_sites()

# ===================== 外部站点（AnyRouter/AgentRouter）=====================
EXTERNAL_SESSIONS_FILE = 'update_sessions.json'
SOLVE_WAF_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve_waf.js')


def load_external_accounts():
	"""加载 AnyRouter/AgentRouter 账号配置，过滤已封禁账号"""
	if not os.path.exists(EXTERNAL_SESSIONS_FILE):
		return []
	try:
		with open(EXTERNAL_SESSIONS_FILE, 'r', encoding='utf-8') as f:
			accounts = json.load(f)
		return [a for a in accounts if 'kefuka' not in a.get('name', '')]
	except Exception:
		return []


def extract_label(name):
	"""从 update_sessions.json 的 name 提取 label: 'linuxdo_34874_ZHnagsan_...' → 'ZHnagsan'"""
	parts = name.split('_')
	return parts[2] if len(parts) >= 3 else name


def solve_waf_challenge(script_content):
	"""用 Node.js 执行 WAF 挑战脚本，解出 acw_sc__v2 cookie"""
	try:
		with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
			f.write(script_content)
			waf_script_path = f.name
		result = subprocess.run(['node', SOLVE_WAF_JS, waf_script_path],
								capture_output=True, text=True, timeout=10)
		os.unlink(waf_script_path)
		if result.returncode == 0 and result.stdout.strip():
			return json.loads(result.stdout.strip())
		return None
	except Exception:
		return None


def match_linuxdo_account(ext_account_name):
	"""从 update_sessions.json 的 name 中提取邮箱，匹配 LINUXDO_ACCOUNTS 中的凭据。
	如 'linuxdo_34874_ZHnagsan_2621097668@qq.com_AnyRouter' → 匹配 login='2621097668@qq.com'"""
	for acc in LINUXDO_ACCOUNTS:
		if acc['login'] in ext_account_name:
			return acc
	return None


def save_external_session(account_name, new_session):
	"""回写新 session 到 update_sessions.json"""
	try:
		with open(EXTERNAL_SESSIONS_FILE, 'r', encoding='utf-8') as f:
			accounts = json.load(f)
		for acc in accounts:
			if acc['name'] == account_name:
				acc['cookies']['session'] = new_session
				break
		with open(EXTERNAL_SESSIONS_FILE, 'w', encoding='utf-8') as f:
			json.dump(accounts, f, indent=2, ensure_ascii=False)
	except Exception as e:
		log.warning(f'    [WARN] 回写 session 失败: {e}')


def get_waf_cookies(domain):
	"""获取阿里云 WAF cookies (acw_tc + cdn_sec_tc + acw_sc__v2)"""
	try:
		with httpx.Client(timeout=15.0, verify=False, follow_redirects=True) as client:
			resp = client.get(f'{domain}/api/user/self',
							  headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
									   'Accept': 'text/html,application/xhtml+xml'})
			waf_cookies = dict(resp.cookies)
			if resp.status_code == 200 and '<script>' in resp.text:
				scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', resp.text, re.IGNORECASE)
				if scripts:
					solved = solve_waf_challenge(scripts[0])
					if solved:
						waf_cookies.update(solved)
					else:
						return None
			return waf_cookies
	except Exception:
		return None

# ===================== LinuxDO 账号 =====================
LINUXDO_ACCOUNTS = [
	{'login': '2621097668@qq.com', 'password': 'Dxw19980927..', 'label': 'ZHnagsan'},
	{'login': 'dw2621097668@gmail.com', 'password': 'Dxw19980927..', 'label': 'caijijiji'},
	# {'login': 'xiaoweidai998@163.com', 'password': 'Dxw19980927..', 'label': 'kefuka'},  # 已封禁
	{'login': 'daixiaowei985@gmail.com', 'password': 'Dxw19980927..', 'label': 'CaiWai'},
	{'login': '2330702014@st.btbu.edu.cn', 'password': 'Dxw19980927..', 'label': 'heshangd'},
]

# ===================== 结果记录 =====================
results = []  # [{account, site, login_ok, checkin_ok, checkin_msg, session, error}]


def kill_chrome():
	if IS_LINUX:
		subprocess.run(['pkill', '-f', 'chrome'], capture_output=True)
	else:
		subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe', '/T'],
					   capture_output=True, encoding='gbk', errors='ignore')


def record(account_label, site_key, site_name='', domain='', **kwargs):
	"""记录一条结果"""
	entry = {
		'account': account_label,
		'site': site_name or site_key,
		'site_key': site_key,
		'domain': domain,
		'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		**kwargs,
	}
	results.append(entry)
	with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
		json.dump(results, f, indent=2, ensure_ascii=False)
	return entry



# ===================== site_info.json 管理 =====================

def load_site_info():
	"""加载 site_info.json，不存在则返回空结构"""
	try:
		with open(SITE_INFO_FILE, 'r', encoding='utf-8') as f:
			return json.load(f)
	except (FileNotFoundError, json.JSONDecodeError):
		return {'_meta': {'last_run': None, 'checkin_date': None}}


def save_site_info(info):
	"""保存 site_info.json，自动更新摘要统计"""
	info['_meta']['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	# 计算摘要
	total = done = success = already = failed = pending = skipped_sites = removed_sites = 0
	for key, val in info.items():
		if key == '_meta' or not isinstance(val, dict):
			continue
		if val.get('_removed'):
			removed_sites += 1
			continue
		if val.get('skip'):
			skipped_sites += 1
			continue
		for acc_val in val.get('accounts', {}).values():
			if acc_val.get('_excluded'):
				continue
			total += 1
			s = acc_val.get('checkin_status', 'pending')
			if s == 'success':
				done += 1; success += 1
			elif s == 'already_checked':
				done += 1; already += 1
			elif s == 'failed':
				done += 1; failed += 1
			else:
				pending += 1
	active_sites = sum(1 for k, v in info.items() if k != '_meta' and isinstance(v, dict) and not v.get('skip') and not v.get('_removed'))
	info['_meta']['summary'] = {
		'total_sites': active_sites + skipped_sites,
		'active_sites': active_sites,
		'skipped_sites': skipped_sites,
		'accounts': len(LINUXDO_ACCOUNTS),
		'total_tasks': total,
		'done': done,
		'success': success,
		'already_checked': already,
		'failed': failed,
		'pending': pending,
	}
	with open(SITE_INFO_FILE, 'w', encoding='utf-8') as f:
		json.dump(info, f, indent=2, ensure_ascii=False)


def sync_site_info(sites):
	"""同步 sites.json → site_info.json。site_info 是唯一执行数据源。
	- 新站点 → 创建条目 + pending
	- 新账号（sites.json 扩大 accounts）→ 创建 pending
	- 已移除站点（info 有但 sites.json 没有）→ 标记 _removed
	- 字段保护：note、探测结果（alive/has_cf/version 等）不被覆盖
	- 跨天重置：checkin_status → pending（保留 session）
	"""
	info = load_site_info()
	today = datetime.now().strftime('%Y-%m-%d')
	info['_meta']['checkin_date'] = today
	all_labels = [a['label'] for a in LINUXDO_ACCOUNTS]

	changes = []

	for site_key, cfg in sites.items():
		# provider 站点（AnyRouter/AgentRouter）：账号从 update_sessions.json 获取
		if cfg.get('provider'):
			ext_accounts = load_external_accounts()
			allowed = [extract_label(a['name']) for a in ext_accounts if a.get('provider') == cfg['provider']]
		else:
			# 该站点允许哪些账号（无 accounts 字段 = 全部）
			allowed = cfg.get('accounts', all_labels)
			# 过滤无效 label
			invalid = [l for l in allowed if l not in all_labels]
			if invalid:
				changes.append(f'  [WARN] {cfg.get("name", site_key)}: 未知账号 {invalid}')
			allowed = [l for l in allowed if l in all_labels]

		if site_key not in info or site_key == '_meta':
			# === 新站点 ===
			info[site_key] = {
				'domain': cfg['domain'],
				'name': cfg.get('name', site_key),
				'note': cfg.get('skip_reason', ''),
			}
			# provider 站点不需要 new-api 字段
			if not cfg.get('provider'):
				info[site_key].update({
					'client_id': cfg.get('client_id'),
					'checkin_path': cfg.get('checkin_path', '/api/user/checkin'),
					'alive': None, 'has_cf': None, 'has_waf': None,
					'version': None, 'checkin_enabled': None, 'min_trust_level': None,
				})
			else:
				info[site_key]['provider'] = cfg['provider']
			if cfg.get('skip'):
				info[site_key]['skip'] = True
				info[site_key]['skip_reason'] = cfg.get('skip_reason', '')
			else:
				info[site_key]['accounts'] = {}
				for lbl in allowed:
					info[site_key]['accounts'][lbl] = {'checkin_status': 'pending'}
			changes.append(f'  [NEW] {cfg.get("name", site_key)}')
		else:
			# === 已存在站点：同步可覆盖字段，保护 note/探测结果 ===
			entry = info[site_key]
			entry.pop('_removed', None)  # 恢复曾被移除的站点
			entry['domain'] = cfg['domain']
			entry['name'] = cfg.get('name', site_key)
			if cfg.get('client_id'):
				entry['client_id'] = cfg['client_id']
			entry['checkin_path'] = cfg.get('checkin_path', '/api/user/checkin')

			if cfg.get('skip'):
				entry['skip'] = True
				entry['skip_reason'] = cfg.get('skip_reason', '')
			else:
				entry.pop('skip', None)
				entry.pop('skip_reason', None)
				accounts = entry.setdefault('accounts', {})

				# 检查新增账号
				for lbl in allowed:
					if lbl not in accounts:
						accounts[lbl] = {'checkin_status': 'pending'}
						changes.append(f'  [NEW ACCOUNT] {entry.get("name", site_key)}: {lbl}')
					else:
						acc_info = accounts[lbl]
						# 跨天重置
						if acc_info.get('checkin_date') == today and acc_info.get('checkin_status') in ('success', 'already_checked'):
							pass
						else:
							acc_info['checkin_status'] = 'pending'

				# 移除不再允许的账号（标记而非删除，保留历史数据）
				for lbl in list(accounts):
					if lbl not in allowed:
						accounts[lbl]['_excluded'] = True
					else:
						accounts[lbl].pop('_excluded', None)

	# 标记已从 sites.json 移除的站点
	for site_key in list(info):
		if site_key != '_meta' and isinstance(info[site_key], dict) and site_key not in sites:
			if not info[site_key].get('_removed'):
				info[site_key]['_removed'] = True
				changes.append(f'  [REMOVED] {info[site_key].get("name", site_key)}')

	save_site_info(info)

	if changes:
		log.info(f'  [SYNC] 检测到变更:')
		for c in changes:
			log.info(c)

	return info


def update_site_info(info, site_key, **kwargs):
	"""更新站点级信息（client_id, alive, has_cf, version 等）"""
	if site_key in info:
		info[site_key].update(kwargs)
		save_site_info(info)


def update_account_info(info, site_key, label, **kwargs):
	"""更新某站点某账号的信息（session, checkin_status 等）"""
	if site_key in info and 'accounts' in info[site_key]:
		acc = info[site_key]['accounts'].setdefault(label, {})
		acc.update(kwargs)
		if 'checkin_status' in kwargs and kwargs['checkin_status'] != 'pending':
			acc['checkin_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		save_site_info(info)


def get_account_info(info, site_key, label):
	"""获取某站点某账号的信息"""
	if site_key in info and 'accounts' in info[site_key]:
		return info[site_key]['accounts'].get(label, {})
	return {}


def is_checkin_done_today(info, site_key, label):
	"""判断某账号在某站点今天是否已签到成功"""
	today = datetime.now().strftime('%Y-%m-%d')
	acc = get_account_info(info, site_key, label)
	return (acc.get('checkin_date') == today and
			acc.get('checkin_status') in ('success', 'already_checked'))


async def resolve_sites(info):
	"""补全 info 中缺失的 client_id，优先用缓存，否则 httpx 获取 /api/status"""
	changed = False

	for site_key, site_data in info.items():
		if site_key == '_meta' or not isinstance(site_data, dict):
			continue
		if site_data.get('skip') or site_data.get('_removed') or site_data.get('client_id') or site_data.get('provider'):
			continue

		# httpx 获取 /api/status
		try:
			async with httpx.AsyncClient(verify=False, timeout=15, follow_redirects=True) as client:
				resp = await client.get(f'{site_data["domain"]}/api/status')
				if resp.status_code == 200:
					d = resp.json().get('data', {})
					cid = d.get('linuxdo_client_id', '')
					if cid:
						update_site_info(info, site_key,
							client_id=cid,
							name=d.get('system_name', '') or site_data.get('name', site_key),
							version=d.get('version', ''),
							checkin_enabled=d.get('checkin_enabled'),
							min_trust_level=d.get('min_trust_level'),
						)
						changed = True
						log.info(f'  [META] {site_key}: 自动获取 client_id={cid[:12]}...')
		except Exception:
			pass

	return changed


async def do_checkin_via_httpx(domain, checkin_path, session, user_id=None, access_token=None):
	"""用 httpx 直接调用签到 API，不走浏览器。返回格式与 do_checkin_via_browser 一致。"""
	headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
	if access_token:
		headers['Authorization'] = f'Bearer {access_token}'
	elif user_id:
		headers['New-Api-User'] = str(user_id)
	cookies = {'session': session}

	try:
		async with httpx.AsyncClient(verify=False, timeout=15, follow_redirects=False) as client:
			resp = await client.post(f'{domain}{checkin_path}', headers=headers, cookies=cookies)

			# 3xx 重定向 = session 过期（跳转到登录页）
			if resp.status_code in (301, 302, 307, 308):
				return {'expired': True, 'message': 'session expired (redirect)'}
			if resp.status_code == 401:
				return {'expired': True, 'message': 'session expired (401)'}

			# HTML 响应 = session 过期
			content_type = resp.headers.get('content-type', '')
			if 'text/html' in content_type:
				return {'expired': True, 'message': 'session expired (html)'}

			data = resp.json()
			result = {
				'status': resp.status_code, 'success': data.get('success'),
				'message': data.get('message', ''), 'data': data.get('data', {}),
			}

			# POST 404 → GET 降级
			if resp.status_code == 404:
				resp2 = await client.get(f'{domain}{checkin_path}', headers=headers, cookies=cookies)
				if 'text/html' in resp2.headers.get('content-type', ''):
					return {'expired': True, 'message': 'session expired (html)'}
				data2 = resp2.json()
				return {
					'status': resp2.status_code, 'success': data2.get('success'),
					'message': data2.get('message', ''), 'data': data2.get('data', {}), 'method': 'GET',
				}

			return result
	except (httpx.ConnectError, httpx.ConnectTimeout):
		return {'error': '站点无法连接'}
	except Exception as e:
		return {'error': str(e)[:80]}


def handle_checkin_result(label, site_key, checkin_result, session_value, info, method='httpx'):
	"""统一处理签到结果（httpx 和浏览器共用）。返回 True 表示有效成功。"""
	today = datetime.now().strftime('%Y-%m-%d')
	site_data = info.get(site_key, {})
	sn = site_data.get('name', site_key)
	dm = site_data.get('domain', '')
	if checkin_result and checkin_result.get('method') == 'GET':
		log.debug(f'    [INFO] POST 404, 降级为 GET 成功')
	log.debug(f'    签到结果: {json.dumps(checkin_result, ensure_ascii=False)}')

	if checkin_result and checkin_result.get('success'):
		data = checkin_result.get('data', {})
		quota = data.get('quota_awarded') or data.get('quota', '?')
		msg = checkin_result.get('message', '') or '签到成功'
		log.info(f'    [OK] {msg} (额度: {quota})')
		record(label, site_key, site_name=sn, domain=dm, login_ok=True, checkin_ok=True,
			   session=session_value[:50], checkin_msg=msg, quota=quota)
		update_account_info(info, site_key, label,
			checkin_status='success', checkin_date=today,
			checkin_method=method, checkin_msg=msg, quota=quota)
		return True
	elif checkin_result and checkin_result.get('error'):
		log.warning(f'    [FAIL] {checkin_result["error"]}')
		record(label, site_key, site_name=sn, domain=dm, login_ok=True, checkin_ok=False,
			   session=session_value[:50], error=checkin_result['error'])
		update_account_info(info, site_key, label,
			checkin_status='failed', checkin_date=today,
			checkin_method=method, error=checkin_result['error'])
		return False
	else:
		msg = checkin_result.get('message', '未知') if checkin_result else '无响应'
		already_kws = ['已签到', '签到过', 'already', 'checked']
		is_already = any(kw in msg for kw in already_kws)
		if is_already:
			log.info(f'    [INFO] {msg}')
			record(label, site_key, site_name=sn, domain=dm, login_ok=True, checkin_ok=False,
				   session=session_value[:50], checkin_msg=msg, already_checked=True)
			update_account_info(info, site_key, label,
				checkin_status='already_checked', checkin_date=today,
				checkin_method=method, checkin_msg=msg)
		else:
			log.info(f'    [INFO] {msg}')
			record(label, site_key, site_name=sn, domain=dm, login_ok=True, checkin_ok=False,
				   session=session_value[:50], checkin_msg=msg)
			update_account_info(info, site_key, label,
				checkin_status='failed', checkin_date=today,
				checkin_method=method, checkin_msg=msg)
		return is_already


async def do_login(page, credentials):
	"""登录 LinuxDO"""
	log.debug('    建立 CF 信任...')
	try:
		await page.goto('https://linux.do/session/csrf', wait_until='commit', timeout=15000)
		await asyncio.sleep(3)
	except Exception:
		pass

	try:
		await page.goto('https://linux.do/login', wait_until='domcontentloaded', timeout=30000)
	except Exception:
		await asyncio.sleep(2)
		await page.goto('https://linux.do/login', wait_until='domcontentloaded', timeout=30000)

	for i in range(30):
		await asyncio.sleep(2)
		try:
			title = await page.title()
		except Exception:
			continue
		if not any(kw in title for kw in ['稍候', 'moment', 'Cloudflare']):
			break

	await asyncio.sleep(3)

	log.debug('    Discourse API 登录...')
	login_js = """
	async (creds) => {
		try {
			const csrfResp = await fetch('/session/csrf', {
				method: 'GET', credentials: 'same-origin',
				headers: {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest', 'Discourse-Present': 'true'},
			});
			if (csrfResp.status !== 200) return {error: 'CSRF ' + csrfResp.status};
			const csrfData = await csrfResp.json();
			const csrf = csrfData.csrf;
			const loginResp = await fetch('/session', {
				method: 'POST', credentials: 'same-origin',
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded',
					'X-CSRF-Token': csrf,
					'X-Requested-With': 'XMLHttpRequest',
					'Discourse-Present': 'true',
				},
				body: `login=${encodeURIComponent(creds.login)}&password=${encodeURIComponent(creds.password)}&second_factor_method=1`,
			});
			return {status: loginResp.status};
		} catch (e) { return {error: e.message}; }
	}
	"""
	result = await page.evaluate(login_js, credentials)
	ok = result and result.get('status') == 200
	log.info(f'    {"[OK]" if ok else "[FAIL]"} {json.dumps(result)}')
	return ok


async def get_site_config_via_browser(page, domain):
	"""通过浏览器获取站点配置（处理 WAF）"""
	try:
		await page.goto(f'{domain}/', wait_until='domcontentloaded', timeout=30000)
	except Exception:
		await asyncio.sleep(3)
		try:
			await page.goto(f'{domain}/', wait_until='commit', timeout=30000)
		except Exception:
			return None

	# 等待 WAF/CF
	for i in range(30):
		await asyncio.sleep(2)
		try:
			title = await page.title()
		except Exception:
			continue
		if not any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'Just a', 'checking', '403']):
			break

	await asyncio.sleep(3)

	# fetch /api/status
	status_result = await page.evaluate("""
		async () => {
			try {
				const resp = await fetch('/api/status', {
					method: 'GET', credentials: 'same-origin',
					headers: {'Accept': 'application/json'},
				});
				const data = await resp.json();
				return {status: resp.status, data: data.data || {}};
			} catch (e) { return {error: e.message}; }
		}
	""")
	if status_result and status_result.get('status') == 200:
		return status_result.get('data', {})
	return None


async def oauth_login_site(page, ctx, domain, client_id, max_wait=60):
	"""
	在已登录 LinuxDO 的浏览器中，通过 OAuth 登录指定站点。
	返回 (session_cookie, access_token) 元组。
	"""
	domain_host = domain.replace('https://', '')
	captured_token = [None]

	# 提取根域名用于跨域重定向匹配（如 jp.duckcoding.com → duckcoding.com）
	domain_parts = domain_host.split('.')
	# 取最后两段作为根域名（处理 .com, .xyz 等）
	root_domain = '.'.join(domain_parts[-2:]) if len(domain_parts) >= 2 else domain_host

	async def on_oauth_response(response):
		"""拦截 OAuth 回调响应，捕获 access_token"""
		try:
			if '/api/oauth/' in response.url and domain_host in response.url:
				if response.status == 200:
					body = await response.json()
					if body.get('success') and body.get('data'):
						token = body['data']
						if isinstance(token, str) and len(token) > 10:
							captured_token[0] = token
							log.debug(f'    [TOKEN] 捕获 access_token')
		except Exception:
			pass

	# 1. 浏览器访问站点首页（建立 WAF cookies）
	log.debug(f'    访问 {domain}...')
	try:
		await page.goto(f'{domain}/', wait_until='domcontentloaded', timeout=30000)
	except Exception:
		await asyncio.sleep(3)
		try:
			await page.goto(f'{domain}/', wait_until='commit', timeout=30000)
		except Exception as e:
			log.warning(f'    [FAIL] 无法访问: {e}')
			return None, None

	# 等待 WAF/CF 通过
	for i in range(15):
		await asyncio.sleep(2)
		try:
			title = await page.title()
		except Exception:
			continue
		if not any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'Just a', 'checking']):
			break

	await asyncio.sleep(2)

	# 2. 浏览器内获取 OAuth state
	state_result = await page.evaluate("""
		async () => {
			try {
				const resp = await fetch('/api/oauth/state', {
					method: 'GET', credentials: 'same-origin',
					headers: {'Accept': 'application/json'},
				});
				const data = await resp.json();
				return {status: resp.status, state: data.data || ''};
			} catch (e) { return {error: e.message}; }
		}
	""")

	if not state_result or state_result.get('status') != 200 or not state_result.get('state'):
		log.warning(f'    [FAIL] 获取 state 失败: {json.dumps(state_result)}')
		return None, None

	state = state_result['state']
	log.debug(f'    State: {state}')

	# 启动响应拦截器（在 OAuth 导航前）
	page.on('response', on_oauth_response)

	# 记录 OAuth 前已有的 session cookie（避免误捕获 state session）
	pre_oauth_sessions = set()
	try:
		pre_cookies = await ctx.cookies()
		for c in pre_cookies:
			if c['name'] == 'session':
				c_domain = c.get('domain', '')
				if domain_host in c_domain or c_domain.endswith(root_domain):
					pre_oauth_sessions.add(c['value'])
	except Exception:
		pass

	# 3. 构建 OAuth URL 并导航
	redirect_uri = quote(f'{domain}/api/oauth/linuxdo', safe='')
	oauth_url = (
		f'{OAUTH_AUTHORIZE_URL}?response_type=code'
		f'&client_id={client_id}'
		f'&redirect_uri={redirect_uri}'
		f'&scope=read+write&state={state}'
	)

	log.debug(f'    导航到 OAuth...')
	try:
		await page.goto(oauth_url, wait_until='commit', timeout=30000)
	except Exception:
		await asyncio.sleep(2)

	# 4. 等待: CF -> 允许 -> session cookie
	clicked_allow = False
	for i in range(max_wait // 2):
		await asyncio.sleep(2)
		try:
			cur_url = page.url
			title = await page.title()
		except Exception:
			break

		# Cloudflare
		if any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'Just a', 'checking']):
			if i % 15 == 0:
				log.debug(f'    [{(i + 1) * 2}s] CF: {title[:30]}')
			continue

		# 点击"允许"
		if 'connect.linux.do' in cur_url and not clicked_allow:
			try:
				allow_btn = page.locator('text=允许').first
				if await allow_btn.is_visible():
					log.debug(f'    [{(i + 1) * 2}s] 点击"允许"...')
					await allow_btn.click()
					clicked_allow = True
					await asyncio.sleep(5)
					continue
			except Exception:
				pass

		# 检查 session cookie（必须是 OAuth 后新产生的）
		# 支持跨域重定向：如 jp.duckcoding.com → duckcoding.com
		try:
			cookies = await ctx.cookies()
		except Exception:
			break
		for c in cookies:
			if c['name'] == 'session':
				c_domain = c.get('domain', '')
				# 匹配原始域名或同根域名
				if domain_host in c_domain or c_domain.endswith(root_domain):
					if c['value'] not in pre_oauth_sessions:
						log.info(f'    [{(i + 1) * 2}s] [OK] 获取新 session!')
						if c_domain != domain_host and c_domain not in domain_host:
							log.debug(f'    [INFO] Cookie 来自重定向域: {c_domain}')
						try:
							page.remove_listener('response', on_oauth_response)
						except Exception:
							pass
						return c['value'], captured_token[0]

		# 检测 OAuth 回调后的异常重定向（如跳到 /login?expired=true）
		if clicked_allow and 'connect.linux.do' not in cur_url:
			# 跨域重定向到 /login
			if domain_host not in cur_url and ('login' in cur_url or 'expired' in cur_url):
				log.warning(f'    [{(i + 1) * 2}s] [FAIL] OAuth 回调重定向到: {cur_url[:80]}')
				try:
					page.remove_listener('response', on_oauth_response)
				except Exception:
					pass
				return None, None
			# 同域重定向到 /login?expired=true（如六哥API）
			if domain_host in cur_url and '/login' in cur_url and ('expired' in cur_url or 'error' in cur_url):
				log.warning(f'    [{(i + 1) * 2}s] [FAIL] OAuth 回调失败 (expired): {cur_url[:80]}')
				try:
					page.remove_listener('response', on_oauth_response)
				except Exception:
					pass
				return None, None

		if i % 15 == 0:
			log.debug(f'    [{(i + 1) * 2}s] {title[:25]} | {cur_url[:55]}')

	try:
		page.remove_listener('response', on_oauth_response)
	except Exception:
		pass
	return None, None


async def do_checkin_via_browser(page, domain, checkin_path, user_id=None, access_token=None):
	"""在浏览器内调用签到 API（支持 access_token 或 New-Api-User 认证），带重试。
	POST 返回 404 时自动降级为 GET（部分站点的 POST 被 OpenAI API 代理拦截）。"""
	extra_headers = ""
	if access_token:
		extra_headers = f"'Authorization': 'Bearer {access_token}',"
	elif user_id:
		extra_headers = f"'New-Api-User': '{user_id}',"

	for attempt in range(3):
		try:
			if attempt > 0:
				log.debug(f'    签到重试 #{attempt + 1}...')
				await page.goto(f'{domain}/', wait_until='domcontentloaded', timeout=30000)
				await asyncio.sleep(3)
			checkin_result = await page.evaluate(f"""
				async () => {{
					try {{
						const resp = await fetch('{checkin_path}', {{
							method: 'POST',
							credentials: 'same-origin',
							headers: {{'Accept': 'application/json', 'Content-Type': 'application/json', {extra_headers}}},
						}});
						const data = await resp.json();
						const result = {{status: resp.status, success: data.success, message: data.message || '', data: data.data || {{}}}};
						// POST 返回 404 时自动降级为 GET
						if (resp.status === 404) {{
							const resp2 = await fetch('{checkin_path}', {{
								method: 'GET',
								credentials: 'same-origin',
								headers: {{'Accept': 'application/json', {extra_headers}}},
							}});
							const data2 = await resp2.json();
							return {{status: resp2.status, success: data2.success, message: data2.message || '', data: data2.data || {{}}, method: 'GET'}};
						}}
						return result;
					}} catch (e) {{ return {{error: e.message}}; }}
				}}
			""")
			return checkin_result
		except Exception as e:
			if attempt < 2:
				log.debug(f'    签到 evaluate 失败: {e}, 重试...')
				await asyncio.sleep(2)
			else:
				return {'error': f'evaluate 失败: {str(e)[:80]}'}


async def get_user_id_from_page(page, domain):
	"""OAuth 登录后，导航到 SPA 页面提取用户 ID"""
	try:
		await page.goto(f'{domain}/console', wait_until='domcontentloaded', timeout=30000)
	except Exception:
		await asyncio.sleep(3)
		try:
			await page.goto(f'{domain}/console', wait_until='commit', timeout=15000)
		except Exception:
			pass

	# 等待 WAF/CF
	for i in range(15):
		await asyncio.sleep(2)
		try:
			title = await page.title()
		except Exception:
			continue
		if not any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'Just a', 'checking']):
			break

	# 等待 SPA 初始化（React 应用需要时间加载和设置 localStorage）
	await asyncio.sleep(5)

	# 从 localStorage 提取用户 ID
	try:
		user_id = await page.evaluate("""
			() => {
				try {
					// 检查常见的 localStorage key
					const keys = ['user', 'userInfo', 'currentUser', 'user_info'];
					for (const key of keys) {
						const val = localStorage.getItem(key);
						if (val) {
							try {
								const obj = JSON.parse(val);
								if (obj && obj.id !== undefined) return String(obj.id);
							} catch(e) {}
						}
					}
					// 遍历所有 key 查找包含 id 和 username 的对象
					for (let i = 0; i < localStorage.length; i++) {
						const key = localStorage.key(i);
						try {
							const obj = JSON.parse(localStorage.getItem(key));
							if (obj && typeof obj === 'object' && 'id' in obj && 'username' in obj) {
								return String(obj.id);
							}
						} catch(e) {}
					}
					return null;
				} catch(e) {
					// SecurityError: cross-origin localStorage 访问被拒绝
					return null;
				}
			}
		""")
		return user_id
	except Exception as e:
		log.debug(f'    [WARN] localStorage 访问失败: {str(e)[:60]}')
		return None


def get_active_sites(info, label):
	"""从 info 中获取某账号应处理的活跃站点列表: [(site_key, site_data), ...]"""
	result = []
	for site_key, site_data in info.items():
		if site_key == '_meta' or not isinstance(site_data, dict):
			continue
		if site_data.get('skip') or site_data.get('_removed') or site_data.get('provider'):
			continue
		accounts = site_data.get('accounts', {})
		acc = accounts.get(label)
		if not acc or acc.get('_excluded'):
			continue
		result.append((site_key, site_data))
	return result


async def _ext_try_checkin(acc, site_key, site_cfg, info, waf_cookies=None):
	"""Phase 1: httpx 直连签到单个外部账号。返回 True=完成(成功或已签), False=需刷新"""
	name = acc.get('name', '')
	label = extract_label(name)
	domain = site_cfg['domain']
	sign_in_path = site_cfg.get('sign_in_path', '/api/user/sign_in')
	needs_waf = site_cfg.get('needs_waf', False)
	site_name = site_cfg.get('name', site_key)
	session = acc.get('cookies', {}).get('session', '')
	api_user = acc.get('api_user', '')

	if not session or not api_user:
		log.warning(f'    [{label}] 缺少 session 或 api_user，跳过')
		return True  # 无法刷新，视为完成

	# 今日已完成
	acc_info = info.get(site_key, {}).get('accounts', {}).get(label, {})
	if acc_info.get('checkin_status') in ('success', 'already_checked') and acc_info.get('checkin_date') == info['_meta']['checkin_date']:
		log.info(f'    [{label}] 今日已签到，跳过')
		return True

	all_cookies = {**(waf_cookies or {}), 'session': session}
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
		'Accept': 'application/json, text/plain, */*',
		'new-api-user': api_user,
		'Origin': domain, 'Referer': f'{domain}/',
	}

	try:
		async with httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=True) as client:
			# WAF 二次验证
			if needs_waf:
				resp_verify = await client.get(f'{domain}/api/user/self', headers=headers, cookies=all_cookies)
				if '<script>' in resp_verify.text and 'arg1=' in resp_verify.text:
					scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', resp_verify.text, re.IGNORECASE)
					if scripts:
						solved = solve_waf_challenge(scripts[0])
						if solved:
							all_cookies.update(solved)
							all_cookies.update(dict(resp_verify.cookies))

			# 验证 session
			resp = await client.get(f'{domain}/api/user/self', headers=headers, cookies=all_cookies)
			try:
				user_data = resp.json()
			except Exception:
				log.warning(f'    [{label}] Session 过期（非 JSON 响应）')
				return False  # 需要刷新

			if not user_data.get('success'):
				log.warning(f'    [{label}] Session 过期: {user_data.get("message", "")}')
				return False  # 需要刷新

			# 签到
			checkin_headers = {**headers, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
			resp_checkin = await client.post(f'{domain}{sign_in_path}', headers=checkin_headers, cookies=all_cookies)
			try:
				result_data = resp_checkin.json()
			except Exception:
				log.warning(f'    [{label}] 签到响应异常')
				record(label, site_key, site_name=site_name, domain=domain, login_ok=True, checkin_ok=False, error='签到响应异常')
				update_account_info(info, site_key, label, checkin_status='failed', checkin_msg='签到响应异常')
				save_site_info(info)
				return True

			msg = result_data.get('msg', result_data.get('message', ''))
			if result_data.get('ret') == 1 or result_data.get('code') == 0 or result_data.get('success'):
				log.info(f'    [{label}] 签到成功! {msg}')
				record(label, site_key, site_name=site_name, domain=domain, login_ok=True, checkin_ok=True, checkin_msg=msg)
				update_account_info(info, site_key, label, checkin_status='success', checkin_msg=msg, checkin_date=info['_meta']['checkin_date'])
			elif '已' in msg or 'already' in msg.lower():
				log.info(f'    [{label}] 今日已签到')
				record(label, site_key, site_name=site_name, domain=domain, login_ok=True, checkin_ok=True, checkin_msg='今日已签到')
				update_account_info(info, site_key, label, checkin_status='already_checked', checkin_msg='今日已签到', checkin_date=info['_meta']['checkin_date'])
			else:
				log.warning(f'    [{label}] 签到失败: {msg}')
				record(label, site_key, site_name=site_name, domain=domain, login_ok=True, checkin_ok=False, error=msg)
				update_account_info(info, site_key, label, checkin_status='failed', checkin_msg=msg)
			save_site_info(info)
			return True

	except Exception as e:
		log.error(f'    [{label}] 异常: {e}')
		record(label, site_key, site_name=site_name, domain=domain, login_ok=False, checkin_ok=False, error=str(e))
		update_account_info(info, site_key, label, checkin_status='failed', checkin_msg=str(e))
		save_site_info(info)
		return True


async def _ext_browser_refresh_and_checkin(failed_accounts, info):
	"""Phase 2: 浏览器 OAuth 刷新过期 session 并签到。
	按 LinuxDO 凭据分组，每组只启动一个 Chrome、登录一次。"""
	from playwright.async_api import async_playwright

	# 按 LinuxDO 邮箱分组
	groups = defaultdict(list)  # email → [(acc, site_key, site_cfg), ...]
	for acc, site_key, site_cfg in failed_accounts:
		creds = match_linuxdo_account(acc.get('name', ''))
		if creds:
			groups[creds['login']].append((acc, site_key, site_cfg, creds))
		else:
			label = extract_label(acc.get('name', ''))
			log.warning(f'    [{label}] 无匹配 LinuxDO 凭据，无法刷新')

	if not groups:
		return

	log.info(f'\n  [Phase 2] 浏览器 OAuth 刷新 ({sum(len(v) for v in groups.values())} 个账号, {len(groups)} 组)')

	for cred_email, items in groups.items():
		creds = items[0][3]  # 同组凭据相同
		log.info(f'\n  {"─" * 50}')
		log.info(f'  [LOGIN] LinuxDO: {cred_email} ({len(items)} 个账号)')

		# 启动 Chrome
		tmpdir = tempfile.mkdtemp(prefix='chrome_ext_')
		chrome_args = [
			CHROME_EXE, f'--remote-debugging-port={DEBUG_PORT}', f'--user-data-dir={tmpdir}',
			'--no-first-run', '--no-default-browser-check',
		]
		if IS_LINUX:
			chrome_args += ['--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
							'--disable-blink-features=AutomationControlled', '--window-size=1920,1080']
		chrome_args.append('about:blank')
		proc = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

		# 等待 CDP
		cdp_ready = False
		for _ in range(10):
			await asyncio.sleep(1)
			try:
				async with httpx.AsyncClient() as _c:
					await _c.get(f'http://127.0.0.1:{DEBUG_PORT}/json/version', timeout=2)
				cdp_ready = True
				break
			except Exception:
				pass

		if not cdp_ready:
			log.error(f'    [FAIL] Chrome CDP 未就绪')
			proc.terminate()
			shutil.rmtree(tmpdir, ignore_errors=True)
			continue

		async with async_playwright() as p:
			try:
				browser = await p.chromium.connect_over_cdp(f'http://127.0.0.1:{DEBUG_PORT}')
				ctx = browser.contexts[0]
				page = await ctx.new_page()

				# 登录 LinuxDO
				logged_in = await do_login(page, creds)
				if not logged_in:
					log.error(f'    [FAIL] LinuxDO 登录失败')
					for acc, site_key, site_cfg, _ in items:
						label = extract_label(acc.get('name', ''))
						site_name = site_cfg.get('name', site_key)
						record(label, site_key, site_name=site_name, domain=site_cfg['domain'],
							   login_ok=False, checkin_ok=False, error='LinuxDO 登录失败')
						update_account_info(info, site_key, label, checkin_status='failed', checkin_msg='LinuxDO 登录失败')
					save_site_info(info)
					await page.close()
					await browser.close()
					proc.terminate()
					shutil.rmtree(tmpdir, ignore_errors=True)
					continue

				log.info(f'    [OK] LinuxDO 登录成功!')

				# 逐个刷新
				for acc, site_key, site_cfg, _ in items:
					label = extract_label(acc.get('name', ''))
					domain = site_cfg['domain']
					site_name = site_cfg.get('name', site_key)
					oauth_client_id = site_cfg.get('oauth_client_id', '')
					redirect_uri = site_cfg.get('redirect_uri', '')
					sign_in_path = site_cfg.get('sign_in_path', '/api/user/sign_in')
					needs_waf = site_cfg.get('needs_waf', False)
					domain_host = domain.replace('https://', '')

					log.info(f'\n    [{label}] OAuth 刷新 {site_name}...')

					if not oauth_client_id or not redirect_uri:
						log.warning(f'    [{label}] 缺少 oauth_client_id/redirect_uri')
						continue

					# 浏览器访问站点首页（建立 WAF）
					try:
						await page.goto(f'{domain}/', wait_until='domcontentloaded', timeout=30000)
						await asyncio.sleep(5)
					except Exception:
						await asyncio.sleep(3)

					# 等待 WAF/CF
					for i in range(15):
						await asyncio.sleep(2)
						try:
							title = await page.title()
						except Exception:
							continue
						if not any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'Just a', 'checking']):
							break

					# 浏览器内获取 state
					state_result = await page.evaluate("""
						async () => {
							try {
								const resp = await fetch('/api/oauth/state', {
									method: 'GET', credentials: 'same-origin',
									headers: {'Accept': 'application/json'},
								});
								const data = await resp.json();
								return {status: resp.status, state: data.data || ''};
							} catch (e) { return {error: e.message}; }
						}
					""")

					if not state_result or state_result.get('status') != 200 or not state_result.get('state'):
						log.warning(f'    [{label}] 获取 state 失败: {json.dumps(state_result)}')
						record(label, site_key, site_name=site_name, domain=domain,
							   login_ok=False, checkin_ok=False, error='获取 OAuth state 失败')
						update_account_info(info, site_key, label, checkin_status='failed', checkin_msg='获取 OAuth state 失败')
						save_site_info(info)
						continue

					state = state_result['state']

					# 构建 OAuth URL（用 sites.json 中的 oauth_client_id + redirect_uri）
					encoded_redirect = redirect_uri.replace(':', '%3A').replace('/', '%2F')
					oauth_url = (
						f'{OAUTH_AUTHORIZE_URL}?response_type=code'
						f'&client_id={oauth_client_id}'
						f'&redirect_uri={encoded_redirect}'
						f'&scope=read+write&state={state}'
					)

					# 导航到 OAuth
					try:
						await page.goto(oauth_url, wait_until='commit', timeout=30000)
					except Exception:
						await asyncio.sleep(2)

					# 等待: CF → 允许 → session cookie
					new_session = None
					clicked_allow = False
					for i in range(90):  # 180s
						await asyncio.sleep(2)
						try:
							cur_url = page.url
							title = await page.title()
						except Exception:
							break

						if any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'Just a', 'checking']):
							if i % 15 == 0:
								log.debug(f'    [{(i+1)*2}s] CF: {title[:30]}')
							continue

						if 'connect.linux.do' in cur_url and not clicked_allow:
							try:
								allow_btn = page.locator('text=允许').first
								if await allow_btn.is_visible():
									log.debug(f'    [{(i+1)*2}s] 点击"允许"...')
									await allow_btn.click()
									clicked_allow = True
									await asyncio.sleep(5)
									continue
							except Exception:
								pass

						try:
							cookies = await ctx.cookies()
						except Exception:
							break
						for c in cookies:
							if c['name'] == 'session' and domain_host in c.get('domain', ''):
								new_session = c['value']
								break
						if new_session:
							break

						if i % 15 == 0:
							log.debug(f'    [{(i+1)*2}s] {title[:25]} | {cur_url[:55]}')

					if new_session:
						log.info(f'    [{label}] [OK] Session 刷新成功!')
						# 回写 update_sessions.json
						save_external_session(acc.get('name', ''), new_session)
						# 更新内存中的 acc（后续签到用新 session）
						acc['cookies']['session'] = new_session

						# 用新 session 签到
						waf_cookies = None
						if needs_waf:
							waf_cookies = get_waf_cookies(domain)
						done = await _ext_try_checkin(acc, site_key, site_cfg, info, waf_cookies)
						if not done:
							log.warning(f'    [{label}] 刷新后签到仍失败')
							record(label, site_key, site_name=site_name, domain=domain,
								   login_ok=True, checkin_ok=False, error='刷新后 session 仍无效')
							update_account_info(info, site_key, label, checkin_status='failed', checkin_msg='刷新后 session 仍无效')
							save_site_info(info)
					else:
						log.warning(f'    [{label}] [FAIL] Session 刷新失败')
						record(label, site_key, site_name=site_name, domain=domain,
							   login_ok=False, checkin_ok=False, error='OAuth 刷新 session 失败')
						update_account_info(info, site_key, label, checkin_status='failed', checkin_msg='OAuth 刷新 session 失败')
						save_site_info(info)

				try:
					await page.close()
					await browser.close()
				except Exception:
					pass
			except Exception as e:
				log.error(f'    [ERROR] 浏览器异常: {e}')

		proc.terminate()
		try:
			proc.wait(timeout=5)
		except Exception:
			proc.kill()
		shutil.rmtree(tmpdir, ignore_errors=True)
		# 清理 Chrome 进程，避免影响后续 Phase 1+2
		kill_chrome()
		await asyncio.sleep(2)


async def process_external_sites(info, external_accounts):
	"""处理 AnyRouter/AgentRouter 签到: Phase 1 httpx 直连 → Phase 2 浏览器 OAuth 刷新"""
	external_sites = {k: v for k, v in SITES.items() if v.get('provider') and not v.get('skip')}
	if not external_sites or not external_accounts:
		return

	log.info('')
	log.info('=' * 70)
	log.info('[EXTERNAL] AnyRouter / AgentRouter 签到')
	log.info('=' * 70)

	failed_accounts = []  # [(acc, site_key, site_cfg), ...]

	# === Phase 1: httpx 直连签到 ===
	for site_key, site_cfg in external_sites.items():
		provider = site_cfg['provider']
		domain = site_cfg['domain']
		needs_waf = site_cfg.get('needs_waf', False)
		site_name = site_cfg.get('name', site_key)

		site_accounts = [a for a in external_accounts if a.get('provider') == provider]
		if not site_accounts:
			continue

		log.info(f'  ──────────────────────────────────────────────────')
		log.info(f'  [{site_name}] {domain} ({len(site_accounts)} 个账号)')

		# WAF cookies
		waf_cookies = None
		if needs_waf:
			if not shutil.which('node'):
				log.warning(f'    [FAIL] Node.js 未安装，无法解析 WAF')
				for acc in site_accounts:
					label = extract_label(acc.get('name', ''))
					record(label, site_key, site_name=site_name, domain=domain,
						   login_ok=False, checkin_ok=False, error='Node.js 未安装')
					update_account_info(info, site_key, label, checkin_status='failed', checkin_msg='Node.js 未安装')
				save_site_info(info)
				continue

			log.info(f'    [WAF] 获取 WAF cookies...')
			waf_cookies = get_waf_cookies(domain)
			if not waf_cookies:
				log.warning(f'    [FAIL] WAF cookies 获取失败')
				for acc in site_accounts:
					label = extract_label(acc.get('name', ''))
					record(label, site_key, site_name=site_name, domain=domain,
						   login_ok=False, checkin_ok=False, error='WAF cookies 获取失败')
					update_account_info(info, site_key, label, checkin_status='failed', checkin_msg='WAF cookies 获取失败')
				save_site_info(info)
				continue
			log.info(f'    [OK] WAF cookies 获取成功')

		for acc in site_accounts:
			done = await _ext_try_checkin(acc, site_key, site_cfg, info, waf_cookies)
			if not done:
				failed_accounts.append((acc, site_key, site_cfg))

	# === Phase 2: 浏览器 OAuth 刷新过期 session ===
	if failed_accounts:
		log.info(f'\n  [INFO] {len(failed_accounts)} 个账号 session 过期，启动浏览器 OAuth 刷新...')
		await _ext_browser_refresh_and_checkin(failed_accounts, info)


async def process_account(account, info, debug_port=9222):
	"""处理单个 LinuxDO 账号在所有站点的登录和签到"""
	from playwright.async_api import async_playwright

	label = account['label']
	today = datetime.now().strftime('%Y-%m-%d')
	log.info(f'\n{"=" * 70}')
	log.info(f'[ACCOUNT] {label} ({account["login"]})')
	log.info(f'{"=" * 70}')

	# === Phase 1: httpx 快速签到（使用 site_info 中缓存的 session）===
	handled_sites = set()
	cache_hits = 0
	active_sites = get_active_sites(info, label)

	for site_key, site_data in active_sites:
		site_name = site_data.get('name', site_key)
		domain = site_data['domain']
		# 其他账号已发现站点挂了 → 跳过（并行共享 info）
		if site_data.get('alive') == False:
			log.debug(f'  [{site_name}] 站点不可达，跳过')
			record(label, site_key, site_name=site_name, domain=domain,
				login_ok=False, checkin_ok=False, error='站点无法连接')
			update_account_info(info, site_key, label,
				checkin_status='failed', checkin_date=today, error='站点无法连接')
			handled_sites.add(site_key)
			continue
		# 今日已签到 → 跳过
		if is_checkin_done_today(info, site_key, label):
			log.info(f'  [{site_name}] 今日已签到，跳过')
			handled_sites.add(site_key)
			continue
		# 从 site_info 获取缓存的 session
		acc_info = get_account_info(info, site_key, label)
		session = acc_info.get('session')
		if not session:
			continue

		checkin_path = site_data.get('checkin_path', '/api/user/checkin')

		try:
			log.info(f'  [{site_name}] httpx 签到...')
			result = await do_checkin_via_httpx(
				domain, checkin_path, session,
				user_id=acc_info.get('user_id'), access_token=acc_info.get('access_token'),
			)

			if result.get('expired'):
				log.debug(f'    [CACHE] session 已过期, 需重新 OAuth')
				update_account_info(info, site_key, label, session=None, session_updated=None)
				continue

			if result.get('error') and '站点无法连接' in result['error']:
				log.warning(f'    [FAIL] {result["error"]}')
				record(label, site_key, site_name=site_name, domain=domain,
					login_ok=False, checkin_ok=False, error=result['error'])
				update_account_info(info, site_key, label,
					checkin_status='failed', checkin_date=today, error=result['error'])
				update_site_info(info, site_key, alive=False)
				handled_sites.add(site_key)
				continue

			if result.get('error'):
				log.debug(f'    [CACHE] httpx 错误: {result["error"]}, 降级到浏览器')
				continue

			handle_checkin_result(label, site_key, result, session, info, method='httpx')
			handled_sites.add(site_key)
			cache_hits += 1
		except Exception as e:
			log.debug(f'    [CACHE] httpx 异常: {e}, 降级到浏览器')

	if cache_hits > 0:
		log.info(f'  [CACHE] {cache_hits} 个站点通过缓存完成签到')

	# 检查是否还有需要浏览器的站点
	remaining = [k for k, _ in active_sites if k not in handled_sites]
	if not remaining:
		log.info(f'  [OK] 所有站点已通过缓存完成!')
		return

	log.info(f'  需要浏览器 OAuth: {len(remaining)} 个站点\n')

	# === Phase 2: 浏览器 OAuth ===
	tmpdir = tempfile.mkdtemp(prefix=f'chrome_{label}_')
	chrome_args = [
		CHROME_EXE, f'--remote-debugging-port={debug_port}', f'--user-data-dir={tmpdir}',
		'--no-first-run', '--no-default-browser-check',
	]
	if IS_LINUX:
		chrome_args += [
			'--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
			'--disable-blink-features=AutomationControlled', '--window-size=1920,1080',
		]
	chrome_args.append('about:blank')
	proc = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

	# 等待 CDP 就绪
	for _ in range(10):
		await asyncio.sleep(1)
		try:
			async with httpx.AsyncClient() as _client:
				await _client.get(f'http://127.0.0.1:{debug_port}/json/version', timeout=2)
			break
		except Exception:
			pass
	else:
		log.error('  [FAIL] Chrome CDP 未就绪')
		proc.terminate()
		shutil.rmtree(tmpdir, ignore_errors=True)
		for site_key, site_data in active_sites:
			if site_key not in handled_sites:
				record(label, site_key, site_name=site_data.get('name', site_key),
					domain=site_data['domain'], login_ok=False, checkin_ok=False, error='Chrome CDP 未就绪')
		return

	async with async_playwright() as p:
		try:
			browser = await p.chromium.connect_over_cdp(f'http://127.0.0.1:{debug_port}')
			ctx = browser.contexts[0]
			page = await ctx.new_page()

			# === 登录 LinuxDO ===
			log.info(f'\n  [Step 1] 登录 LinuxDO...')
			with timer(f'{label} LinuxDO 登录'):
				logged_in = await do_login(page, account)
			if not logged_in:
				log.error(f'  [FAIL] LinuxDO 登录失败，跳过所有站点')
				for site_key, site_data in active_sites:
					if site_key not in handled_sites:
						record(label, site_key, site_name=site_data.get('name', site_key),
							domain=site_data['domain'], login_ok=False, checkin_ok=False, error='LinuxDO 登录失败')
				await page.close()
				await browser.close()
				proc.terminate()
				shutil.rmtree(tmpdir, ignore_errors=True)
				return

			log.info(f'  [OK] LinuxDO 登录成功!\n')

			# === 逐站点 OAuth + 签到 ===
			consecutive_oauth_fails = 0
			MAX_CONSECUTIVE_FAILS = 5

			for site_key, site_data in active_sites:
				site_name = site_data.get('name', site_key)
				domain = site_data['domain']
				client_id = site_data.get('client_id')
				checkin_path = site_data.get('checkin_path', '/api/user/checkin')

				if site_key in handled_sites:
					continue

				# 今日已签到跳过（Phase 2 重检查）
				if is_checkin_done_today(info, site_key, label):
					log.debug(f'  [SKIP] {site_name} 今日已签到')
					handled_sites.add(site_key)
					continue

				# 连续 OAuth 失败检测
				if consecutive_oauth_fails >= MAX_CONSECUTIVE_FAILS:
					log.warning(f'  [SKIP] 连续 {consecutive_oauth_fails} 次 OAuth 失败，跳过剩余站点')
					for sk, sd in active_sites:
						if sk not in handled_sites:
							record(label, sk, site_name=sd.get('name', sk), domain=sd['domain'],
								login_ok=False, checkin_ok=False, error=f'跳过(连续{consecutive_oauth_fails}次OAuth失败)')
					break

				log.info(f'  {"─" * 50}')
				log.info(f'  [{site_name}] {domain}')

				try:
					# 如果 client_id 未知，先通过浏览器获取
					if not client_id:
						log.debug(f'    获取站点配置...')
						status_data = await get_site_config_via_browser(page, domain)
						if status_data:
							client_id = status_data.get('linuxdo_client_id', '')
							checkin_enabled = status_data.get('checkin_enabled', False)
							log.debug(f'    Client ID: {client_id}')
							log.debug(f'    签到功能: {"开启" if checkin_enabled else "关闭"}')
							if not client_id:
								log.warning(f'    [SKIP] 无 LinuxDO OAuth')
								record(label, site_key, site_name=site_name, domain=domain,
									login_ok=False, checkin_ok=False, error='无 LinuxDO OAuth')
								continue
							update_site_info(info, site_key,
								client_id=client_id, alive=True,
								version=status_data.get('version', ''),
								checkin_enabled=checkin_enabled,
								min_trust_level=status_data.get('min_trust_level'),
							)
						else:
							log.warning(f'    [FAIL] 无法获取站点配置')
							record(label, site_key, site_name=site_name, domain=domain,
								login_ok=False, checkin_ok=False, error='无法访问站点（WAF/CF）')
							continue

					# OAuth 登录
					log.info(f'    --- OAuth 登录 ---')
					with timer(f'{label}/{site_name} OAuth'):
						session_value, access_token = await oauth_login_site(page, ctx, domain, client_id)

					if not session_value:
						log.warning(f'    [FAIL] 登录失败')
						record(label, site_key, site_name=site_name, domain=domain,
							login_ok=False, checkin_ok=False, error='OAuth 获取 session 失败')
						update_account_info(info, site_key, label,
							checkin_status='failed', checkin_date=today, error='OAuth 获取 session 失败')
						consecutive_oauth_fails += 1
						continue

					consecutive_oauth_fails = 0
					log.info(f'    [OK] 登录成功! Session: {session_value[:40]}...')
					if access_token:
						log.debug(f'    Access Token: {access_token[:30]}...')

					# 获取用户 ID
					user_id = None
					if not access_token:
						log.debug(f'    --- 获取用户 ID ---')
						user_id = await get_user_id_from_page(page, domain)
						if user_id:
							log.debug(f'    用户 ID: {user_id}')
						else:
							log.warning(f'    [WARN] 未获取到用户 ID 和 access_token，尝试直接签到')

					# 保存 session 到 site_info
					update_account_info(info, site_key, label,
						session=session_value, user_id=user_id, access_token=access_token,
						session_updated=today)

					# 签到
					log.info(f'    --- 签到 ---')
					try:
						await page.goto(f'{domain}/', wait_until='domcontentloaded', timeout=15000)
						await asyncio.sleep(2)
					except Exception:
						pass

					with timer(f'{label}/{site_name} 签到'):
						checkin_result = await do_checkin_via_browser(page, domain, checkin_path, user_id=user_id, access_token=access_token)
					handle_checkin_result(label, site_key, checkin_result, session_value, info, method='browser')

				except Exception as e:
					log.error(f'    [ERROR] 站点处理异常: {e}', exc_info=True)
					record(label, site_key, site_name=site_name, domain=domain,
						login_ok=False, checkin_ok=False, error=f'异常: {str(e)[:80]}')

			try:
				await asyncio.wait_for(page.close(), timeout=5)
			except Exception:
				pass
			try:
				await asyncio.wait_for(browser.close(), timeout=5)
			except Exception:
				pass
		except Exception as e:
			log.error(f'  [ERROR] 浏览器异常: {e}', exc_info=True)

	proc.terminate()
	try:
		proc.wait(timeout=5)
	except Exception:
		proc.kill()
	shutil.rmtree(tmpdir, ignore_errors=True)


async def main():
	global log
	log = setup_logging()
	overall_start = time.monotonic()

	# 解析命令行参数
	parser = argparse.ArgumentParser(description='多站点自动签到')
	parser.add_argument('--serial', action='store_true', help='串行执行（低内存服务器）')
	args = parser.parse_args()

	log.info('=' * 70)
	log.info('多站点自动登录 + 签到')
	log.info(f'站点配置: {SITES_FILE} ({len(SITES)} 个)')
	log.info(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
	log.info(f'环境: Python {sys.version.split()[0]} | {platform.system()} {platform.release()}')
	log.info('=' * 70)

	# Chrome 存在性检查
	if IS_LINUX:
		chrome_exists = shutil.which(CHROME_EXE) is not None or os.path.exists(CHROME_EXE)
	else:
		chrome_exists = os.path.exists(CHROME_EXE)
	if not chrome_exists:
		log.error(f'[ERROR] Chrome 未找到: {CHROME_EXE}')
		if IS_LINUX:
			log.error('Linux 安装: sudo dnf install -y chromium 或 sudo apt install -y chromium-browser')
		sys.exit(1)

	# 清理遗留 Chrome 进程
	kill_chrome()
	await asyncio.sleep(2)

	# 同步 sites.json → site_info.json（唯一执行数据源）
	info = sync_site_info(SITES)
	summary = info['_meta'].get('summary', {})
	log.info(f'  site_info: {SITE_INFO_FILE} (今日: {info["_meta"]["checkin_date"]})')
	log.info(f'  活跃站点: {summary.get("active_sites", 0)} | 跳过: {summary.get("skipped_sites", 0)} | 账号: {len(LINUXDO_ACCOUNTS)}')

	# 自动补全缺失的 client_id
	await resolve_sites(info)

	# Phase 0: AnyRouter/AgentRouter 签到（httpx 直连，无需浏览器）
	external_accounts = load_external_accounts()
	if external_accounts:
		await process_external_sites(info, external_accounts)

	# 自动检测串行模式：Linux + 内存 < 3GB
	serial_mode = args.serial
	if IS_LINUX and not args.serial:
		try:
			with open('/proc/meminfo') as f:
				for line in f:
					if line.startswith('MemTotal:'):
						kb = int(line.split()[1])
						if kb < 3 * 1024 * 1024:
							serial_mode = True
							log.info('  [INFO] 内存不足 3GB，自动切换串行模式')
						break
		except Exception:
			pass

	if serial_mode:
		log.info(f'  [MODE] 串行执行')
		for account in LINUXDO_ACCOUNTS:
			try:
				await process_account(account, info, debug_port=9222)
			except Exception as e:
				log.error(f'  [ERROR] 账号 {account["label"]} 异常: {e}')
	else:
		log.info(f'  [MODE] 并行执行 ({len(LINUXDO_ACCOUNTS)} 个 Chrome)')
		tasks = []
		for i, account in enumerate(LINUXDO_ACCOUNTS):
			tasks.append(process_account(account, info, debug_port=9222 + i))
		gather_results = await asyncio.gather(*tasks, return_exceptions=True)
		for i, result in enumerate(gather_results):
			if isinstance(result, Exception):
				log.error(f'  [ERROR] 账号 {LINUXDO_ACCOUNTS[i]["label"]} 异常: {result}')

	# 输出汇总（基于 site_info，包含缓存跳过的完整视图）
	overall_ms = round((time.monotonic() - overall_start) * 1000)
	all_labels = [a['label'] for a in LINUXDO_ACCOUNTS]

	# 按站点汇总状态（从 site_info 读取，覆盖缓存+本次执行）
	site_groups = {'success': [], 'failed': [], 'skipped': []}
	total_tasks = total_ok = total_already = total_fail = 0
	for site_key, site_data in info.items():
		if site_key == '_meta' or not isinstance(site_data, dict):
			continue
		if site_data.get('_removed'):
			continue
		if site_data.get('skip'):
			site_groups['skipped'].append((site_key, site_data))
			continue
		accounts = site_data.get('accounts', {})
		acc_list = []
		site_ok = site_already = site_fail = 0
		for lbl in all_labels:
			acc = accounts.get(lbl)
			if not acc or acc.get('_excluded'):
				continue
			total_tasks += 1
			st = acc.get('checkin_status', 'pending')
			if st == 'success':
				site_ok += 1; total_ok += 1
				quota = acc.get('quota', '')
				acc_list.append((lbl, 'ok', f'签到成功 (额度: {quota})'))
			elif st == 'already_checked':
				site_already += 1; total_already += 1
				acc_list.append((lbl, 'ok', '今日已签到'))
			elif st == 'failed':
				site_fail += 1; total_fail += 1
				acc_list.append((lbl, 'fail', acc.get('error', acc.get('checkin_msg', '失败'))))
			else:
				site_fail += 1; total_fail += 1
				acc_list.append((lbl, 'fail', '未执行'))
		entry = (site_key, site_data, acc_list, site_ok, site_already, site_fail)
		if site_fail > 0 and site_ok + site_already == 0:
			site_groups['failed'].append(entry)
		elif site_fail > 0:
			site_groups['failed'].append(entry)  # 部分失败也归到失败区
		else:
			site_groups['success'].append(entry)

	log.info(f'\n\n{"=" * 70}')
	log.info('汇总报告')
	log.info(f'{"=" * 70}')

	# 成功区
	ok_count = len(site_groups['success'])
	if ok_count:
		log.info(f'\n  [OK] 全部成功 ({ok_count} 个站点)')
		log.info(f'  {"─" * 50}')
		for site_key, site_data, acc_list, s_ok, s_al, s_fail in site_groups['success']:
			name = site_data.get('name', site_key)
			labels = ', '.join(lbl for lbl, _, _ in acc_list)
			log.info(f'  {name} [{len(acc_list)}账号: {labels}]')
			for lbl, _, detail in acc_list:
				log.info(f'    {lbl}: {detail}')

	# 失败区
	fail_count = len(site_groups['failed'])
	if fail_count:
		log.info(f'\n  [FAIL] 存在失败 ({fail_count} 个站点)')
		log.info(f'  {"─" * 50}')
		for site_key, site_data, acc_list, s_ok, s_al, s_fail in site_groups['failed']:
			name = site_data.get('name', site_key)
			labels = ', '.join(lbl for lbl, _, _ in acc_list)
			log.info(f'  {name} [{len(acc_list)}账号: {labels}] 成功:{s_ok + s_al} 失败:{s_fail}')
			for lbl, status, detail in acc_list:
				tag = '[OK]' if status == 'ok' else '[FAIL]'
				log.info(f'    {tag} {lbl}: {detail}')

	# 跳过区
	skip_count = len(site_groups['skipped'])
	if skip_count:
		log.info(f'\n  [SKIP] 跳过 ({skip_count} 个站点)')
		log.info(f'  {"─" * 50}')
		for site_key, site_data in site_groups['skipped']:
			name = site_data.get('name', site_key)
			reason = site_data.get('skip_reason', '')
			log.info(f'  {name}: {reason}' if reason else f'  {name}')

	# 统计摘要
	total_effective = total_ok + total_already
	log.info(f'\n{"=" * 70}')
	log.info(f'运行统计')
	log.info(f'{"=" * 70}')
	log.info(f'  总耗时: {overall_ms / 1000:.1f}s')
	log.info(f'  站点: 成功 {ok_count} | 失败 {fail_count} | 跳过 {skip_count}')
	log.info(f'  任务: {total_tasks} | 签到成功: {total_ok} | 已签到: {total_already} | 失败: {total_fail}')
	log.info(f'  有效完成: {total_effective}/{total_tasks} ({total_effective * 100 // max(total_tasks, 1)}%)')

	# 按账号统计
	log.info(f'\n  按账号:')
	for acc in LINUXDO_ACCOUNTS:
		lbl = acc['label']
		a_ok = a_al = a_fail = a_total = 0
		for site_key, site_data in info.items():
			if site_key == '_meta' or not isinstance(site_data, dict):
				continue
			if site_data.get('skip') or site_data.get('_removed'):
				continue
			a = site_data.get('accounts', {}).get(lbl)
			if not a or a.get('_excluded'):
				continue
			a_total += 1
			st = a.get('checkin_status', 'pending')
			if st == 'success': a_ok += 1
			elif st == 'already_checked': a_al += 1
			else: a_fail += 1
		log.info(f'    {lbl:12s} 成功: {a_ok:>2} | 已签: {a_al:>2} | 失败: {a_fail:>2} | 共 {a_total}')

	# 失败原因汇总
	errors = {}
	for grp in site_groups['failed']:
		for lbl, status, detail in grp[2]:
			if status == 'fail':
				errors[detail] = errors.get(detail, 0) + 1
	if errors:
		log.info(f'\n  失败原因:')
		for err, count in sorted(errors.items(), key=lambda x: -x[1]):
			log.info(f'    {err}: {count} 次')

	log.info(f'\n结果已保存到: {RESULTS_FILE}')
	log.info(f'站点信息已保存到: {SITE_INFO_FILE}')


if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		log.info('\n[INFO] 用户中断')
		kill_chrome()
		sys.exit(0)
