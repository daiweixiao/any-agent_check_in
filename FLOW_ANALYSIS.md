# AgentRouter 登录与签到流程完整分析

## 🔐 完整流程图

```
用户点击登录
    ↓
【第三方 OAuth 认证】Linux.do
    ↓
OAuth 授权回调（带 code 和 state）
    ↓
【1. OAuth 回调处理】
GET /api/oauth/linuxdo?code=xxx&state=xxx
    ↓
服务器验证 OAuth，创建/更新用户
    ↓
【自动签到触发】checked_in: true
    ↓
【返回用户信息 + 设置 Session Cookie】
Set-Cookie: session=xxx (有效期30天)
    ↓
【2. 获取系统状态】
GET /api/status
    ↓
返回系统公告、配置信息
    ↓
【3. 获取用户模型列表】
GET /api/user/models
    ↓
返回可用模型（需要 new-api-user 头）
    ↓
【4. 获取 Token 列表】
GET /api/token/?p=1&size=10
    ↓
返回用户的 API Keys
    ↓
【用户进入控制台】
```

---

## 📋 详细请求流程分析

### **阶段 1: OAuth 登录回调**

#### **请求信息**
```http
GET /api/oauth/linuxdo?code=0uIuIfEzSqGW9EXyCr5QFoa7mBigbWo3&state=S83ReejONfFq
Host: agentrouter.org
Cookie: _ga=...; acw_tc=...; session=旧session
new-api-user: -1  ← 未登录状态
```

#### **响应信息**
```http
HTTP/1.1 200 OK
Set-Cookie: session=MTc2MTQwNjM2NHxEW...=; Path=/; Expires=Mon, 24 Nov 2025 15:32:44 GMT; Max-Age=2592000; HttpOnly; SameSite=Strict

{
  "data": {
    "id": 34877,
    "username": "linuxdo_34877",
    "display_name": "维 戴",
    "role": 1,
    "status": 1,
    "quota": 0,           // 签到前余额（单位：credits * 500000）
    "used_quota": 0,
    "group": "default",
    "checked_in": true,   // ⭐ 关键：已自动签到
    "last_login_time": 1761182671
  },
  "success": true
}
```

#### **关键机制**
- **自动签到触发点**：OAuth 登录成功时
- **Session Cookie**：
  - 有效期：30天（Max-Age=2592000）
  - HttpOnly：防止 JS 访问
  - SameSite=Strict：防止 CSRF 攻击
- **用户状态**：`checked_in: true` 表示签到完成

---

### **阶段 2: 获取系统状态**

#### **请求信息**
```http
GET /api/status
Host: agentrouter.org
Cookie: session=MTc2MTQwNjM2NHx...（新 session）
new-api-user: -1  ← 仍然是 -1，因为还在初始化
```

#### **响应信息**
```json
{
  "data": {
    "system_name": "Agent Router",
    "announcements": [...],           // 系统公告
    "quota_per_unit": 500000,         // 单位换算：$1 = 500000 credits
    "price": 7.3,                     // 价格信息
    "server_address": "https://agentrouter.org",
    "docs_link": "https://docs.agentrouter.org",
    "email_verification": true,
    "github_oauth": true,
    "linuxdo_oauth": true,
    // ... 更多配置
  },
  "success": true
}
```

#### **作用**
- 获取系统配置和公告
- 确认服务状态
- 获取单位换算规则（500000 credits = $1）

---

### **阶段 3: 获取可用模型**

#### **请求信息**
```http
GET /api/user/models
Host: agentrouter.org
Cookie: session=MTc2MTQwNjM2NHx...
new-api-user: 34877  ← ⭐ 已更新为实际用户 ID
Referer: https://agentrouter.org/console/token
```

#### **响应信息**
```json
{
  "data": [
    "deepseek-r1-0528",
    "deepseek-v3.1",
    "deepseek-v3.2",
    "glm-4.5",
    "glm-4.6",
    "gpt-5",
    "grok-code-fast-1"
  ],
  "success": true
}
```

#### **关键变化**
- `new-api-user` 从 `-1` 变为 `34877`
- 前端已完成用户信息初始化
- 开始请求需要认证的资源

---

### **阶段 4: 获取 Token 列表**

#### **请求信息**
```http
GET /api/token/?p=1&size=10
Host: agentrouter.org
Cookie: session=MTc2MTQwNjM2NHx...
new-api-user: 34877
```

#### **响应信息**
```json
{
  "data": {
    "page": 1,
    "page_size": 10,
    "total": 0,
    "items": []  // 新用户暂无 Token
  },
  "success": true
}
```

---

## 🔍 核心机制深度分析

### **1. Session Cookie 机制**

```
MTc2MTQwNjM2NHxEWDhFQVFMX2dBQUJFQUVRQUFEXzRfLUFBQWNHYzNSeWFXNW5EQW9BQ0hWelpYSnVZVzFsQm5OMGNtbHVad3dQQUExc2FXNTFlR1J2WHpNME9EYzNCbk4wY21sdVp3d0dBQVJ5YjJ4bEEybHVkQVFDQUFJR2MzUnlhVzVuREFnQUJuTjBZWFIxY3dOcGJuUUVBZ0FDQm5OMGNtbHVad3dIQUFWbmNtOTFjQVp6ZEhKcGJtY01DUUFIWkdWbVlYVnNkQVp6ZEhKcGJtY01CUUFEWVdabUJuTjBjbWx1Wnd3R0FBUTBNVGxGQm5OMGNtbHVad3dOQUF0dllYVjBhRjl6ZEdGMFpRWnpkSEpwYm1jTURnQU1Vemd6VW1WbGFrOU9aa1p4Qm5OMGNtbHVad3dFQUFKcFpBTnBiblFFQlFEOUFSQjZ8JIfapZbxzSc9wHcoiPG4f8CPG5bJx1y_ok3MiqQbcoI=
```

这是一个 **Base64 编码的加密 Session**，包含：
- 用户 ID
- 用户名（linuxdo_34877）
- 角色权限
- 状态信息
- OAuth 状态
- 签名校验

### **2. new-api-user 请求头**

| 阶段 | new-api-user 值 | 含义 |
|------|----------------|------|
| OAuth 回调前 | `-1` | 未登录/匿名用户 |
| OAuth 回调后 | `34877` | 已登录，实际用户 ID |
| 后续请求 | `34877` | 持续使用，用于 API 调用统计 |

**作用：**
- API 使用量统计
- 权限验证
- 用户识别

### **3. 自动签到机制**

#### **触发时机：**
```python
# 从代码 utils/config.py 可以看出
agentrouter: ProviderConfig(
    sign_in_path=None,  # ← 无需签到接口
    bypass_method=None   # ← 无需 WAF 绕过
)
```

#### **签到逻辑：**
```python
# 从 checkin.py 的逻辑
if provider_config.needs_manual_check_in():
    # AnyRouter 需要手动调用签到接口
    success = execute_check_in(...)
else:
    # AgentRouter 自动完成
    print('Check-in completed automatically (triggered by user info request)')
```

#### **实际实现：**
- OAuth 登录时后端自动完成签到
- 查询用户信息接口也会触发签到检查
- 无需前端主动调用签到接口

---

## 🆚 对比：AnyRouter vs AgentRouter

| 特性 | AnyRouter | AgentRouter |
|-----|-----------|-------------|
| **WAF 防护** | ✅ 有（需要绕过） | ❌ 无 |
| **签到接口** | `POST /api/user/sign_in` | 无（自动触发） |
| **触发时机** | 手动调用签到 API | OAuth 登录/查询用户信息 |
| **Cookies 需求** | WAF cookies + Session | 仅 Session |
| **Playwright** | ✅ 必需（获取 WAF cookies） | ❌ 不需要 |
| **请求复杂度** | 高 | 低 |

---

## 🔄 自动签到脚本执行流程

### **对于 AgentRouter**

```python
# 1. 准备 cookies（无需 WAF）
all_cookies = user_cookies  # 直接使用用户 session

# 2. 创建 HTTP 客户端
client = httpx.Client()
client.cookies.update(all_cookies)

# 3. 设置请求头
headers = {
    'User-Agent': '...',
    'Cookie': 'session=xxx',
    'new-api-user': '34877'  # 关键请求头
}

# 4. 获取用户信息（自动触发签到）
response = client.get('https://agentrouter.org/api/user/self', headers=headers)

# 5. 解析余额
data = response.json()
quota = data['quota'] / 500000  # 转换为美元
used = data['used_quota'] / 500000

# 6. 完成（无需额外签到请求）
print(f'当前余额: ${quota}')
```

---

## 📊 数据流向图

```
                    前端                                后端
                     |                                   |
    [1] OAuth 登录请求 |                                   |
         |------------>|  验证 OAuth code                  |
         |             |  查询/创建用户                     |
         |             |  ⭐ 自动执行签到逻辑               |
         |             |  生成 Session Cookie              |
         |<------------|  返回用户信息 + checked_in: true  |
                     |                                   |
    [2] 获取系统状态   |                                   |
         |------------>|  返回系统配置                      |
         |<------------|                                   |
                     |                                   |
    [3] 初始化用户信息 |                                   |
         |  (前端设置 new-api-user = 34877)                |
                     |                                   |
    [4] 获取可用模型   |                                   |
         |------------>|  验证 Session + new-api-user      |
         |<------------|  返回模型列表                      |
                     |                                   |
    [5] 获取 Token    |                                   |
         |------------>|  验证权限                          |
         |<------------|  返回 API Keys                    |
```

---

## 💡 关键要点总结

### **登录流程**
1. 用户通过 Linux.do OAuth 登录
2. 服务器验证 OAuth，创建/更新用户
3. **自动完成签到**（无需前端操作）
4. 返回 Session Cookie（有效期30天）

### **认证机制**
- **Session Cookie**: 主要认证凭证
- **new-api-user**: API 调用标识（用户 ID）
- **OAuth State**: 防止 CSRF 攻击

### **签到机制**
- **触发点**: OAuth 登录成功时
- **实现方式**: 后端自动处理
- **验证方式**: `checked_in: true` 字段

### **安全特性**
- HttpOnly Cookie（防 XSS）
- SameSite=Strict（防 CSRF）
- OAuth State 验证
- Session 加密存储

---

## 🎯 脚本自动化要点

### **必需配置**
1. **Session Cookie**: 登录后获取
2. **API User ID**: 从请求头 `new-api-user` 获取

### **可选配置**
- 通知推送（钉钉、邮件等）

### **执行逻辑**
```python
# 只需访问用户信息接口即可
response = httpx.get(
    'https://agentrouter.org/api/user/self',
    headers={'new-api-user': '34877'},
    cookies={'session': 'xxx'}
)

# 签到已自动完成
# 解析余额信息即可
```

### **优势**
- ✅ 无需浏览器自动化
- ✅ 无需绕过 WAF
- ✅ 请求简单高效
- ✅ 签到自动触发
