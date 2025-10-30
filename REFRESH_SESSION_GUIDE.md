# AgentRouter Session Cookie 刷新指南

## 问题说明

当你看到以下错误时，说明 AgentRouter 账号的 session cookie 已过期：

```
Failed to get user info: HTTP 401
[FAILED] xxx: Session expired or invalid, please update cookies
```

## 解决方案

### 方法一：使用自动刷新脚本（推荐）

使用项目提供的自动刷新脚本 `auto_refresh_session.py`：

```bash
python auto_refresh_session.py
```

这个脚本会：
1. 自动检测所有过期的 session cookies
2. 使用浏览器自动登录并获取新的 session
3. 更新配置文件中的 cookies

**注意：** 需要在 `.env` 文件中配置相应账号的用户名和密码。

### 方法二：手动刷新 Session Cookie

#### 步骤 1: 在浏览器中登录

1. 打开 Chrome/Edge 浏览器（推荐使用隐私模式）
2. 访问 [AgentRouter 登录页面](https://agentrouter.org/login)
3. 使用你的账号和密码登录成功

#### 步骤 2: 获取 Session Cookie

1. 按 `F12` 打开开发者工具
2. 切换到 **Application** (应用程序) 标签页
3. 左侧菜单找到 **Storage > Cookies > https://agentrouter.org**
4. 在右侧列表中找到名为 `session` 的 cookie
5. 双击 `Value` 列，复制完整的 session 值（一串很长的字符串）

#### 步骤 3: 更新配置文件

在 `test_multi_accounts.py` 中找到对应的账号配置，更新 `session` 值：

```python
{
    "name": "账号1 - AgentRouter",
    "provider": "agentrouter",
    "cookies": {
        "session": "新的session值粘贴在这里"
    },
    "api_user": "34877"
}
```

#### 步骤 4: 测试验证

运行测试脚本验证新的 session 是否有效：

```bash
python test_multi_accounts.py
```

如果看到以下输出，说明更新成功：

```
:money: Current balance: $xxx.x, Used: $x.x
[INFO] xxx: Check-in completed automatically
[SUCCESS] xxx: Check-in successful!
```

## 需要更新的账号列表

根据最新测试结果，以下 **5 个 AgentRouter 账号** 的 session 已过期：

1. ✅ **账号1 - AgentRouter** (api_user: 34877)
2. ✅ **GitHub主号 - 余额最多 - AgentRouter** (api_user: 34327)
3. ✅ **linuxdo_caijijiji - dw2621097668@gmail - AgentRouter** (api_user: 34877)
4. ✅ **ZHnagsan - linuxdo_2621097668qq.com - AgentRouter** (api_user: 34874)
5. ✅ **heshangd - linuxdo_2330702014@st.btbu.edu.cn - AgentRouter** (api_user: 45551)

**AnyRouter 账号状态良好，无需更新。**

## Session Cookie 有效期

- AgentRouter 的 session cookie 通常有效期为 **7-14 天**
- 建议设置自动化任务定期刷新 session
- 也可以使用 `check_session_expiry.py` 检查 session 状态

## 自动化刷新

为了避免频繁手动更新，可以：

1. **使用 GitHub Actions**（推荐）
   - 配置 `.github/workflows/auto_refresh.yml`
   - 每周自动刷新一次 session

2. **本地定时任务**
   ```bash
   # Linux/Mac (crontab)
   0 0 * * 0 cd /path/to/project && python auto_refresh_session.py
   
   # Windows (任务计划程序)
   设置每周日午夜运行 auto_refresh_session.py
   ```

## 常见问题

### Q: 为什么 session 会过期？
A: 出于安全考虑，网站会定期让 session cookie 失效，要求用户重新登录。

### Q: 能否使用永久性的认证方式？
A: 目前 AgentRouter 只支持基于 session cookie 的认证，没有 API Token 等永久认证方式。

### Q: 自动刷新脚本安全吗？
A: 脚本使用 Playwright 模拟真实浏览器登录，不会泄露你的凭据。建议将密码存储在 `.env` 文件中，不要提交到 Git。

## 技术支持

如遇到问题，请查看：
- `AUTO_LOGIN_README.md` - 自动登录功能详细说明
- `AUTO_LOGIN_SECURITY_GUIDE.md` - 安全最佳实践
- `ADD_ACCOUNT_GUIDE.md` - 账号配置完整指南
