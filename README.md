# 多站点自动签到系统

> 支持 27 个 new-api 公益站 + AnyRouter/AgentRouter 的自动签到，4 账号并行/串行，Session 缓存加速

[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## 特性

- 27 个 new-api 公益站自动签到（LinuxDO OAuth 登录）
- AnyRouter / AgentRouter 签到支持
- 4 个 LinuxDO 账号并行处理（Windows）/ 串行处理（Linux 服务器自动适配）
- Session 缓存 + httpx 直连（缓存命中时 ~30s 完成全部签到）
- 两阶段执行：Phase 1 缓存快速签到 -> Phase 2 浏览器 OAuth 补充
- 真实 Chrome + CDP + Playwright 绕过 Cloudflare/WAF
- 密码 Fernet 加密存储
- GitHub Actions 定时自动运行
- 多种通知推送（Server酱、PushPlus、邮件、钉钉等）

---

## 快速开始

### 本地运行

#### 1. 安装依赖

```bash
pip install httpx playwright cryptography
playwright install chromium
```

#### 2. 运行多站点签到

```bash
python multi_site_checkin.py

# Linux 服务器（如阿里云）自动检测内存，< 3GB 自动串行
# 也可手动指定串行模式
python multi_site_checkin.py --serial
```

脚本会自动：
1. 同步 `sites.json` 到 `site_info.json`（检测新站点/账号变更）
2. 用缓存 session 通过 httpx 直接签到（Phase 1）
3. 对无缓存的站点启动浏览器 OAuth 登录（Phase 2）
4. 保存新 session 到 site_info.json 供下次使用

首次运行约 22 分钟（全部走 OAuth），后续运行约 7 分钟（大部分走缓存）。

#### 3. 查看结果

- `checkin_results.json` - 签到结果（每个账号每个站点的状态）
- `site_info.json` - 运行数据（session 缓存、签到状态、站点信息）
- `logs/checkin_*.log` - 详细运行日志

### GitHub Actions（全自动）

#### Step 1: Fork/上传代码到 GitHub

1. 创建私有仓库：https://github.com/new
2. 上传代码（使用 `git_push.bat`）

#### Step 2: 配置 Secrets

访问：`https://github.com/你的用户名/仓库名/settings/secrets/actions`

添加 2 个 Secrets：

**Secret 1: ANYROUTER_ACCOUNTS**
```bash
# 运行转换工具生成配置
python convert_config.py
# 复制 github_actions_config.json 的内容粘贴到 GitHub Secrets
```

**Secret 2: ENCRYPTION_KEY**
```
你的 Fernet 加密密钥
```

#### Step 3: 手动触发测试

1. 进入 Actions 页面
2. 选择工作流
3. 点击 "Run workflow"

每天 UTC 0 点（北京时间 8:00）自动运行。

---

## 签到覆盖范围

### 全部成功（21 个站点 x 4 账号）

老魔公益站、WoW公益站、WONG公益站、余额比寿命长、HotaruAPI、KFC公益站、duckcoding黄鸭、duckcoding-jp、小呆API-base、Embedding公益站、Huan API、慕鸢公益站、NPC API、Jarvis API、云端API、ibsgss公益站、星野Ai新站、Zer0by公益站、Old API、纳米哈基米、Elysiver公益站

### 部分成功（3 个站点）

Einzieg API、dev88公益站、ThatAPI（CF 验证不稳定，非固定失败）

### 站点不可达（3 个站点）

摸鱼公益、佬友freestyle、New API（服务端问题）

### 跳过（6 个站点）

uibers、小呆API、MTU公益、略貌取神、六哥API、不知名公益站（权限不足）

> 详细站点信息见 [SITE_REGISTRY.md](./SITE_REGISTRY.md)

---

## 项目结构

```
.
├── multi_site_checkin.py    # 主力脚本：27 站点 x 4 账号自动签到
├── sites.json               # 站点配置（人工维护：添加/删除/跳过）
├── site_info.json           # 运行数据（程序维护：session/签到状态/探测结果）
├── checkin.py               # AnyRouter/AgentRouter 签到（GitHub Actions 用）
├── auto_checkin.py          # AnyRouter/AgentRouter 每日签到
├── auto_refresh_chrome.py   # Session 自动刷新
├── probe_sites.py           # 站点探测（存活/版本/签到状态）
├── encrypt_password.py      # 密码加密工具
├── convert_config.py        # 配置转换工具
├── solve_waf.js             # WAF cookie 求解器
├── checkin_results.json     # 签到结果（自动生成）
├── .github/workflows/       # GitHub Actions 配置
│   ├── checkin.yml
│   └── check-session.yml
├── utils/
│   ├── config.py            # 配置管理
│   └── notify.py            # 通知系统
├── SITE_REGISTRY.md         # 站点注册表（66 个站点）
├── TECHNICAL_GUIDE.md       # 技术深度指南
└── docs/                    # 操作文档
```

---

## 性能

| 场景 | 耗时 | 说明 |
|------|------|------|
| 首次运行（无缓存） | ~22 分钟 | 全部走浏览器 OAuth |
| 日常运行（有缓存） | ~7 分钟 | 大部分走 httpx 直连，少量 OAuth |
| 缓存全命中 | ~1-2 分钟 | 所有站点 httpx 直连 |

### Linux 服务器部署（阿里云等）

```bash
# 安装 Chromium
sudo dnf install -y chromium        # CentOS/RHEL/Alibaba Cloud Linux
sudo apt install -y chromium-browser # Ubuntu/Debian

# 运行（自动 headless + 串行模式）
python multi_site_checkin.py
```

Linux 环境自动适配：
- Chrome 路径自动检测（`google-chrome` / `chromium-browser` / `chromium`）
- 内存 < 3GB 自动切换串行模式（单 Chrome 实例，端口 9222）
- headless 模式 + `--no-sandbox` + 反自动化检测
- 可手动强制串行：`python multi_site_checkin.py --serial`

| 场景（串行模式） | 耗时 | 说明 |
|------|------|------|
| 日常运行（有缓存） | ~10 分钟 | 4 账号依次执行 |
| 缓存全命中 | ~2-3 分钟 | 仅 httpx 直连 |

优化前（串行 5 账号无缓存）耗时 96 分钟，优化后提速 92%。

---

## 配置通知（可选）

### Server酱（推荐）

1. 访问：https://sct.ftqq.com/
2. 微信扫码登录获取 SendKey
3. 添加 GitHub Secret：`SERVERPUSHKEY` = 你的 SendKey

其他支持：PushPlus、邮件、钉钉、飞书、企业微信

---

## 常见问题

**Q: 每天需要手动运行吗？**
A: 本地需要手动运行 `python multi_site_checkin.py`。配置 GitHub Actions 后可全自动。

**Q: Session 会过期吗？**
A: 会，约 30 天。但脚本会自动检测过期并重新 OAuth 获取新 session，无需手动处理。

**Q: 缓存文件可以删除吗？**
A: `site_info.json` 中的 session 缓存删除后下次运行会重新走 OAuth（耗时更长），但不影响功能。

**Q: GitHub Actions 免费吗？**
A: 是的，每月 2000 分钟免费额度，签到只需几分钟/次。

---

## 安全说明

- 密码使用 Fernet 加密存储
- GitHub Secrets 加密保护
- 使用私有仓库保护隐私
- `.gitignore` 防止敏感文件泄露（.env、site_info.json 等）

---

## 技术文档

- [SITE_REGISTRY.md](./SITE_REGISTRY.md) - 站点注册表（66 个站点清单、账号映射、状态）
- [TECHNICAL_GUIDE.md](./TECHNICAL_GUIDE.md) - 技术深度指南（防护绕过、签到机制、踩坑记录）
- [docs/QUICK_START.md](./docs/QUICK_START.md) - 快速开始
- [docs/GITHUB_ACTIONS_SETUP.md](./docs/GITHUB_ACTIONS_SETUP.md) - GitHub Actions 配置
- [docs/PASSWORD_ENCRYPTION_GUIDE.md](./docs/PASSWORD_ENCRYPTION_GUIDE.md) - 密码加密指南

---

## License

MIT License
