#!/usr/bin/env python3
"""
自动刷新 Session（利用真实 Chrome 浏览器）

核心设计：
- 按 LinuxDO 凭据分组，同一凭据只登录一次
- 在同一个 Chrome 会话中刷新该凭据关联的所有账号
- 避免 LinuxDO 登录频率限制
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict

import httpx

CHROME_EXE = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
SOLVE_WAF_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve_waf.js')
CONFIG_FILE = 'update_sessions.json'
DEBUG_PORT = 9222

# LinuxDO OAuth 配置
OAUTH_AUTHORIZE_URL = 'https://connect.linux.do/oauth2/authorize'

PLATFORMS = {
	'anyrouter': {
		'domain': 'https://anyrouter.top',
		'redirect_uri': 'https://anyrouter.top/oauth/linuxdo',
		'oauth_client_id': '8w2uZtoWH9AUXrZr1qeCEEmvXLafea3c',
		'needs_waf': True,
	},
	'agentrouter': {
		'domain': 'https://agentrouter.org',
		'redirect_uri': 'https://agentrouter.org/oauth/linuxdo',
		'oauth_client_id': 'KZUecGfhhDZMVnv8UtEdhOhf9sNOhqVX',
		'needs_waf': False,
	},
}

# 账号对应的 LinuxDO 凭据（根据名称中的邮箱匹配）
LINUXDO_CREDENTIALS = {
	'2621097668@qq.com': {'login': '2621097668@qq.com', 'password': 'Dxw19980927..'},
	'dw2621097668@gmail.com': {'login': 'dw2621097668@gmail.com', 'password': 'Dxw19980927..'},
	'xiaoweidai998@163.com': {'login': 'xiaoweidai998@163.com', 'password': 'Dxw19980927..'},
	'daixiaowei985@gmail.com': {'login': 'daixiaowei985@gmail.com', 'password': 'Dxw19980927..'},
	'2330702014@st.btbu.edu.cn': {'login': '2330702014@st.btbu.edu.cn', 'password': 'Dxw19980927..'},
}


def solve_waf(domain: str) -> dict:
	"""获取 WAF cookies"""
	with httpx.Client(timeout=15, verify=False, follow_redirects=True) as client:
		resp = client.get(f'{domain}/', headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'})
		cookies = dict(resp.cookies)
		if '<script>' in resp.text:
			scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', resp.text, re.IGNORECASE)
			if scripts:
				with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
					f.write(scripts[0])
					waf_file = f.name
				result = subprocess.run(['node', SOLVE_WAF_JS, waf_file], capture_output=True, text=True, timeout=10)
				os.unlink(waf_file)
				if result.returncode == 0:
					cookies.update(json.loads(result.stdout.strip()))
		return cookies


def get_oauth_state(domain: str, waf_cookies: dict = None) -> str:
	"""获取 OAuth state"""
	with httpx.Client(timeout=15, verify=False, follow_redirects=True) as client:
		resp = client.get(
			f'{domain}/api/oauth/state',
			headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
			cookies=waf_cookies or {},
		)
		return resp.json().get('data', '')


def build_oauth_url(platform_name: str, state: str) -> str:
	"""构建 OAuth URL"""
	platform = PLATFORMS[platform_name]
	redirect_uri = platform['redirect_uri'].replace(':', '%3A').replace('/', '%2F')
	client_id = platform['oauth_client_id']
	return (
		f'{OAUTH_AUTHORIZE_URL}?response_type=code'
		f'&client_id={client_id}'
		f'&redirect_uri={redirect_uri}'
		f'&scope=read+write&state={state}'
	)


def kill_chrome():
	subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe', '/T'], capture_output=True, encoding='gbk', errors='ignore')


def match_credentials(account_name: str) -> str | None:
	"""根据账号名称匹配 LinuxDO 凭据，返回邮箱 key"""
	for email in LINUXDO_CREDENTIALS:
		if email in account_name:
			return email
	return None


def check_session_valid(session: str, api_user: str, provider: str) -> bool:
	"""检查 session 是否有效"""
	platform = PLATFORMS.get(provider, {})
	domain = platform.get('domain', '')
	if not domain:
		return False
	try:
		# 需要 WAF cookies 才能通过 WAF 保护
		waf_cookies = solve_waf(domain) if platform.get('needs_waf') else {}
		waf_cookies['session'] = session

		with httpx.Client(timeout=10, verify=False, follow_redirects=True) as client:
			resp = client.get(
				f'{domain}/api/user/self',
				headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'new-api-user': api_user},
				cookies=waf_cookies,
			)
			return resp.status_code == 200 and resp.json().get('success', False)
	except Exception:
		return False


async def wait_cloudflare(page, max_wait=120):
	"""等待 Cloudflare 通过"""
	for i in range(max_wait // 2):
		await asyncio.sleep(2)
		try:
			title = await page.title()
		except Exception:
			return False
		is_cf = any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'checking', 'Just a'])
		if not is_cf:
			print(f'    Cloudflare 通过 ({(i + 1) * 2}s)')
			return True
		if i % 10 == 0:
			print(f'    [{(i + 1) * 2}s] {title[:40]}')
	return False


async def do_login(page, credentials):
	"""在 linux.do 登录：先建立 CF 信任，再通过 API 登录"""
	# Step A: 建立 CF 信任（导航到 /session/csrf 让 CF 放行 /session/ 路径）
	print('    建立 CF 信任 (/session/csrf)...')
	try:
		await page.goto('https://linux.do/session/csrf', wait_until='commit', timeout=15000)
		await asyncio.sleep(3)
	except Exception:
		pass

	# Step B: 导航到登录页
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

	# Step C: 通过 API 登录（单次 AJAX 调用：CSRF + POST /session）
	print('    通过 Discourse API 登录...')
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
	print(f'    API 结果: {json.dumps(result)}')
	return result and result.get('status') == 200


async def get_state_via_browser(page, domain: str) -> str | None:
	"""在浏览器中获取 OAuth state（确保 state 与浏览器 session 一致）"""
	# 先访问站点首页建立 WAF cookies
	print(f'    浏览器访问 {domain} 建立 WAF...')
	try:
		await page.goto(f'{domain}/', wait_until='domcontentloaded', timeout=30000)
		await asyncio.sleep(5)  # 等待 WAF JS 执行
	except Exception as e:
		print(f'    [WARN] 访问首页异常: {e}')
		await asyncio.sleep(3)

	# 在浏览器内 fetch state
	state_result = await page.evaluate("""
		async () => {
			try {
				const resp = await fetch('/api/oauth/state', {
					method: 'GET',
					credentials: 'same-origin',
					headers: {'Accept': 'application/json'},
				});
				const data = await resp.json();
				return {status: resp.status, state: data.data || ''};
			} catch (e) { return {error: e.message}; }
		}
	""")

	if state_result and state_result.get('status') == 200:
		return state_result.get('state', '')
	print(f'    [WARN] 获取 state 失败: {json.dumps(state_result)}')
	return None


async def wait_for_oauth_redirect(page, ctx, target_domain: str, max_wait=180):
	"""
	等待 OAuth 流程完成，处理 Cloudflare 和授权页面。
	统一处理：CF 挑战 -> 授权页面("允许") -> session cookie 捕获。
	返回 session cookie 值。
	"""
	clicked_allow = False
	for i in range(max_wait // 2):
		await asyncio.sleep(2)

		try:
			cur_url = page.url
			title = await page.title()
		except Exception:
			break

		# 跳过 Cloudflare 挑战页面
		if any(kw in title for kw in ['稍候', 'moment', 'Cloudflare', 'Just a', 'checking']):
			if i % 15 == 0:
				print(f'    [{(i + 1) * 2}s] CF: {title[:30]}')
			continue

		# 检查并点击 "允许" 按钮（connect.linux.do 授权页面）
		if 'connect.linux.do' in cur_url and not clicked_allow:
			try:
				allow_btn = page.locator('text=允许').first
				if await allow_btn.is_visible():
					print(f'    [{(i + 1) * 2}s] 点击"允许"...')
					await allow_btn.click()
					clicked_allow = True
					await asyncio.sleep(5)
					continue
			except Exception:
				pass

		# 检查 session cookie
		try:
			cookies = await ctx.cookies()
		except Exception:
			break
		for c in cookies:
			if c['name'] == 'session' and target_domain in c.get('domain', ''):
				print(f'    [{(i + 1) * 2}s] [OK] 获取 session cookie!')
				return c['value']

		if i % 15 == 0:
			print(f'    [{(i + 1) * 2}s] {title[:25]} | {cur_url[:55]}')

	return None


async def refresh_account_in_session(page, ctx, platform_name: str) -> str | None:
	"""在已登录的 Chrome 会话中，为一个平台刷新 session"""
	platform = PLATFORMS[platform_name]
	domain = platform['domain']
	domain_host = domain.replace('https://', '')

	# 在浏览器中获取 OAuth state（确保与浏览器 session 一致）
	state = await get_state_via_browser(page, domain)
	if not state:
		# 回退到 httpx 方式
		print(f'    回退到 httpx 获取 state...')
		waf_cookies = solve_waf(domain) if platform['needs_waf'] else {}
		state = get_oauth_state(domain, waf_cookies)
	if not state:
		print(f'    [FAIL] 无法获取 OAuth state')
		return None
	print(f'    State: {state}')

	oauth_url = build_oauth_url(platform_name, state)

	# 导航到 OAuth（已登录 linux.do，应该自动跳转）
	print(f'    导航到 OAuth...')
	await page.goto(oauth_url, wait_until='commit', timeout=30000)

	# 统一等待：CF + 允许 + session cookie
	print(f'    等待 OAuth 流程 + session...')
	return await wait_for_oauth_redirect(page, ctx, domain_host, max_wait=180)


async def refresh_credential_group(cred_email: str, account_indices: list, accounts: list) -> dict:
	"""
	为同一个 LinuxDO 凭据关联的所有账号刷新 session。
	只启动一个 Chrome 实例，只登录一次。
	返回 {account_index: new_session} 映射。
	"""
	from playwright.async_api import async_playwright

	credentials = LINUXDO_CREDENTIALS[cred_email]
	results = {}

	print(f'\n{"=" * 60}')
	print(f'[LOGIN] LinuxDO: {cred_email}')
	print(f'  关联账号: {len(account_indices)} 个')
	print(f'{"=" * 60}')

	# 为第一个账号构建 OAuth URL
	first_idx = account_indices[0]
	first_acc = accounts[first_idx]
	first_provider = first_acc.get('provider', 'anyrouter')
	first_platform = PLATFORMS[first_provider]
	first_domain = first_platform['domain']
	first_domain_host = first_domain.replace('https://', '')

	# Start Chrome
	kill_chrome()
	await asyncio.sleep(2)

	tmpdir = tempfile.mkdtemp(prefix='chrome_oauth_')
	proc = subprocess.Popen(
		[CHROME_EXE, f'--remote-debugging-port={DEBUG_PORT}', f'--user-data-dir={tmpdir}',
		 '--no-first-run', '--no-default-browser-check', 'about:blank'],
		stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
	)

	for _ in range(10):
		await asyncio.sleep(1)
		try:
			httpx.get(f'http://127.0.0.1:{DEBUG_PORT}/json/version', timeout=2)
			break
		except Exception:
			pass
	else:
		print('  [FAIL] Chrome CDP 未就绪')
		proc.terminate()
		shutil.rmtree(tmpdir, ignore_errors=True)
		return results

	async with async_playwright() as p:
		try:
			browser = await p.chromium.connect_over_cdp(f'http://127.0.0.1:{DEBUG_PORT}')
			ctx = browser.contexts[0]
			page = await ctx.new_page()

			# === Step 2: 先登录 LinuxDO ===
			print(f'\n  [Step 1] 登录 LinuxDO...')
			logged_in = await do_login(page, credentials)
			if logged_in:
				print('  [OK] LinuxDO 登录成功!')
			else:
				print('  [FAIL] LinuxDO 登录失败')
				try:
					await page.screenshot(path='login_debug.png')
				except Exception:
					pass
				await page.close()
				await browser.close()
				proc.terminate()
				shutil.rmtree(tmpdir, ignore_errors=True)
				return results

			# === Step 3: 在浏览器中获取 state（确保与浏览器 session 一致）===
			print(f'\n  [Step 2] 获取 {first_provider} state (浏览器内)...')
			state = await get_state_via_browser(page, first_domain)
			if not state:
				print(f'  [FAIL] 无法获取 OAuth state')
				await page.close()
				await browser.close()
				proc.terminate()
				shutil.rmtree(tmpdir, ignore_errors=True)
				return results
			print(f'  State: {state}')

			oauth_url = build_oauth_url(first_provider, state)

			# === Step 4: 导航到 OAuth ===
			print(f'\n  [Step 3] 导航到 OAuth...')
			await page.goto(oauth_url, wait_until='commit', timeout=30000)

			# === Step 5: 统一等待：CF + 允许 + session cookie ===
			print(f'  [Step 4] 等待 OAuth 流程 + session...')
			session_value = await wait_for_oauth_redirect(page, ctx, first_domain_host, max_wait=180)

			if session_value:
				results[first_idx] = session_value
				print(f'  [OK] {first_acc.get("name", "")} session 获取成功!')
			else:
				print(f'  [FAIL] {first_acc.get("name", "")} session 获取失败')
				# 截图
				try:
					await page.screenshot(path='session_fail_debug.png')
				except Exception:
					pass

			# === 后续账号：复用登录态 ===
			for acc_idx in account_indices[1:]:
				acc = accounts[acc_idx]
				provider = acc.get('provider', 'anyrouter')
				name = acc.get('name', '')

				print(f'\n  [NEXT] {name} ({provider})')

				# 在同一个浏览器中导航到新的 OAuth URL
				new_session = await refresh_account_in_session(page, ctx, provider)

				if new_session:
					results[acc_idx] = new_session
					print(f'  [OK] {name} session 获取成功!')
				else:
					print(f'  [FAIL] {name} session 获取失败')

			await page.close()
			await browser.close()
		except Exception as e:
			print(f'  [ERROR] {e}')

	proc.terminate()
	try:
		proc.wait(timeout=5)
	except Exception:
		proc.kill()
	shutil.rmtree(tmpdir, ignore_errors=True)

	return results


async def main():
	print('=' * 60)
	print('Session 自动刷新（真实 Chrome + LinuxDO OAuth）')
	print('=' * 60)

	# Check Chrome
	if not os.path.exists(CHROME_EXE):
		print(f'[ERROR] Chrome 未找到: {CHROME_EXE}')
		sys.exit(1)

	# Load config
	if not os.path.exists(CONFIG_FILE):
		print(f'[ERROR] 配置文件不存在: {CONFIG_FILE}')
		sys.exit(1)

	with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
		accounts = json.load(f)

	print(f'[INFO] 加载 {len(accounts)} 个账号')

	# Check which accounts need refresh, group by credential
	cred_groups = defaultdict(list)  # email -> [(account_index, account)]
	for i, acc in enumerate(accounts):
		name = acc.get('name', f'Account_{i}')
		session = acc.get('cookies', {}).get('session', '')
		api_user = acc.get('api_user', '')
		provider = acc.get('provider', 'anyrouter')

		print(f'  [{i}] {name}...', end=' ')
		if session and check_session_valid(session, api_user, provider):
			print('有效')
			continue

		print('过期', end='')
		cred_email = match_credentials(name)
		if cred_email:
			cred_groups[cred_email].append(i)
			print('')
		else:
			print(' -> 无匹配凭据，跳过')

	total_to_refresh = sum(len(v) for v in cred_groups.values())
	if total_to_refresh == 0:
		print('\n[OK] 所有有凭据的账号 session 都有效')
		return

	print(f'\n[INFO] 需要刷新 {total_to_refresh} 个账号，分 {len(cred_groups)} 组')

	# Process each credential group
	updated = 0
	for cred_email, acc_indices in cred_groups.items():
		results = await refresh_credential_group(cred_email, acc_indices, accounts)

		for acc_idx, new_session in results.items():
			accounts[acc_idx]['cookies']['session'] = new_session
			updated += 1

			# Save immediately
			with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
				json.dump(accounts, f, indent=2, ensure_ascii=False)

			# Verify
			acc = accounts[acc_idx]
			api_user = acc.get('api_user', '')
			provider = acc.get('provider', 'anyrouter')
			if check_session_valid(new_session, api_user, provider):
				print(f'  [VERIFY] {acc.get("name", "")} - Session 验证通过!')
			else:
				print(f'  [VERIFY] {acc.get("name", "")} - Session 验证未通过（可能需要 WAF cookies）')

	print(f'\n{"=" * 60}')
	print(f'[RESULT] 刷新完成: {updated}/{total_to_refresh} 成功')
	print(f'{"=" * 60}')


if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		print('\n[INFO] 用户中断')
		kill_chrome()
		sys.exit(0)
