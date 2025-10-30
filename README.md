# AnyRouter / AgentRouter 自动签到

> 自动签到脚本，支持多账号，支持密码加密，支持 GitHub Actions 云端运行

[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## ✨ 特性

- ✅ **多账号支持** - 支持同时管理多个账号
- ✅ **密码加密存储** - 使用 Fernet 加密保护敏感信息
- ✅ **自动签到** - GitHub Actions 定时自动执行
- ✅ **多平台支持** - AgentRouter 和 AnyRouter
- ✅ **通知推送** - 支持微信、邮件等多种通知方式

---

## 🚀 快速开始（5分钟配置）

### 方式 1：GitHub Actions（推荐 - 全自动）

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

# 复制 github_actions_config.json 的内容
# 粘贴到 GitHub Secrets
```

**Secret 2: ENCRYPTION_KEY**
```
Q94uwxjIRzf40zSpyBM3mczOhid4JmoGRM1hylSzJJM=
```

#### Step 3: 手动触发测试

1. 进入 Actions 页面
2. 选择 "AnyRouter 自动签到"
3. 点击 "Run workflow"
4. 等待 5 分钟，查看结果

✅ **完成！** 现在每 6 小时自动签到一次

---

### 方式 2：本地运行

#### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

#### 2. 配置账号

编辑 `test_multi_accounts.py`，配置你的账号信息。

#### 3. 运行签到

```bash
python test_multi_accounts.py
```

---

## 📝 账号配置

### 配置格式

```python
{
    "name": "账号名称",
    "provider": "agentrouter",  # 或 "anyrouter"
    "linuxdo_username": "linuxdo_12345",
    "encrypted_password": "加密后的密码",
    "cookies": {
        "session": "你的 session cookie"
    },
    "api_user": "12345"
}
```

### 获取配置信息

#### 1. 获取 Session Cookie

1. 登录 AgentRouter/AnyRouter
2. 按 F12 打开开发者工具
3. 访问任意 API 接口
4. 找到 Request Headers 中的 `Cookie`
5. 复制 `session=` 后面的值

#### 2. 获取 API User

在 Request Headers 中找到：
- AgentRouter: `new-api-user`
- AnyRouter: `x-api-user`

#### 3. 加密密码

```bash
python encrypt_password.py
# 输入密码，获得加密字符串
```

---

## 🔔 配置通知（可选）

### Server酱（推荐）

1. 访问：https://sct.ftqq.com/
2. 微信扫码登录获取 SendKey
3. 添加 GitHub Secret：
   - Name: `SERVERPUSHKEY`
   - Value: 你的 SendKey

### 其他通知方式

支持：PushPlus、邮件、钉钉、飞书、企业微信

详见：[通知配置文档](./docs/notifications.md)

---

## 🕒 定时任务

当前配置：**每 6 小时执行一次**（0点、6点、12点、18点）

修改定时：编辑 `.github/workflows/checkin.yml`

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # 每6小时
    # - cron: '0 0 * * *'   # 每天0点
    # - cron: '0 8 * * *'   # 每天8点
```

---

## ❓ 常见问题

### Q: Session 会过期吗？

A: 会的，通常 30 天。但每天自动签到可以保持活跃，基本不会过期。

### Q: 如何更新 Session？

A: 重新获取 Session Cookie，更新 GitHub Secret 中的 `ANYROUTER_ACCOUNTS`。

### Q: GitHub Actions 免费吗？

A: 是的！每月 2000 分钟免费额度，签到只需 2-3 分钟/次，完全够用。

### Q: 如何查看运行历史？

A: 访问仓库的 Actions 页面，可以看到所有运行记录和日志。

---

## 📂 项目结构

```
.
├── checkin.py              # 主签到脚本
├── test_multi_accounts.py  # 本地测试配置
├── encrypt_password.py     # 密码加密工具
├── convert_config.py       # 配置转换工具
├── .github/workflows/      # GitHub Actions 配置
│   └── checkin.yml
├── utils/                  # 工具模块
│   ├── config.py
│   └── notify.py
└── docs/                   # 详细文档
```

---

## 🛡️ 安全说明

- ✅ 密码使用 Fernet 加密存储
- ✅ GitHub Secrets 加密保护
- ✅ 使用私有仓库保护隐私
- ✅ `.gitignore` 防止敏感文件泄露

---

## 📄 License

MIT License

---

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 浏览器自动化
- [httpx](https://www.python-httpx.org/) - HTTP 客户端
- [cryptography](https://cryptography.io/) - 加密库

---

## 📮 联系

有问题？提交 [Issue](https://github.com/你的用户名/仓库名/issues)

---

**⭐ 觉得有用？给个 Star 吧！**
