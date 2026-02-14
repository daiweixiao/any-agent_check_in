#!/usr/bin/env python3
"""
多站点自动登录 + 签到
- 5 个 LinuxDO 账号 x N 个站点
- 自动 OAuth 登录，自动签到
- 输出详细结果报告
- logging 模块双输出（控制台 + 日志文件）
"""

import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import httpx

CHROME_EXE = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
DEBUG_PORT = 9222
OAUTH_AUTHORIZE_URL = 'https://connect.linux.do/oauth2/authorize'
RESULTS_FILE = 'checkin_results.json'
SESSIONS_CACHE_FILE = 'sessions_cache.json'
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
SITES = {
	'einzieg': {
		'name': 'Einzieg API',
		'domain': 'https://api.einzieg.site',
		'client_id': 'aBambSqvDqCgTW8fCarJBeQji8M5RATf',
		'checkin_path': '/api/user/checkin',
	},
	'moyu': {
		'name': '摸鱼公益',
		'domain': 'https://clove.cc.cd',
		'client_id': 'Lr8C2Ny7JPr7c4YqysaDtVEqkO1a9eL7',
		'checkin_path': '/api/user/checkin',
	},
	'laomo': {
		'name': '老魔公益站',
		'domain': 'https://api.2020111.xyz',
		'client_id': 'gnyvfmAfXrnYrt9ierq3Onj1ADvdVmmm',
		'checkin_path': '/api/user/checkin',
	},
	'wow': {
		'name': 'WoW公益站',
		'domain': 'https://linuxdoapi.223384.xyz',
		'client_id': '3fcFoNvesssuyuFsvzBafjWivE4wvTwN',
		'checkin_path': '/api/user/checkin',
	},
	'elysiver': {
		'name': 'Elysiver公益站',
		'domain': 'https://elysiver.h-e.top',
		'client_id': None,  # 需要从浏览器获取（有 WAF）
		'checkin_path': '/api/user/checkin',
	},
	'wong': {
		'name': 'WONG公益站',
		'domain': 'https://wzw.pp.ua',
		'client_id': '451QxPCe4n9e7XrvzokzPcqPH9rUyTQF',
		'checkin_path': '/api/user/checkin',
	},
	'yebsm': {
		'name': '余额比寿命长',
		'domain': 'https://new.123nhh.xyz',
		'client_id': 'm17Y3zburaQfwCe53fWpae8tKPCuHXcy',
		'checkin_path': '/api/user/checkin',
	},
	'hotaru': {
		'name': '莹和兰',
		'domain': 'https://api.hotaruapi.top',
		'client_id': 'qVGkHnU8fLzJVEMgHCuNUCYifUQwePWn',
		'checkin_path': '/api/user/checkin',
		'skip': True,  # OAuth 回调重定向到 hotaruapi.com (域名配置错误)
	},
	'dev88': {
		'name': 'dev88公益站',
		'domain': 'https://api.dev88.tech',
		'client_id': 'E8gcZeQkasYqaNiM2GwjUbV1ztY1owAc',
		'checkin_path': '/api/user/checkin',  # 需 TL2
	},
	'kfc': {
		'name': 'KFC公益站',
		'domain': 'https://kfc-api.sxxe.net',
		'client_id': 'UZgHjwXCE3HTrsNMjjEi0d8wpcj7d4Of',
		'checkin_path': '/api/user/checkin',
	},
	'uibers': {
		'name': 'uibers',
		'domain': 'https://www.uibers.com',
		'client_id': '41mEEby1c7Uy2r5e9iaErGE4SCbcqz3G',
		'checkin_path': '/api/user/checkin',
		'skip': True,  # OAuth 始终失败，原因未知
	},
	'duckcoding': {
		'name': 'duckcoding黄鸭',
		'domain': 'https://free.duckcoding.com',
		'client_id': 'XNJfOdoSeXkcx80mDydoheJ0nZS4tjIf',
		'checkin_path': '/api/user/checkin',
	},
	'duckcoding_jp': {
		'name': 'duckcoding-jp',
		'domain': 'https://jp.duckcoding.com',
		'client_id': 'MGPwGpfcyKGHsdnsY0BMpt6VZPrkxOBd',
		'checkin_path': '/api/user/checkin',
	},
	'xiaodai': {
		'name': '小呆API',
		'domain': 'https://new.184772.xyz',
		'client_id': 'Bl5uJRVkjxVpGC2MDw3UZdzb89RMguVa',
		'checkin_path': '/api/user/checkin',
		'skip': True,  # 重定向到 api.daiju.live，与 xiaodai_base 重复
	},
	'xiaodai_base': {
		'name': '小呆API-base',
		'domain': 'https://api.daiju.live',
		'client_id': 'Bl5uJRVkjxVpGC2MDw3UZdzb89RMguVa',
		'checkin_path': '/api/user/checkin',
	},
	'embedding': {
		'name': 'Embedding公益站',
		'domain': 'https://router.tumuer.me',
		'client_id': 'L3bf5EA8RoJJObIJ2W7g1CaVAZNEqM4M',
		'checkin_path': '/api/user/checkin',
	},
	'huan': {
		'name': 'Huan API',
		'domain': 'https://ai.huan666.de',
		'client_id': 'FNvJFnlfpfDM2mKDp8HTElASdjEwUriS',
		'checkin_path': '/api/user/checkin',
	},
	'muyuan': {
		'name': '慕鸢公益站',
		'domain': 'https://newapi.linuxdo.edu.rs',
		'client_id': 'rxyZeu4Wg8HNzwaG6YCj6OnFvap7ZfRU',
		'checkin_path': '/api/user/checkin',
	},
	'thatapi': {
		'name': 'ThatAPI',
		'domain': 'https://gyapi.zxiaoruan.cn',
		'client_id': 'doAqU5TVU6L7sXudST9MQ102aaJObESS',
		'checkin_path': '/api/user/checkin',  # 需 TL2
	},
	'freestyle': {
		'name': '佬友freestyle',
		'domain': 'https://api.freestyle.cc.cd',
		'client_id': 'yCN8PmzMMcdOpuZp8UVQh7dxywofhpc2',
		'checkin_path': '/api/user/checkin',
	},
	'newapi': {
		'name': 'New API',
		'domain': 'https://openai.api-test.us.ci',
		'client_id': '65Lj7gYXHoSAVDDUq6Plb11thoqAV1t7',
		'checkin_path': '/api/user/checkin',
	},
	'mtu': {
		'name': 'MTU公益',
		'domain': 'https://jiuuij.de5.net',
		'client_id': 'Sof7UgAZT2JTbXTlz8djq3eACVf2alFf',
		'checkin_path': '/api/user/checkin',
		'skip': True,  # 需 TL2，所有账号均不满足
	},
	'npc': {
		'name': 'NPC API',
		'domain': 'https://npcodex.kiroxubei.tech',
		'client_id': 'APUcB3LChvSGi3FmkODZx6Ij2038mkHY',
		'checkin_path': '/api/user/checkin',
	},
	'jarvis': {
		'name': 'Jarvis API',
		'domain': 'https://ai.ctacy.cc',
		'client_id': 'vtdgTJlFRj6WZjCfjuNucKeNXn5rplzV',
		'checkin_path': '/api/user/checkin',
	},
	'yunduan': {
		'name': '云端API',
		'domain': 'https://cloudapi.wdyu.eu.cc',
		'client_id': 'RLuQBBcU7LkZmed1mvqiktf2O5lhjbVv',
		'checkin_path': '/api/user/checkin',
	},
	'ibsgss': {
		'name': 'ibsgss公益站',
		'domain': 'https://codex.ibsgss.uk',
		'client_id': 'F3kKRQ29SJGivfhtIpjE0W0tAyxbvR2X',
		'checkin_path': '/api/user/checkin',
	},
	'hoshino': {
		'name': '星野Ai新站',
		'domain': 'https://api.hoshino.edu.rs',
		'client_id': 'XPXmWksr3NcH2aiz0MgqK5jtEmfdfZ0Q',
		'checkin_path': '/api/user/checkin',
	},
	'zer0by': {
		'name': 'Zer0by公益站',
		'domain': 'https://new-api.oseeue.com',
		'client_id': '03yHVaQuD9VhIZM63IL8xHne3wiCGxCI',
		'checkin_path': '/api/user/checkin',
	},
	'oldapi': {
		'name': 'Old API',
		'domain': 'https://sakuradori.dpdns.org',
		'client_id': 'QSRbjIGtYWCdyd0SPEiXGN4HlK4k0n7Z',
		'checkin_path': '/api/user/checkin',
	},
	'nanohajimi': {
		'name': '纳米哈基米',
		'domain': 'https://free.nanohajimi.mom',
		'client_id': 'svkUqtRyhOJMULQ1Zfnfhvv9ALSnANhf',
		'checkin_path': '/api/user/checkin',
	},
	'lmq': {
		'name': '略貌取神',
		'domain': 'https://lmq.kangnaixi.xyz',
		'client_id': 'shJeHLhXpkDmjyuMOujQCz8FkRlkVcW2',
		'checkin_path': '/api/user/checkin',
		'skip': True,  # 签到返回"权限不足"，多账号均不满足 TL 要求
	},
	'liuge': {
		'name': '六哥API',
		'domain': 'https://api.crisxie.top',
		'client_id': 'tlowvyTdQapFFeB0sm6plyWOl2M354cW',
		'checkin_path': '/api/user/checkin',
		'skip': True,  # 需 TL2，签到返回"权限不足"
	},
	'agentify': {
		'name': '不知名公益站',
		'domain': 'https://api.agentify.top',
		'client_id': 'UudCcOSQPmz3EHp2EAH5JjHo6jMcVoaZ',
		'checkin_path': '/api/user/checkin',
		'skip': True,  # 签到返回"权限不足"
	},
}

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
	subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe', '/T'],
				   capture_output=True, encoding='gbk', errors='ignore')


def record(account_label, site_key, **kwargs):
	"""记录一条结果"""
	entry = {
		'account': account_label,
		'site': SITES[site_key]['name'],
		'site_key': site_key,
		'domain': SITES[site_key]['domain'],
		'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		**kwargs,
	}
	results.append(entry)
	# 实时保存
	with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
		json.dump(results, f, indent=2, ensure_ascii=False)
	return entry


# ===================== Session 缓存 =====================

def load_sessions():
	"""从缓存文件加载 sessions"""
	try:
		with open(SESSIONS_CACHE_FILE, 'r', encoding='utf-8') as f:
			return json.load(f)
	except (FileNotFoundError, json.JSONDecodeError):
		return {}


def save_session_entry(label, site_key, session_data):
	"""保存单个 session（load-merge-save，asyncio 单线程下原子安全）"""
	sessions = load_sessions()
	if label not in sessions:
		sessions[label] = {}
	sessions[label][site_key] = session_data
	with open(SESSIONS_CACHE_FILE, 'w', encoding='utf-8') as f:
		json.dump(sessions, f, indent=2, ensure_ascii=False)


def delete_session_entry(label, site_key):
	"""删除过期 session"""
	sessions = load_sessions()
	if label in sessions and site_key in sessions[label]:
		del sessions[label][site_key]
		with open(SESSIONS_CACHE_FILE, 'w', encoding='utf-8') as f:
			json.dump(sessions, f, indent=2, ensure_ascii=False)


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


def handle_checkin_result(label, site_key, checkin_result, session_value):
	"""统一处理签到结果（httpx 和浏览器共用）。返回 True 表示有效成功。"""
	if checkin_result and checkin_result.get('method') == 'GET':
		log.debug(f'    [INFO] POST 404, 降级为 GET 成功')
	log.debug(f'    签到结果: {json.dumps(checkin_result, ensure_ascii=False)}')

	if checkin_result and checkin_result.get('success'):
		data = checkin_result.get('data', {})
		quota = data.get('quota_awarded') or data.get('quota', '?')
		msg = checkin_result.get('message', '') or '签到成功'
		log.info(f'    [OK] {msg} (额度: {quota})')
		record(label, site_key, login_ok=True, checkin_ok=True,
			   session=session_value[:50], checkin_msg=msg, quota=quota)
		return True
	elif checkin_result and checkin_result.get('error'):
		log.warning(f'    [FAIL] {checkin_result["error"]}')
		record(label, site_key, login_ok=True, checkin_ok=False,
			   session=session_value[:50], error=checkin_result['error'])
		return False
	else:
		msg = checkin_result.get('message', '未知') if checkin_result else '无响应'
		already_kws = ['已签到', '签到过', 'already', 'checked']
		is_already = any(kw in msg for kw in already_kws)
		if is_already:
			log.info(f'    [INFO] {msg}')
			record(label, site_key, login_ok=True, checkin_ok=False,
				   session=session_value[:50], checkin_msg=msg, already_checked=True)
		else:
			log.info(f'    [INFO] {msg}')
			record(label, site_key, login_ok=True, checkin_ok=False,
				   session=session_value[:50], checkin_msg=msg)
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


async def process_account(account, debug_port=9222):
	"""处理单个 LinuxDO 账号在所有站点的登录和签到"""
	from playwright.async_api import async_playwright

	label = account['label']
	log.info(f'\n{"=" * 70}')
	log.info(f'[ACCOUNT] {label} ({account["login"]})')
	log.info(f'{"=" * 70}')

	# === Phase 1: httpx 快速签到（缓存 session）===
	sessions = load_sessions()
	acc_sessions = sessions.get(label, {})
	handled_sites = set()
	cache_hits = 0

	for site_key, site_cfg in SITES.items():
		if site_cfg.get('skip'):
			continue
		cached = acc_sessions.get(site_key)
		if not cached or not cached.get('session'):
			continue

		site_name = site_cfg['name']
		domain = site_cfg['domain']
		checkin_path = site_cfg['checkin_path']

		try:
			log.info(f'  [{site_name}] httpx 签到...')
			result = await do_checkin_via_httpx(
				domain, checkin_path, cached['session'],
				user_id=cached.get('user_id'), access_token=cached.get('access_token'),
			)

			if result.get('expired'):
				log.debug(f'    [CACHE] session 已过期, 需重新 OAuth')
				delete_session_entry(label, site_key)
				continue

			if result.get('error') and '站点无法连接' in result['error']:
				log.warning(f'    [FAIL] {result["error"]}')
				record(label, site_key, login_ok=False, checkin_ok=False, error=result['error'])
				handled_sites.add(site_key)
				continue

			if result.get('error'):
				log.debug(f'    [CACHE] httpx 错误: {result["error"]}, 降级到浏览器')
				continue

			handle_checkin_result(label, site_key, result, cached['session'])
			handled_sites.add(site_key)
			cache_hits += 1
		except Exception as e:
			log.debug(f'    [CACHE] httpx 异常: {e}, 降级到浏览器')

	if cache_hits > 0:
		log.info(f'  [CACHE] {cache_hits} 个站点通过缓存完成签到')

	# 检查是否还有需要浏览器的站点
	remaining = [k for k, v in SITES.items() if not v.get('skip') and k not in handled_sites]
	if not remaining:
		log.info(f'  [OK] 所有站点已通过缓存完成!')
		# 跳过的站点仍需记录
		for site_key, site_cfg in SITES.items():
			if site_cfg.get('skip'):
				record(label, site_key, login_ok=False, checkin_ok=False, error='已标记跳过')
		return

	log.info(f'  需要浏览器 OAuth: {len(remaining)} 个站点\n')

	# === Phase 2: 浏览器 OAuth ===
	tmpdir = tempfile.mkdtemp(prefix=f'chrome_{label}_')
	proc = subprocess.Popen(
		[CHROME_EXE, f'--remote-debugging-port={debug_port}', f'--user-data-dir={tmpdir}',
		 '--no-first-run', '--no-default-browser-check', 'about:blank'],
		stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
	)

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
		for site_key, sc in SITES.items():
			if site_key not in handled_sites:
				record(label, site_key, login_ok=False, checkin_ok=False,
					   error='已标记跳过' if sc.get('skip') else 'Chrome CDP 未就绪')
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
				for site_key, sc in SITES.items():
					if site_key not in handled_sites:
						record(label, site_key, login_ok=False, checkin_ok=False,
							   error='已标记跳过' if sc.get('skip') else 'LinuxDO 登录失败')
				await page.close()
				await browser.close()
				proc.terminate()
				shutil.rmtree(tmpdir, ignore_errors=True)
				return

			log.info(f'  [OK] LinuxDO 登录成功!\n')

			# === 逐站点 OAuth + 签到 ===
			consecutive_oauth_fails = 0
			MAX_CONSECUTIVE_FAILS = 5  # 连续 N 次 OAuth 失败则跳过剩余站点

			for site_key, site_cfg in SITES.items():
				site_name = site_cfg['name']
				domain = site_cfg['domain']
				client_id = site_cfg['client_id']
				checkin_path = site_cfg['checkin_path']

				# 跳过已知无效站点或已通过缓存处理的站点
				if site_cfg.get('skip'):
					log.debug(f'  [SKIP] {site_name} (已标记跳过)')
					record(label, site_key, login_ok=False, checkin_ok=False, error='已标记跳过')
					continue

				if site_key in handled_sites:
					continue

				# 连续 OAuth 失败检测
				if consecutive_oauth_fails >= MAX_CONSECUTIVE_FAILS:
					log.warning(f'  [SKIP] 连续 {consecutive_oauth_fails} 次 OAuth 失败，跳过剩余站点')
					for sk, sc in list(SITES.items())[list(SITES.keys()).index(site_key):]:
						if not sc.get('skip') and sk not in handled_sites:
							record(label, sk, login_ok=False, checkin_ok=False, error=f'跳过(连续{consecutive_oauth_fails}次OAuth失败)')
					break

				log.info(f'  {"─" * 50}')
				log.info(f'  [{site_name}] {domain}')

				try:
					# 如果 client_id 未知（如 Elysiver），先通过浏览器获取
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
								record(label, site_key, login_ok=False, checkin_ok=False, error='无 LinuxDO OAuth')
								continue
							# 更新配置
							SITES[site_key]['client_id'] = client_id
						else:
							log.warning(f'    [FAIL] 无法获取站点配置')
							record(label, site_key, login_ok=False, checkin_ok=False, error='无法访问站点（WAF/CF）')
							continue

					# OAuth 登录
					log.info(f'    --- OAuth 登录 ---')
					with timer(f'{label}/{site_name} OAuth'):
						session_value, access_token = await oauth_login_site(page, ctx, domain, client_id)

					if not session_value:
						log.warning(f'    [FAIL] 登录失败')
						record(label, site_key, login_ok=False, checkin_ok=False, error='OAuth 获取 session 失败')
						consecutive_oauth_fails += 1
						continue

					consecutive_oauth_fails = 0  # 成功则重置计数
					log.info(f'    [OK] 登录成功! Session: {session_value[:40]}...')
					if access_token:
						log.debug(f'    Access Token: {access_token[:30]}...')

					# 获取用户 ID（作为 access_token 的备用方案）
					user_id = None
					if not access_token:
						log.debug(f'    --- 获取用户 ID ---')
						user_id = await get_user_id_from_page(page, domain)
						if user_id:
							log.debug(f'    用户 ID: {user_id}')
						else:
							log.warning(f'    [WARN] 未获取到用户 ID 和 access_token，尝试直接签到')

					# 保存 session 到缓存
					save_session_entry(label, site_key, {
						'session': session_value,
						'user_id': user_id,
						'access_token': access_token,
						'updated': datetime.now().strftime('%Y-%m-%d'),
					})

					# 签到
					log.info(f'    --- 签到 ---')
					# 确保在正确域名下
					try:
						await page.goto(f'{domain}/', wait_until='domcontentloaded', timeout=15000)
						await asyncio.sleep(2)
					except Exception:
						pass

					with timer(f'{label}/{site_name} 签到'):
						checkin_result = await do_checkin_via_browser(page, domain, checkin_path, user_id=user_id, access_token=access_token)
					handle_checkin_result(label, site_key, checkin_result, session_value)

				except Exception as e:
					log.error(f'    [ERROR] 站点处理异常: {e}', exc_info=True)
					record(label, site_key, login_ok=False, checkin_ok=False, error=f'异常: {str(e)[:80]}')

			await page.close()
			await browser.close()
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

	log.info('=' * 70)
	log.info('多站点自动登录 + 签到')
	active_sites = sum(1 for s in SITES.values() if not s.get('skip'))
	skip_sites = len(SITES) - active_sites
	log.info(f'站点: {active_sites} 个 (跳过 {skip_sites} 个) | 账号: {len(LINUXDO_ACCOUNTS)} 个')
	log.info(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
	log.info(f'环境: Python {sys.version.split()[0]} | {platform.system()} {platform.release()}')
	log.info('=' * 70)

	if not os.path.exists(CHROME_EXE):
		log.error(f'[ERROR] Chrome 未找到: {CHROME_EXE}')
		sys.exit(1)

	# 清理遗留 Chrome 进程
	kill_chrome()
	await asyncio.sleep(2)

	# 并行处理所有账号（每个账号独立 Chrome 端口）
	tasks = []
	for i, account in enumerate(LINUXDO_ACCOUNTS):
		tasks.append(process_account(account, debug_port=9222 + i))
	gather_results = await asyncio.gather(*tasks, return_exceptions=True)
	for i, result in enumerate(gather_results):
		if isinstance(result, Exception):
			log.error(f'  [ERROR] 账号 {LINUXDO_ACCOUNTS[i]["label"]} 异常: {result}')

	# 输出汇总
	overall_ms = round((time.monotonic() - overall_start) * 1000)
	log.info(f'\n\n{"=" * 70}')
	log.info('汇总报告')
	log.info(f'{"=" * 70}')

	total_login_ok = sum(1 for r in results if r.get('login_ok'))
	total_checkin_ok = sum(1 for r in results if r.get('checkin_ok'))
	total_already = sum(1 for r in results if r.get('already_checked'))
	total_entries = len(results)

	# 按站点分组
	for site_key, site_cfg in SITES.items():
		site_name = site_cfg['name']
		site_results = [r for r in results if r['site_key'] == site_key]
		login_ok = sum(1 for r in site_results if r.get('login_ok'))
		checkin_ok = sum(1 for r in site_results if r.get('checkin_ok'))
		already = sum(1 for r in site_results if r.get('already_checked'))
		total = len(site_results)
		log.info(f'\n  [{site_name}] 登录: {login_ok}/{total} | 签到: {checkin_ok}/{total} | 已签: {already}/{total}')
		for r in site_results:
			status = ''
			if r.get('checkin_ok'):
				status = f'签到成功 (额度: {r.get("quota", "?")})'
			elif r.get('already_checked'):
				status = f'今日已签到'
			elif r.get('login_ok'):
				status = f'已登录, 签到: {r.get("checkin_msg", r.get("error", "失败"))}'
			else:
				status = f'登录失败: {r.get("error", "未知")}'
			log.info(f'    {r["account"]}: {status}')

	# 统计摘要
	log.info(f'\n{"=" * 70}')
	log.info(f'运行统计')
	log.info(f'{"=" * 70}')
	log.info(f'  总耗时: {overall_ms / 1000:.1f}s')
	log.info(f'  站点数: {len(SITES)} | 账号数: {len(LINUXDO_ACCOUNTS)} | 总任务: {total_entries}')
	log.info(f'  登录成功: {total_login_ok}/{total_entries} ({total_login_ok * 100 // max(total_entries, 1)}%)')
	log.info(f'  签到成功: {total_checkin_ok}/{total_entries} ({total_checkin_ok * 100 // max(total_entries, 1)}%)')
	log.info(f'  今日已签: {total_already}/{total_entries}')
	log.info(f'  有效成功: {total_checkin_ok + total_already}/{total_entries} ({(total_checkin_ok + total_already) * 100 // max(total_entries, 1)}%)')

	# 按账号统计
	log.info(f'\n  按账号:')
	for acc in LINUXDO_ACCOUNTS:
		acc_label = acc['label']
		acc_results = [r for r in results if r['account'] == acc_label]
		acc_login = sum(1 for r in acc_results if r.get('login_ok'))
		acc_checkin = sum(1 for r in acc_results if r.get('checkin_ok'))
		acc_already = sum(1 for r in acc_results if r.get('already_checked'))
		acc_total = len(acc_results)
		log.info(f'    {acc_label:12s} 登录: {acc_login:>2}/{acc_total} | 签到: {acc_checkin:>2}/{acc_total} | 已签: {acc_already:>2}/{acc_total}')

	# 失败原因汇总
	errors = {}
	for r in results:
		err = r.get('error')
		if err:
			errors[err] = errors.get(err, 0) + 1
	if errors:
		log.info(f'\n  失败原因:')
		for err, count in sorted(errors.items(), key=lambda x: -x[1]):
			log.info(f'    {err}: {count} 次')

	log.info(f'\n结果已保存到: {RESULTS_FILE}')


if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		log.info('\n[INFO] 用户中断')
		kill_chrome()
		sys.exit(0)
