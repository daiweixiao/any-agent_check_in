#!/usr/bin/env python3
"""
AnyRouter 自动签到脚本（无需浏览器版本）
通过纯代码解析 WAF acw_sc__v2 cookie，无需 Playwright

核心思路来自 https://github.com/zhx47/anyrouter
"""

import json
import os
import re
import subprocess
import sys
import tempfile

import httpx

# ==================== 配置 ====================

ANYROUTER_DOMAIN = 'https://anyrouter.top'

HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
	'Accept': 'application/json, text/plain, */*',
	'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
	'Accept-Encoding': 'gzip, deflate, br',
	'Origin': ANYROUTER_DOMAIN,
	'Referer': f'{ANYROUTER_DOMAIN}/',
	'Connection': 'keep-alive',
	'Sec-Fetch-Dest': 'empty',
	'Sec-Fetch-Mode': 'cors',
	'Sec-Fetch-Site': 'same-origin',
}

# solve_waf.js 的路径（与本脚本同目录）
SOLVE_WAF_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve_waf.js')


def solve_waf_challenge(script_content: str) -> dict | None:
	"""用 Node.js 执行 WAF 挑战脚本，解出 acw_sc__v2 cookie"""
	try:
		# 将 WAF 挑战脚本写入临时文件（避免命令行参数特殊字符问题）
		with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
			f.write(script_content)
			waf_script_path = f.name

		result = subprocess.run(
			['node', SOLVE_WAF_JS, waf_script_path],
			capture_output=True,
			text=True,
			timeout=10,
		)

		os.unlink(waf_script_path)

		if result.returncode == 0 and result.stdout.strip():
			cookies = json.loads(result.stdout.strip())
			if cookies:
				return cookies
		if result.stderr:
			print(f'  [WARN] Node.js stderr: {result.stderr[:200]}')
		return None
	except Exception as e:
		print(f'  [ERROR] 解析 WAF 失败: {e}')
		return None


def get_waf_cookies(domain: str = ANYROUTER_DOMAIN) -> dict | None:
	"""
	获取完整的 WAF cookies (acw_tc + cdn_sec_tc + acw_sc__v2)
	不需要浏览器，纯代码实现
	"""
	print('[WAF] 获取 WAF cookies...')

	try:
		with httpx.Client(timeout=15.0, verify=False, follow_redirects=True) as client:
			# 第一次请求获取 acw_tc 和 cdn_sec_tc，以及挑战脚本
			resp = client.get(
				f'{domain}/api/user/self',
				headers={
					'User-Agent': HEADERS['User-Agent'],
					'Accept': 'text/html,application/xhtml+xml',
				},
			)

			# 提取已有 cookies (acw_tc, cdn_sec_tc)
			waf_cookies = dict(resp.cookies)
			print(f'  [INFO] 服务器设置的 cookies: {list(waf_cookies.keys())}')

			# 检查响应是否是 WAF 挑战页面
			if resp.status_code == 200 and '<script>' in resp.text:
				# 提取脚本内容
				scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', resp.text, re.IGNORECASE)
				if scripts:
					print(f'  [INFO] 检测到 WAF 挑战脚本，正在用 Node.js 解析...')
					solved = solve_waf_challenge(scripts[0])
					if solved:
						waf_cookies.update(solved)
						print(f'  [OK] WAF 解析成功，获得 cookies: {list(waf_cookies.keys())}')
					else:
						print(f'  [FAIL] WAF 解析失败')
						return None

			# 验证是否获取了所有必需的 WAF cookies
			required = ['acw_tc', 'cdn_sec_tc', 'acw_sc__v2']
			missing = [c for c in required if c not in waf_cookies]
			if missing:
				print(f'  [WARN] 缺少 WAF cookies: {missing}')
				# 不一定需要全部，继续尝试
			else:
				print(f'  [OK] 全部 WAF cookies 获取成功')

			return waf_cookies

	except Exception as e:
		print(f'  [ERROR] 获取 WAF cookies 失败: {e}')
		return None


def check_in_account(
	session: str,
	api_user: str,
	name: str = '',
	domain: str = ANYROUTER_DOMAIN,
	sign_in_path: str = '/api/user/sign_in',
	needs_waf: bool = True,
) -> bool:
	"""为单个账号执行签到"""
	display_name = name or f'user_{api_user}'
	print(f'\n{"="*60}')
	print(f'[ACCOUNT] {display_name}')
	print(f'{"="*60}')

	# 1. 获取 WAF cookies（仅 AnyRouter 需要）
	if needs_waf:
		waf_cookies = get_waf_cookies(domain)
		if not waf_cookies:
			print(f'  [FAIL] 无法获取 WAF cookies')
			return False
		all_cookies = {**waf_cookies, 'session': session}
	else:
		print(f'  [INFO] 此平台无需 WAF 处理')
		all_cookies = {'session': session}

	headers = {**HEADERS, 'new-api-user': api_user}
	headers['Origin'] = domain
	headers['Referer'] = f'{domain}/'

	try:
		with httpx.Client(timeout=30.0, verify=False, follow_redirects=True) as client:
			# 重要：先用 WAF cookies 做一次请求让 WAF 放行
			# 带上 acw_sc__v2 再请求一次
			resp_verify = client.get(
				f'{domain}/api/user/self',
				headers=headers,
				cookies=all_cookies,
			)

			# 如果返回的还是 HTML（WAF 挑战），说明 cookie 不对，需要重新解析
			if '<script>' in resp_verify.text and 'arg1=' in resp_verify.text:
				print(f'  [INFO] WAF 二次挑战，重新解析...')
				scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', resp_verify.text, re.IGNORECASE)
				if scripts:
					solved = solve_waf_challenge(scripts[0])
					if solved:
						all_cookies.update(solved)
						# 更新 response cookies
						all_cookies.update(dict(resp_verify.cookies))
						# 重新请求
						resp_verify = client.get(
							f'{domain}/api/user/self',
							headers=headers,
							cookies=all_cookies,
						)

			# 3. 获取用户信息
			print(f'  [INFO] 查询用户信息...')
			try:
				user_data = resp_verify.json()
			except Exception:
				print(f'  [FAIL] 响应不是 JSON: {resp_verify.text[:100]}...')
				return False

			if user_data.get('success'):
				data = user_data.get('data', {})
				quota = round(data.get('quota', 0) / 500000, 2)
				used = round(data.get('used_quota', 0) / 500000, 2)
				username = data.get('username', 'unknown')
				print(f'  [OK] 用户: {username}')
				print(f'  [OK] 余额: ${quota}, 已用: ${used}')
			else:
				msg = user_data.get('message', 'Unknown error')
				print(f'  [FAIL] 用户信息获取失败: {msg}')
				if '未登录' in msg or '401' in str(resp_verify.status_code):
					print(f'  [FAIL] Session 已过期，需要重新登录获取')
				return False

			# 4. 执行签到
			if sign_in_path:
				print(f'  [INFO] 执行签到...')
				checkin_headers = {**headers, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
				resp_checkin = client.post(
					f'{domain}{sign_in_path}',
					headers=checkin_headers,
					cookies=all_cookies,
				)

				try:
					result = resp_checkin.json()
					if result.get('ret') == 1 or result.get('code') == 0 or result.get('success'):
						msg = result.get('msg', result.get('message', ''))
						print(f'  [OK] 签到成功! {msg}')
						return True
					else:
						msg = result.get('msg', result.get('message', 'Unknown'))
						print(f'  [INFO] 签到响应: {msg}')
						# "已签到" 也算成功
						if '已' in msg or 'already' in msg.lower():
							print(f'  [OK] 今日已签到过')
							return True
						return False
				except Exception:
					if '<script>' in resp_checkin.text:
						print(f'  [FAIL] 签到请求被 WAF 拦截')
					else:
						print(f'  [FAIL] 签到响应异常: {resp_checkin.text[:100]}')
					return False
			else:
				print(f'  [OK] 此平台无需显式签到（查询用户信息时自动完成）')
				return True

	except Exception as e:
		print(f'  [ERROR] 签到异常: {e}')
		return False


def main():
	"""主函数"""
	print('=' * 60)
	print('AnyRouter 自动签到（无浏览器版本）')
	print('=' * 60)

	# 从环境变量或配置文件加载账号
	accounts = []

	# 优先从环境变量加载
	env_accounts = os.getenv('ANYROUTER_ACCOUNTS')
	if env_accounts:
		try:
			accounts = json.loads(env_accounts)
			print(f'[INFO] 从环境变量加载了 {len(accounts)} 个账号')
		except json.JSONDecodeError:
			print('[ERROR] ANYROUTER_ACCOUNTS 环境变量格式错误')

	# 其次从配置文件加载
	if not accounts:
		config_files = ['accounts.json', 'update_sessions.json', 'test_config.json']
		for config_file in config_files:
			if os.path.exists(config_file):
				try:
					with open(config_file, 'r', encoding='utf-8') as f:
						accounts = json.load(f)
					print(f'[INFO] 从 {config_file} 加载了 {len(accounts)} 个账号')
					break
				except Exception as e:
					print(f'[WARN] 读取 {config_file} 失败: {e}')

	if not accounts:
		print('[ERROR] 未找到账号配置')
		print('  请设置环境变量 ANYROUTER_ACCOUNTS 或创建 accounts.json')
		sys.exit(1)

	# 签到
	success_count = 0
	total_count = len(accounts)

	for i, account in enumerate(accounts):
		name = account.get('name', f'Account_{i+1}')
		session = account.get('cookies', {}).get('session', '')
		api_user = account.get('api_user', '')
		provider = account.get('provider', 'anyrouter')

		if not session or not api_user:
			print(f'\n[SKIP] {name}: 缺少 session 或 api_user')
			continue

		# 根据 provider 设置域名和签到路径
		if provider == 'agentrouter':
			domain = 'https://agentrouter.org'
			sign_in_path = '/api/user/sign_in'
			needs_waf = False
		else:
			domain = ANYROUTER_DOMAIN
			sign_in_path = '/api/user/sign_in'
			needs_waf = True

		success = check_in_account(
			session=session,
			api_user=api_user,
			name=name,
			domain=domain,
			sign_in_path=sign_in_path,
			needs_waf=needs_waf,
		)

		if success:
			success_count += 1

	# 结果统计
	print(f'\n{"="*60}')
	print(f'[RESULT] 签到完成: {success_count}/{total_count} 成功')
	print(f'{"="*60}')

	sys.exit(0 if success_count > 0 else 1)


if __name__ == '__main__':
	main()
