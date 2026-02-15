# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

多站点自动签到系统，支持 AnyRouter/AgentRouter 及 27 个 new-api 公益站（活跃）+ 6 个跳过站点的自动登录和签到。使用 Playwright + 真实 Chrome 进行浏览器自动化（绕过 Cloudflare/WAF），httpx 处理 HTTP 请求和缓存签到。支持 4 个 LinuxDO 账号并行处理（Windows）或串行处理（Linux 服务器自动适配）、Session 缓存加速、密码加密存储、GitHub Actions 云端运行。共探测 66 个站点。

站点配置外置到 `sites.json`（人工维护），运行时数据存储在 `site_info.json`（程序唯一执行数据源）。启动时自动 sync 两个文件，检测新增/移除站点和账号。

## 核心命令

### 依赖管理
```bash
# 安装依赖（使用 uv）
uv sync

# 安装 Playwright 浏览器
uv run playwright install chromium --with-deps

# 或使用传统方式
pip install -r requirements.txt
playwright install chromium
```

### 运行签到
```bash
# 多站点签到（27 站点 x 4 账号，主力脚本）
python multi_site_checkin.py

# AnyRouter/AgentRouter 签到（需要 update_sessions.json）
python auto_checkin.py

# AnyRouter/AgentRouter Session 刷新（session 过期时使用）
python auto_refresh_chrome.py

# 主签到脚本（GitHub Actions 用）
uv run checkin.py
# 或
python checkin.py

# 本地测试（需要配置文件）
python test_session.py update_sessions.json
# Windows 快捷方式
test_session.bat

# 检查 session 有效性
python check_session_expiry.py
```

### 测试
```bash
# 运行通知测试
python tests/test_notify.py

# 本地测试
python test_local.py
```

### 代码质量
```bash
# Ruff 格式化和检查
ruff check .
ruff format .

# Pre-commit hooks
pre-commit run --all-files
```

## 架构设计

### 核心模块

**multi_site_checkin.py** - 多站点自动登录 + 签到（主力脚本）
- 27 个 new-api 公益站 x 4 个 LinuxDO 账号
- 站点配置外置到 `sites.json`，运行数据存储在 `site_info.json`（唯一执行数据源）
- 启动时 `sync_site_info()` 自动同步：检测新站点/新账号/移除站点，跨天重置签到状态
- 两阶段执行：Phase 1 httpx 缓存直连 + Phase 2 浏览器 OAuth
- 4 账号 asyncio.gather 并行（Windows，端口 9222-9225）
- Linux 串行模式：内存 < 3GB 自动切换，或 `--serial` 手动指定（单 Chrome 实例，端口 9222）
- Linux headless：`--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage`
- Session/user_id/access_token 缓存在 site_info.json，过期自动删除并重新 OAuth
- 真实 Chrome + CDP + Playwright 绕过 Cloudflare/WAF
- OAuth 登录后从 localStorage 提取用户 ID 用于签到认证
- 汇总报告按成功/失败/跳过分组，每站点标注账号状态
- 输出详细结果到 checkin_results.json + logs/

**checkin.py** - 主签到逻辑（GitHub Actions 用）
- 使用 Playwright 处理需要 WAF cookies 的站点（anyrouter）
- 使用 httpx 处理标准 API 请求（agentrouter）
- 支持余额变化检测和通知
- 异步执行，支持多账号并发

**auto_refresh_chrome.py** - AnyRouter/AgentRouter Session 自动刷新
- 检测 session 过期 → 自动 OAuth 重新登录获取新 session
- 按 LinuxDO 凭据分组，每组只启动一个 Chrome 实例
- 保存新 session 到 update_sessions.json

**auto_checkin.py** - AnyRouter/AgentRouter 每日签到
- 读取 update_sessions.json 中的 session
- AnyRouter: solve_waf.js 获取 WAF cookies + session 调用 API
- AgentRouter: 直接用 session 调用 API

**utils/config.py** - 配置管理
- `ProviderConfig`: 定义不同平台的配置（domain, API paths, bypass_method）
- `AccountConfig`: 账号配置（cookies, api_user, provider）
- `AppConfig`: 应用级配置，支持从环境变量 `PROVIDERS` 加载自定义平台
- 默认支持 anyrouter 和 agentrouter 两个平台

**utils/notify.py** - 通知系统
- 支持多种通知方式：Server酱、PushPlus、邮件、钉钉、飞书、企业微信
- 通过环境变量配置

### 关键设计模式

**两阶段签到** (`multi_site_checkin.py`)
- Phase 1: 用 site_info.json 中的缓存 session，通过 httpx 直接调 API 签到（~30s 完成）
- Phase 2: 对无缓存或缓存过期的站点，启动浏览器走 OAuth 获取新 session
- Session 过期检测：3xx 重定向、401、HTML 响应均视为过期

**账号并行/串行执行**
- Windows：4 个账号通过 asyncio.gather 同时执行，每个账号独立 Chrome 实例（CDP 端口 9222-9225）
- Linux（阿里云等）：自动检测内存 < 3GB 切换串行模式，4 账号依次执行共用端口 9222；也可 `--serial` 手动指定
- Linux Chrome：自动检测路径（`shutil.which`），headless + `--no-sandbox` + 反自动化检测
- Session 文件写入使用 load-merge-save 原子模式（asyncio 单线程安全）

**WAF 绕过策略** (`bypass_method`)
- `waf_cookies`: 使用 Playwright 获取 WAF cookies 后再调用 API（anyrouter）
- `None`: 直接调用 API（agentrouter）

**签到流程差异**
- anyrouter: 需要显式调用 `/api/user/sign_in` 接口
- agentrouter: 查询 `/api/user/self` 时自动完成签到（`sign_in_path=None`）
- new-api 公益站: `POST /api/user/checkin`，需要 session cookie + `New-Api-User` 请求头
- POST 404 时自动降级为 GET（部分站点路由差异）

**Session 管理**
- Session cookie 有效期约 30 天
- 每次签到会刷新活跃状态
- 缓存在 site_info.json 各站点各账号条目中（含 session、user_id、access_token、更新日期）
- 过期时自动清除缓存并走 OAuth 重新获取
- 跨天自动重置 checkin_status 为 pending（保留 session）

### 配置结构

**环境变量**
- `ANYROUTER_ACCOUNTS`: JSON 数组，包含所有账号配置
- `PROVIDERS`: 可选，自定义平台配置（覆盖默认）
- `ENCRYPTION_KEY`: Fernet 加密密钥
- 通知相关：`SERVERPUSHKEY`, `PUSHPLUS_TOKEN`, `EMAIL_*`, `DINGDING_WEBHOOK` 等

**账号配置格式**
```json
{
  "name": "账号显示名称",
  "provider": "agentrouter",
  "cookies": {"session": "session_value"},
  "api_user": "12345"
}
```

## GitHub Actions

**主工作流** (`.github/workflows/checkin.yml`)
- 每天 UTC 0点运行（北京时间 8:00）
- 使用 windows-latest runner
- 缓存策略：uv 依赖、Playwright 浏览器、余额历史
- 支持手动触发 (`workflow_dispatch`)

**Session 检查** (`.github/workflows/check-session.yml`)
- 独立的 session 有效性检查工作流

## 常见任务

### 添加新的 new-api 公益站

1. 在 `sites.json` 中添加新站点配置：
   ```json
   "site_key": {
     "domain": "https://example.com",
     "name": "站点名称",
     "client_id": "xxx"
   }
   ```
2. `domain` 必填，`name` 和 `client_id` 可选（运行时自动从 `/api/status` 获取）
3. 如需跳过某站点，添加 `"skip": true, "skip_reason": "原因"`
4. 如需限制账号，添加 `"accounts": ["ZHnagsan", "caijijiji"]`（默认所有账号）
5. 运行脚本时 `sync_site_info()` 自动检测新站点并创建 pending 条目

### 添加新平台支持（AnyRouter/AgentRouter 类型）

1. 在 `utils/config.py` 的 `AppConfig.load_from_env()` 中添加新的 `ProviderConfig`
2. 或通过环境变量 `PROVIDERS` 动态配置
3. 确定是否需要 WAF bypass（设置 `bypass_method`）
4. 确定签到接口路径（`sign_in_path`，可为 None）

### 调试 Session 失效

1. 使用 `test_session.py` 本地测试
2. 查看 `QUICK_FIX.md` 快速修复指南
3. 查看 `SESSION_TROUBLESHOOTING.md` 详细排查
4. 检查 API 响应是否为 HTML（表示 session 过期）
5. 在 site_info.json 中删除对应账号的 session 字段可强制重新 OAuth

### 修改签到逻辑

- AnyRouter/AgentRouter: `checkin.py` 的 `check_in_account()` 和 `get_waf_cookies()`
- new-api 公益站:
  - httpx 直连: `do_checkin_via_httpx()` - 缓存 session 快速签到
  - 浏览器签到: `do_checkin_via_browser()` - OAuth 登录后签到
  - OAuth 登录: `oauth_login_site()` - LinuxDO OAuth 流程
  - 用户 ID: `get_user_id_from_page()` - 从 localStorage 提取
  - 结果处理: `handle_checkin_result()` - httpx 和浏览器共用
- 注意区分不同 provider 的处理方式和认证要求

## 数据文件关系

```
sites.json                    ← 人工维护（添加/删除/跳过站点）
site_info.json                ← 程序唯一执行数据源（sync 自动同步 sites.json 变更）
                                含 session、user_id、签到状态、站点探测结果等
checkin_results.json          ← 程序自动追加（历史签到记录）
logs/checkin_*.log            ← 程序自动生成（详细日志）
```

## 代码风格

- 使用 Ruff 格式化（单引号、tab 缩进）
- 异步函数使用 `async/await`
- 错误处理：捕获具体异常，提供详细错误信息
- 日志输出：使用 emoji 和清晰的格式

## 安全注意事项

- 密码使用 Fernet 加密存储
- Session cookies 通过 GitHub Secrets 保护
- 不要在代码中硬编码敏感信息
- `.gitignore` 已配置忽略 `.env`、配置文件和运行时数据

## 工具脚本

- `encrypt_password.py`: 密码加密工具
- `convert_config.py`: 配置格式转换
- `generate_config.py`: 生成配置模板
- `auto_refresh_chrome.py`: Chrome 浏览器方式刷新 session（推荐，处理 Cloudflare/WAF）
- `test_session.py`: 本地 session 测试工具
- `solve_waf.js`: 阿里云 WAF acw_sc__v2 cookie 求解器
- `probe_sites.py`: 站点探测脚本（检查存活、版本、签到状态）

## 关键技术文档

- `TECHNICAL_GUIDE.md`: 技术深度指南（防护机制分析、破解方案、多站点签到系统、踩坑记录）
- `SITE_REGISTRY.md`: 站点信息注册表（66个站点清单、账号映射、技术问题索引 -> 指向 TECHNICAL_GUIDE.md）
