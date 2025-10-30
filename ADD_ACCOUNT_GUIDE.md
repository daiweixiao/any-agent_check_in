# 添加新账号完整指南

## 🎯 三步添加新账号

### **步骤 1: 获取新账号信息**
### **步骤 2: 添加到配置**
### **步骤 3: 测试验证**

---

## 📱 步骤 1: 获取新账号信息

### **使用不同浏览器（最简单）**

假设你要添加第3个账号：

1. **使用 Firefox 浏览器**（或任何未登录的浏览器）
   
2. **访问对应网站：**
   - AgentRouter: https://agentrouter.org
   - AnyRouter: https://anyrouter.top

3. **登录你的第3个账号**

4. **按 F12 打开开发者工具**

5. **获取 Session Cookie：**
   ```
   F12 → Application（或应用）标签 
        → 左侧 Cookies 
        → 点击对应域名
        → 找到 "session" 
        → 复制 Value 值
   ```

6. **获取 API User ID：**
   ```
   F12 → Network（或网络）标签
        → 刷新页面或点击任意功能
        → 点击任意请求（如 /api/user/models）
        → 查看 Request Headers（请求标头）
        → 找到 "new-api-user"
        → 复制值
   ```

7. **记录信息：**
   ```
   账号3信息：
   - 平台: agentrouter（或 anyrouter）
   - session: MTc2MTQxMjM0NXxEWDhF... （完整复制）
   - api_user: 35789
   ```

---

## ✏️ 步骤 2: 添加到配置

### **方法 A: 本地测试（test_multi_accounts.py）**

打开 `test_multi_accounts.py`，找到 `ACCOUNTS` 列表：

```python
ACCOUNTS = [
    {
        "name": "账号1 - AgentRouter",
        "provider": "agentrouter",
        "cookies": {
            "session": "MTc2MTQwNjM2NHw..."
        },
        "api_user": "34877"
    },
    {
        "name": "账号2 - AnyRouter",
        "provider": "anyrouter",
        "cookies": {
            "session": "MTc2MTQwNzAwOXw..."
        },
        "api_user": "87260"
    },
    # ⬇️ 在这里添加第3个账号
    {
        "name": "账号3 - AgentRouter",  # 👈 自定义名称
        "provider": "agentrouter",       # 👈 agentrouter 或 anyrouter
        "cookies": {
            "session": "你的第3个账号session"  # 👈 粘贴刚才复制的 session
        },
        "api_user": "你的第3个账号user_id"  # 👈 粘贴刚才复制的 api_user
    },
    # 继续添加第4、5、6个账号...
]
```

**完整示例：**

```python
ACCOUNTS = [
    {
        "name": "主号 - AgentRouter",
        "provider": "agentrouter",
        "cookies": {
            "session": "MTc2MTQwNjM2NHxEWDhFQVFMX2dBQUJFQUVRQUFEXzRfLUFBQWNHYzNSeWFXNW5EQW9BQ0hWelpYSnVZVzFsQm5OMGNtbHVad3dQQUExc2FXNTFlR1J2WHpNME9EYzNCbk4wY21sdVp3d0dBQVJ5YjJ4bEEybHVkQVFDQUFJR2MzUnlhVzVuREFnQUJuTjBZWFIxY3dOcGJuUUVBZ0FDQm5OMGNtbHVad3dIQUFWbmNtOTFjQVp6ZEhKcGJtY01DUUFIWkdWbVlYVnNkQVp6ZEhKcGJtY01CUUFEWVdabUJuTjBjbWx1Wnd3R0FBUTBNVGxGQm5OMGNtbHVad3dOQUF0dllYVjBhRjl6ZEdGMFpRWnpkSEpwYm1jTURnQU1Vemd6VW1WbGFrOU9aa1p4Qm5OMGNtbHVad3dFQUFKcFpBTnBiblFFQlFEOUFSQjZ8JIfapZbxzSc9wHcoiPG4f8CPG5bJx1y_ok3MiqQbcoI="
        },
        "api_user": "34877"
    },
    {
        "name": "小号 - AnyRouter",
        "provider": "anyrouter",
        "cookies": {
            "session": "MTc2MTQwNzAwOXxEWDhFQVFMX2dBQUJFQUVRQUFEX3h2LUFBQVlHYzNSeWFXNW5EQWNBQldkeWIzVndCbk4wY21sdVp3d0pBQWRrWldaaGRXeDBCbk4wY21sdVp3d05BQXR2WVhWMGFGOXpkR0YwWlFaemRISnBibWNNRGdBTWNWSmFhRXhhZW5wbVFVdFZCbk4wY21sdVp3d0VBQUpwWkFOcGJuUUVCUUQ5QXFtNEJuTjBjbWx1Wnd3S0FBaDFjMlZ5Ym1GdFpRWnpkSEpwYm1jTUR3QU5iR2x1ZFhoa2IxODROekkyTUFaemRISnBibWNNQmdBRWNtOXNaUU5wYm5RRUFnQUNCbk4wY21sdVp3d0lBQVp6ZEdGMGRYTURhVzUwQkFJQUFnPT18gkpWU2NiZZhgAqlojXB23X8Uig9zRZOKI0MkHKAspNc="
        },
        "api_user": "87260"
    },
    {
        "name": "备用号 - AgentRouter",
        "provider": "agentrouter",
        "cookies": {
            "session": "MTc2MTQxMjM0NXxEWDhFQVFMX2dBQUJFQUVRQUFEXzRfLUFBQWNHYzNSeWFXNW5EQW9BQ0hWelpYSnVZVzFsQm5OMGNtbHVad3dQQUExc2FXNTFlR1J2WHpNMU56ZzVCbk4wY21sdVp3d0dBQVJ5YjJ4bEEybHVkQVFDQUFJR2MzUnlhVzVuREFnQUJuTjBZWFIxY3dOcGJuUUVBZ0FDQm5OMGNtbHVad3dIQUFWbmNtOTFjQVp6ZEhKcGJtY01DUUFIWkdWbVlYVnNkQVp6ZEhKcGJtY01CUUFEWVdabUJuTjBjbWx1Wnd3R0FBUTBNVGxGQm5OMGNtbHVad3dOQUF0dllYVjBhRjl6ZEdGMFpRWnpkSEpwYm1jTURnQU1Vemd6VW1WbGFrOU9aa1p4Qm5OMGNtbHVad3dFQUFKcFpBTnBiblFFQlFEOUFSQjZ8abcdefgh12345678901234567890abcdefgh="
        },
        "api_user": "35789"
    },
]
```

---

### **方法 B: GitHub Actions（生产环境）**

将多个账号转换为**单行 JSON**：

```json
[{"name":"主号 - AgentRouter","provider":"agentrouter","cookies":{"session":"MTc2MTQwNjM2NHw..."},"api_user":"34877"},{"name":"小号 - AnyRouter","provider":"anyrouter","cookies":{"session":"MTc2MTQwNzAwOXw..."},"api_user":"87260"},{"name":"备用号 - AgentRouter","provider":"agentrouter","cookies":{"session":"MTc2MTQxMjM0NXw..."},"api_user":"35789"}]
```

**配置到 GitHub：**

1. 进入你的 GitHub 仓库
2. `Settings` → `Environments` → `production`
3. 找到现有的 `ANYROUTER_ACCOUNTS` secret
4. 点击编辑（铅笔图标）
5. 替换为新的 JSON（包含所有账号）
6. 保存

---

## 🧪 步骤 3: 测试验证

### **本地测试**

```bash
# 在项目目录运行
uv run python test_multi_accounts.py
```

**期望输出：**

```
======================================================================
🧪 多账号签到测试
======================================================================

✅ 已配置 3 个账号

📋 主号 - AgentRouter
   - Provider: agentrouter
   - Session: ✅
   - API User: ✅

📋 小号 - AnyRouter
   - Provider: anyrouter
   - Session: ✅
   - API User: ✅

📋 备用号 - AgentRouter
   - Provider: agentrouter
   - Session: ✅
   - API User: ✅

======================================================================
🚀 开始执行签到测试
======================================================================

[PROCESSING] Starting to process 主号 - AgentRouter
:money: Current balance: $325.0, Used: $0.0
[SUCCESS] 主号 - AgentRouter: Check-in successful!

[PROCESSING] Starting to process 小号 - AnyRouter
[PROCESSING] Starting browser to get WAF cookies...
:money: Current balance: $250.0, Used: $0.0
[SUCCESS] 小号 - AnyRouter: Check-in successful!

[PROCESSING] Starting to process 备用号 - AgentRouter
:money: Current balance: $150.0, Used: $25.0
[SUCCESS] 备用号 - AgentRouter: Check-in successful!

[STATS] Check-in result statistics:
[SUCCESS] Success: 3/3
[SUCCESS] All accounts check-in successful!
```

---

## 📋 配置模板

### **AgentRouter 账号模板**

```python
{
    "name": "你的账号名称",
    "provider": "agentrouter",
    "cookies": {
        "session": "从 F12 复制的 session"
    },
    "api_user": "从 F12 复制的 user_id"
},
```

### **AnyRouter 账号模板**

```python
{
    "name": "你的账号名称",
    "provider": "anyrouter",
    "cookies": {
        "session": "从 F12 复制的 session"
    },
    "api_user": "从 F12 复制的 user_id"
},
```

---

## ⚠️ 常见问题

### **Q1: 添加账号后报错怎么办？**

**检查清单：**
- ✅ 是否有逗号分隔每个账号
- ✅ session 是否完整复制（很长的字符串）
- ✅ api_user 是否正确（纯数字）
- ✅ provider 是否拼写正确（agentrouter 或 anyrouter）
- ✅ JSON 格式是否正确（花括号、引号）

### **Q2: 如何知道账号是 AgentRouter 还是 AnyRouter？**

看登录的网站域名：
- `agentrouter.org` → `"provider": "agentrouter"`
- `anyrouter.top` → `"provider": "anyrouter"`

### **Q3: 可以添加无限个账号吗？**

理论上可以，但建议：
- **本地测试**: 10个以内
- **GitHub Actions**: 5-10个（执行时间限制）

如果 AnyRouter 账号太多（每个60秒），总时间会很长。

### **Q4: 账号顺序重要吗？**

不重要，脚本会按数组顺序依次处理。建议：
- 把 AgentRouter 账号放前面（快）
- AnyRouter 账号放后面（慢）

### **Q5: 某个账号失败会影响其他账号吗？**

不会！脚本有容错机制：
- 某个账号失败，继续处理下一个
- 只要有1个成功，整体任务就成功
- 查看日志了解具体哪个失败

---

## 🎯 快速参考

### **添加流程总结**

```
1️⃣ 新浏览器登录新账号
    ↓
2️⃣ F12 获取 session + api_user
    ↓
3️⃣ 复制模板，填入信息
    ↓
4️⃣ 添加到 ACCOUNTS 列表
    ↓
5️⃣ 运行测试验证
    ↓
6️⃣ 部署到 GitHub Actions
```

### **JSON 压缩工具**

如果需要转换为单行（GitHub Secrets）：
- 在线工具: https://jsonformatter.org/json-minify
- 或者使用任意文本编辑器删除换行

---

## 💡 最佳实践

1. **先本地测试**
   - 确保账号信息正确
   - 验证签到成功
   - 再部署到 GitHub

2. **账号命名规范**
   - 使用有意义的名称
   - 包含平台信息
   - 例如：`"主号 - AgentRouter"` 而不是 `"账号1"`

3. **定期更新**
   - Session 约30天有效
   - 提前更新避免失败
   - 设置提醒或通知

4. **记录备份**
   - 保存账号配置到本地文件
   - 方便后续更新
   - 不要提交到 Git（.gitignore）

---

## 🚀 现在就试试！

添加完新账号后，运行：

```bash
uv run python test_multi_accounts.py
```

看到全部 ✅ 就可以部署到 GitHub Actions 了！
