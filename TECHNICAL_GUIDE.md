# 多站点自动签到系统 - 技术深度指南

## 目录

- [一、系统总览](#一系统总览)
- [二、网站防护机制详解](#二网站防护机制详解)
- [三、破解方案详解](#三破解方案详解)
- [四、脚本使用指南](#四脚本使用指南)（含 4.5 probe_sites.py、4.6 脚本架构对比）
- [五、完整工作流程](#五完整工作流程)
- [六、多站点签到系统](#六多站点签到系统)
- [七、问题排查手册](#七问题排查手册)
- [八、配置参考](#八配置参考)（含 8.4 utils/config.py、8.6 安全与密码迁移）
- [附录](#附录踩坑记录)（A-P）

---

## 一、系统总览

### 1.1 涉及的网站

| 平台 | 域名 | 用途 | 防护 | 签到方式 |
|------|------|------|------|----------|
| **AnyRouter** | `anyrouter.top` | AI API 聚合平台 | 阿里云 WAF + Cloudflare | 查询自动签到 |
| **AgentRouter** | `agentrouter.org` | AI API 聚合平台 | 无 WAF | 查询自动签到 |
| **Einzieg API** | `api.einzieg.site` | AI API 公益站 | 无 WAF | POST /api/user/checkin |
| **摸鱼公益** | `clove.cc.cd` | AI API 公益站 | 无 WAF | POST /api/user/checkin |
| **老魔公益站** | `api.2020111.xyz` | AI API 公益站 | 无 WAF | POST /api/user/checkin |
| **WoW公益站** | `linuxdoapi.223384.xyz` | AI API 公益站 | 无 WAF | POST /api/user/checkin |
| **Elysiver公益站** | `elysiver.h-e.top` | AI API 公益站 | 阿里云 WAF | POST /api/user/checkin |
| **WONG公益站** | `wzw.pp.ua` | AI API 公益站 | 无 WAF | POST /api/user/checkin |
| **余额比寿命长** | `new.123nhh.xyz` | AI API 公益站 | 无 WAF（/api/status 响应慢） | POST /api/user/checkin |
| **LinuxDO** | `linux.do` | 论坛（Discourse） | Cloudflare Turnstile | - |
| **LinuxDO Connect** | `connect.linux.do` | OAuth 授权中心 | Cloudflare | - |

> 所有公益站均基于 **new-api** 框架（Go 后端 + React SPA 前端），使用 LinuxDO OAuth 登录。目前已配置 7 个站点，探测发现另有 23 个可添加站点（详见 SITE_REGISTRY.md）。

### 1.2 核心脚本

```
签到类:
  auto_checkin.py         -- AnyRouter/AgentRouter 每日签到（本地用，httpx + Node.js WAF）
  checkin.py              -- 每日签到（GitHub Actions 用，Playwright WAF + 通知 + 余额监控）
  multi_site_checkin.py   -- 多站点自动登录 + 签到（7 站点 x 5 账号，浏览器 OAuth）

Session 管理:
  auto_refresh_chrome.py  -- AnyRouter/AgentRouter Session 自动刷新（真实 Chrome + OAuth）

工具类:
  solve_waf.js            -- WAF acw_sc__v2 cookie 求解器（Node.js，被 auto_checkin.py 调用）
  probe_sites.py          -- 批量站点探测（检查 /api/status，判断 new-api/签到/OAuth）

配置层:
  utils/config.py         -- checkin.py 的配置数据类（ProviderConfig / AccountConfig / AppConfig）
  utils/notify.py         -- 通知模块（Server酱/PushPlus/邮件/钉钉/飞书/企业微信）
```

### 1.3 整体流程

```
┌──────────────────────────────────────────────────────────────┐
│            AnyRouter/AgentRouter 日常签到                      │
│                                                              │
│  auto_checkin.py                                             │
│    ├── 读取 update_sessions.json 中的 session                 │
│    ├── [AnyRouter] solve_waf.js 获取 WAF cookies              │
│    ├── 携带 session + WAF cookies 调用签到 API                 │
│    └── 输出签到结果                                            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│            AnyRouter/AgentRouter Session 过期刷新              │
│                                                              │
│  auto_refresh_chrome.py                                      │
│    ├── 启动 Chrome（临时 profile + CDP 9222 端口）              │
│    ├── Playwright 连接 Chrome                                 │
│    ├── 登录 LinuxDO（CSRF API 方式，绕过 Cloudflare）           │
│    ├── 浏览器访问平台首页（建立 WAF session）                    │
│    ├── 浏览器内获取 OAuth state                                │
│    ├── 导航到 OAuth 授权页面                                    │
│    ├── 自动点击"允许"                                          │
│    ├── SPA 自动交换 code -> session cookie                     │
│    └── 保存新 session 到 update_sessions.json                  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│            多站点登录 + 签到（5 站点 x 5 账号）                  │
│                                                              │
│  multi_site_checkin.py                                       │
│    ├── 启动 Chrome（每个 LinuxDO 账号一个实例）                  │
│    ├── 登录 LinuxDO                                           │
│    ├── 逐站点执行:                                             │
│    │   ├── [Elysiver] 通过浏览器获取 WAF 后的站点配置            │
│    │   ├── 浏览器内获取 OAuth state                             │
│    │   ├── 过滤旧 session cookie（避免捕获 state session）       │
│    │   ├── OAuth 授权 → 获取新 session cookie                   │
│    │   ├── 导航到 SPA /console → localStorage 提取用户 ID       │
│    │   ├── 携带 New-Api-User 头部调用签到 API                    │
│    │   └── 记录签到结果到 checkin_results.json                   │
│    └── 输出汇总报告                                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 二、四个网站逐一分析：如何拦截、如何绕过

### 2.1 AnyRouter (`anyrouter.top`)

#### 网站架构

AnyRouter 是一个 AI API 聚合平台，前端是 Vue/React SPA 单页应用，后端 API 路径以 `/api/` 开头。

```
前端 SPA 页面:  anyrouter.top/            → 返回 HTML + JS bundle
                anyrouter.top/console     → SPA 路由（同一个 HTML）
                anyrouter.top/oauth/linuxdo?code=... → SPA 路由

后端 API:       anyrouter.top/api/user/self     → 用户信息
                anyrouter.top/api/user/sign_in  → 签到
                anyrouter.top/api/oauth/state   → OAuth state
                anyrouter.top/api/oauth/linuxdo → OAuth code 交换
                anyrouter.top/api/status        → 平台状态 + OAuth Client ID
```

#### 拦截方式：阿里云 WAF（3 层 Cookie 验证）

AnyRouter 使用阿里云 Web 应用防火墙。**每一个 HTTP 请求**都必须携带 3 个 WAF cookie 才能到达后端，否则被拦截。

**实际抓包 - 第一次请求（无 cookie）**：
```http
GET https://anyrouter.top/ HTTP/1.1
User-Agent: Mozilla/5.0

--- 响应 ---
HTTP/1.1 200 OK
Set-Cookie: acw_tc=9b6682ab...;path=/;HttpOnly;Max-Age=1800
Set-Cookie: cdn_sec_tc=9b6682ab...;path=/;HttpOnly;Max-Age=1800
Content-Type: text/html

<html>
<script>
var arg1='F05D972BA4165D5FB9B3B61E45F68D5AC39ADC42';
(function(a,c){var G=a0j,d=a();while(!![]){try{
... 500+ 行混淆 JavaScript ...
// 最终执行:
document.cookie = "acw_sc__v2=" + 计算出的值;
document.location.reload();
// 然后是反调试代码:
setInterval(function(){debugger;}, 100);
</script>
</html>
```

3 个 cookie 的来源：

| Cookie | 来源 | 说明 |
|--------|------|------|
| `acw_tc` | 服务器 Set-Cookie | 会话追踪，随响应自动设置 |
| `cdn_sec_tc` | 服务器 Set-Cookie | CDN 安全标记，随响应自动设置 |
| `acw_sc__v2` | JavaScript 计算 | 需要执行混淆脚本得到，**这是关键** |

**实际抓包 - 第二次请求（带完整 cookie）**：
```http
GET https://anyrouter.top/api/user/self HTTP/1.1
Cookie: acw_tc=9b6682ab...; cdn_sec_tc=9b6682ab...; acw_sc__v2=698ed37f...; session=MTc3MDk2OTIzNn...

--- 响应 ---
HTTP/1.1 200 OK
Content-Type: application/json

{"success":true,"data":{"username":"ZHnagsan","quota":50000000,...}}
```

**实际抓包 - 缺少 acw_sc__v2 时**：
```http
GET https://anyrouter.top/api/user/self HTTP/1.1
Cookie: acw_tc=9b6682ab...; cdn_sec_tc=9b6682ab...; session=MTc3MDk2OTIzNn...
（注意：没有 acw_sc__v2）

--- 响应 ---
HTTP/1.1 200 OK
Content-Type: text/html

<html><script>var arg1='...'; ... WAF 挑战页面 ... </script></html>
（返回的是 WAF 挑战页，不是 API JSON）
```

**WAF 脚本的反调试机制**：
- 脚本中嵌入了 `debugger` 语句的无限循环
- 如果在 Chrome DevTools 中打开该页面，会卡在断点上无法继续
- 这是为了阻止开发者分析挑战算法

#### 我们的绕过方案

**方案：Node.js 模拟执行（solve_waf.js）**

```
1. httpx 请求 anyrouter.top/ → 获取 acw_tc + cdn_sec_tc（自动设置）
                              → 获取 HTML 中的 <script> 内容

2. 将脚本内容写入临时文件

3. 用 Node.js 执行 solve_waf.js:
   - 构造假的 document 对象，拦截 cookie setter
   - eval() 执行 WAF 脚本
   - 脚本计算出 acw_sc__v2 并尝试设置 document.cookie
   - 我们的 setter 捕获这个值，立即 process.exit(0) 退出
   - 避免了后续的 debugger 死循环和 reload

4. 输出 JSON: {"acw_sc__v2": "698ed37f..."}

5. 三个 cookie 组合使用，后续 API 请求全部放行
```

#### 特殊坑：OAuth State 绑定

AnyRouter 的 OAuth state 存储在**服务端 session** 中，而服务端 session 通过 WAF cookie 来识别。

```
❌ 错误做法:
   httpx (cookie组A) → GET /api/oauth/state → state="abc"
   浏览器 (cookie组B) → OAuth 回调 → /api/oauth/linuxdo?state=abc
   服务器在 cookie组B 的 session 中找不到 state → 403 "state is empty or not same"

✅ 正确做法:
   浏览器 (cookie组B) → 先访问首页建立 WAF → fetch /api/oauth/state → state="abc"
   浏览器 (cookie组B) → OAuth 回调 → /api/oauth/linuxdo?state=abc
   服务器在 cookie组B 的 session 中找到 state → 匹配 → 成功
```

---

### 2.2 AgentRouter (`agentrouter.org`)

#### 网站架构

AgentRouter 与 AnyRouter 是姊妹站，API 结构完全一致，但**没有 WAF 保护**。

```
后端 API:       agentrouter.org/api/user/self     → 用户信息
                agentrouter.org/api/user/sign_in  → 签到
                agentrouter.org/api/oauth/state   → OAuth state
                agentrouter.org/api/oauth/linuxdo → OAuth code 交换
```

#### 拦截方式：无 WAF，仅 Session 验证

**实际抓包 - 直接请求（无 WAF）**：
```http
GET https://agentrouter.org/api/user/self HTTP/1.1
Cookie: session=MTc3MDk2MjA5OH...
new-api-user: 34874

--- 响应 ---
HTTP/1.1 200 OK
Content-Type: application/json

{"success":true,"data":{"username":"ZHnagsan",...}}
```

不需要任何 WAF cookie，只要有有效的 `session` cookie 就能直接调用所有 API。

#### 我们的处理方式

- 签到：直接 `httpx.get()` + `session` cookie，零额外操作
- Session 刷新：浏览器完成 OAuth 后，SPA 直接调用 API 交换 code，session cookie 自动设置
- 没有 WAF 的干扰，AgentRouter 的自动化最为简单

---

### 2.3 LinuxDO (`linux.do`)

#### 网站架构

LinuxDO 是一个 Discourse 论坛，也是 AnyRouter/AgentRouter 的唯一登录入口（LinuxDO OAuth）。

```
关键端点:
  linux.do/login            → 登录页面
  linux.do/session/csrf     → 获取 CSRF token（JSON API）
  linux.do/session          → POST 登录（需要 CSRF token）
  linux.do/session/sso_provider?sig=... → OAuth SSO 中转
```

#### 拦截方式 1：Cloudflare Turnstile（浏览器指纹检测）

LinuxDO 使用 Cloudflare Turnstile 验证访问者身份。

**httpx 直接请求（被拦截）**：
```http
GET https://linux.do/ HTTP/1.1
User-Agent: Mozilla/5.0

--- 响应 ---
HTTP/1.1 403 Forbidden
（或返回 Cloudflare 挑战页面 HTML）
```

**Playwright 内置 Chromium（被拦截）**：
```
页面标题: "请稍候…" / "Just a moment..."
原因: navigator.webdriver === true → Cloudflare 识别为自动化浏览器
结果: 挑战永远无法通过
```

**真实 Chrome 浏览器（通过）**：
```
页面标题: "请稍候…" → (2-5秒后) → "LINUX DO - 新的理想型社区"
原因: 真实 Chrome 的浏览器指纹完整，Cloudflare 自动放行
```

**Cloudflare 检测了什么？**
- `navigator.webdriver` 属性（自动化标记）
- WebGL 渲染器指纹
- Canvas 指纹
- Chrome CDP 连接的方式（通过 CDP 连接真实 Chrome 不会暴露自动化标记）

#### 拦截方式 2：Cloudflare 对 AJAX 的特殊限制（最难发现的机制）

即使通过了 Cloudflare 的页面级验证，对 `/session/` 路径的 AJAX 请求还有额外限制。

**实际调试日志（4 种场景对比）**：

```
场景 A: 在 linux.do 页面上直接 fetch
─────────────────────────────────────────
page.evaluate("fetch('/session/csrf')")
  [NET] GET https://linux.do/session/csrf -> 403  ← 被拦截！

场景 B: 先页面导航到 /session/csrf
─────────────────────────────────────────
page.goto('https://linux.do/session/csrf')
  [NET] GET https://linux.do/session/csrf -> 200  ← 页面导航通过

场景 C: 页面导航后，第一次 AJAX
─────────────────────────────────────────
page.goto('https://linux.do/session/csrf')  // 先建立信任
page.goto('https://linux.do/login')
page.evaluate("fetch('/session/csrf')")
  [NET] GET https://linux.do/session/csrf -> 200  ← 第一次 AJAX 通过！

场景 D: 第一次 AJAX 之后，第二次 AJAX
─────────────────────────────────────────
（接场景 C）
page.evaluate("fetch('/session/csrf')")
  [NET] GET https://linux.do/session/csrf -> 403  ← 第二次就不行了！
```

**结论**：Cloudflare 对 `/session/` 路径实施了一种"一次性 AJAX 信任"机制：
1. 页面导航（非 AJAX）到 `/session/` 路径会建立信任
2. 这个信任只能让**后续一次** AJAX 请求通过
3. 用完即失效，后续 AJAX 再次被拦截

#### 拦截方式 3：Discourse CSRF 保护

Discourse 论坛的登录需要 CSRF token：

```http
--- 步骤 1: 获取 CSRF ---
GET https://linux.do/session/csrf HTTP/1.1
X-Requested-With: XMLHttpRequest
Accept: application/json

响应: {"csrf": "a1b2c3d4e5f6..."}

--- 步骤 2: POST 登录 ---
POST https://linux.do/session HTTP/1.1
X-CSRF-Token: a1b2c3d4e5f6...
Content-Type: application/x-www-form-urlencoded

login=email@qq.com&password=xxx&second_factor_method=1

响应 (成功): HTTP 200 {"user": {"username": "xxx"}}
响应 (失败): HTTP 403 / 422
```

#### 我们的绕过方案（三步组合拳）

```
Step 1: 真实 Chrome + CDP
  解决: Cloudflare Turnstile 浏览器指纹检测
  方法: subprocess 启动真实 Chrome (--remote-debugging-port=9222)
        Playwright 通过 CDP 连接，不触发自动化标记

Step 2: 页面导航建立 CF 信任
  解决: Cloudflare 对 /session/ 的 AJAX 限制
  方法: page.goto('https://linux.do/session/csrf')
        这次页面导航建立了一次性 AJAX 信任额度

Step 3: 单次 evaluate 完成登录
  解决: 信任只够一次 AJAX + CSRF 保护
  方法: 在一个 page.evaluate() 中同时完成:
        - fetch('/session/csrf') → 获取 CSRF token（消耗信任额度）
        - fetch('/session', {method: 'POST', ...}) → 用 CSRF token 登录
        两个 fetch 在同一个 evaluate 上下文中，不会被重复拦截
```

**为什么登录按钮表单填写方式不行？**

Discourse 的登录按钮点击后，内部会自动调用 `fetch('/session/csrf')` 获取 CSRF token。但这次 AJAX 被 Cloudflare 拦截（403），导致按钮永远显示"正在登录..."。用 API 方式可以完全控制请求流程。

---

### 2.4 LinuxDO Connect (`connect.linux.do`)

#### 网站架构

LinuxDO Connect 是 OAuth 授权中心，用于第三方应用（AnyRouter/AgentRouter）通过 LinuxDO 账号登录。

```
关键端点:
  connect.linux.do/oauth2/authorize?client_id=...&redirect_uri=...&state=...
    → 显示授权页面（"允许"/"拒绝"按钮）
    → 点击"允许"后重定向到 redirect_uri?code=xxx&state=xxx
```

#### 拦截方式 1：Cloudflare

与 LinuxDO 类似，connect.linux.do 也有 Cloudflare 保护，有时加载需要 10-60 秒。

#### 拦截方式 2：DOM 结构的意外

**"允许"按钮不是 `<button>`，而是 `<a>` 标签！**

实际 DOM：
```html
<!-- 授权页面的可点击元素 -->
<a href="/oauth2/authorize?..." class="...">允许</a>
<a href="/oauth2/authorize?..." class="...">拒绝</a>
```

**导致的问题**：
```python
# ❌ 这些选择器全部无法匹配:
page.locator('button:has-text("允许")')      # 匹配 <button>，但实际是 <a>
page.locator('input[type="submit"]')          # 匹配 <input>，但实际是 <a>
page.locator('.btn-primary')                  # class 名不对

# ✅ 唯一有效的选择器:
page.locator('text=允许')                     # 文本匹配，不限标签类型
```

#### 拦截方式 3：OAuth Client ID 区分

每个平台有独立的 OAuth Client ID，写错会导致回调重定向到错误的平台：

```
AnyRouter  的 Client ID: 8w2uZtoWH9AUXrZr1qeCEEmvXLafea3c
AgentRouter 的 Client ID: KZUecGfhhDZMVnv8UtEdhOhf9sNOhqVX

❌ 用 AgentRouter 的 Client ID 去刷新 AnyRouter 的 session:
   authorize?client_id=KZUecGfhhDZMVnv8UtEdhOhf9sNOhqVX&redirect_uri=anyrouter.top/...
   → 授权后重定向到 agentrouter.org（错误的域名！）

✅ 用正确的 Client ID:
   authorize?client_id=8w2uZtoWH9AUXrZr1qeCEEmvXLafea3c&redirect_uri=anyrouter.top/...
   → 授权后重定向到 anyrouter.top（正确）
```

Client ID 可以通过各平台的 `/api/status` 接口查到。

#### 我们的绕过方案

```
1. 等待 Cloudflare 通过（真实 Chrome 自动处理）
2. 用 text=允许 选择器定位按钮（兼容 <a>/<button>/<input>）
3. 使用平台特定的 OAuth Client ID
4. 统一处理循环：每 2 秒检查一次页面状态
   - 如果在 CF 挑战页 → 继续等待
   - 如果在授权页 → 点击"允许"
   - 如果已重定向到目标平台 → 检查 session cookie
```

---

## 三、破解方案详解

### 3.1 WAF 破解 - solve_waf.js

**原理**：在 Node.js 中模拟浏览器环境执行 WAF 脚本

```javascript
// 1. 构造假的 document 对象
const document = {
  set cookie(val) {
    // 拦截 cookie 设置，提取 acw_sc__v2 的值
    // 立即输出并退出，避免执行后续的反调试代码
    process.exit(0);
  },
  location: {
    reload() { /* 拦截 reload，不执行真正的页面刷新 */ }
  }
};

// 2. 用 eval 执行 WAF 挑战脚本
eval(scriptContent);

// 3. 输出 JSON 格式的 cookie
// {"acw_sc__v2": "computed_value"}
```

**关键技巧**：
- WAF 脚本设置 cookie 后会调用 `reload()`，之后有 `debugger` 死循环
- 在 cookie setter 中立即调用 `process.exit(0)` 跳过所有后续代码
- 5秒超时保护，防止意外卡死

**使用方式**：
```bash
# 自动流程（auto_checkin.py 内部调用）:
# 1. httpx 请求获取 WAF 挑战页面 HTML
# 2. 提取 <script> 标签内容
# 3. 写入临时 .js 文件
# 4. node solve_waf.js 临时文件路径
# 5. 读取 stdout 的 JSON 输出
```

### 3.2 Cloudflare 绕过 - 真实 Chrome + CDP

**为什么 Playwright 内置浏览器不行？**
- Playwright 的 Chromium 有自动化标记（`navigator.webdriver = true`）
- Cloudflare Turnstile 能检测到这些标记并拒绝通过

**为什么真实 Chrome 可以？**
- 真实 Chrome 没有自动化标记
- 通过 CDP (Chrome DevTools Protocol) 远程控制，Cloudflare 无法区分是人还是自动化

**启动方式**：
```python
# 1. 启动 Chrome，使用临时 profile（避免锁冲突）
proc = subprocess.Popen([
    chrome_exe,
    '--remote-debugging-port=9222',     # CDP 端口
    '--user-data-dir=临时目录',           # 必须用临时目录！
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
])

# 2. Playwright 通过 CDP 连接
browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
```

**为什么必须用临时 profile？**
- 真实 Chrome profile 目录会被已运行的 Chrome 锁定
- 锁定状态下 CDP 无法正常工作（等待超时）
- 临时目录没有锁冲突，CDP 秒连

### 3.3 LinuxDO 登录 - CSRF 信任建立 + 单次 AJAX

**完整登录流程（3步）**：

```
Step A: 建立 CF 信任
    页面导航到 https://linux.do/session/csrf
    → Cloudflare 自动放行（真实 Chrome）
    → 建立了一次 AJAX 信任额度

Step B: 导航到登录页
    页面导航到 https://linux.do/login
    → 等待 Cloudflare 通过
    → Discourse SPA 加载完成

Step C: 单次 AJAX 完成登录（关键！）
    在 page.evaluate 中执行：

    // 第一个 fetch: 消耗 CF 信任额度获取 CSRF token
    const csrfResp = await fetch('/session/csrf', {...});
    const csrf = csrfData.csrf;

    // 第二个 fetch: 立即使用 CSRF token 登录
    // 注意：这不算"新的 AJAX"，因为和第一个在同一个 evaluate 上下文中
    const loginResp = await fetch('/session', {
        method: 'POST',
        headers: { 'X-CSRF-Token': csrf, ... },
        body: 'login=...&password=...'
    });
```

**为什么必须在一个 evaluate 中完成？**
- CF 信任只允许一次 AJAX 到 `/session/` 路径
- 如果分两次 evaluate，第二次 AJAX 会被 CF 拦截 (403)
- 在同一个 evaluate 中连续 fetch 不会被 CF 拦截

### 3.4 OAuth 全浏览器流程

这是最终的可靠方案，核心思想是**所有操作都在浏览器中完成**：

```
1. 浏览器访问 anyrouter.top/
   → WAF 自动执行 JS 挑战
   → 获得 acw_tc + cdn_sec_tc + acw_sc__v2
   → 浏览器 cookies 中保存了完整的 WAF session

2. 浏览器内 fetch('/api/oauth/state')
   → 使用浏览器自己的 cookies（包含 WAF cookies）
   → state 绑定在浏览器的 WAF session 上
   → 这样后续 OAuth 回调时 state 能匹配！

3. 浏览器导航到 OAuth URL
   → connect.linux.do 授权页面
   → Cloudflare 通过后显示"允许"按钮

4. 自动点击"允许"（text=允许 选择器）
   → 重定向回 anyrouter.top/oauth/linuxdo?code=xxx&state=xxx

5. SPA 前端自动执行
   → fetch('/api/oauth/linuxdo?code=xxx&state=xxx')
   → 因为浏览器的 WAF cookies 和获取 state 时一致
   → API 验证 state 匹配 → 成功
   → 设置 session cookie
```

---

## 四、脚本使用指南

### 4.1 auto_refresh_chrome.py - Session 自动刷新

**用途**：当 AnyRouter/AgentRouter session 过期时，自动通过 LinuxDO OAuth 获取新 session

**前提条件**：
- Windows 系统 + Google Chrome 浏览器
- Node.js（用于 WAF 解析）
- Python 依赖：`httpx`, `playwright`
- `update_sessions.json` 配置文件

**运行**：
```bash
python auto_refresh_chrome.py
```

**配置**：编辑脚本中的 `LINUXDO_CREDENTIALS` 字典：
```python
LINUXDO_CREDENTIALS = {
    '你的邮箱@qq.com': {
        'login': '你的邮箱@qq.com',
        'password': '你的密码'
    },
    # 支持多个 LinuxDO 账号
    '另一个邮箱@gmail.com': {
        'login': '另一个邮箱@gmail.com',
        'password': '另一个密码'
    },
}
```

**匹配规则**：脚本通过账号名称中是否包含邮箱来匹配凭据。例如：
- 账号名 `linuxdo_87247_ZHnagsan_2621097668@qq.com_AnyRouter` 包含 `2621097668@qq.com`
- 自动匹配到 `LINUXDO_CREDENTIALS['2621097668@qq.com']`

**工作流程**：
```
1. 读取 update_sessions.json
2. 逐个检查账号 session 是否有效
3. 将过期账号按 LinuxDO 凭据分组
4. 每组只启动一个 Chrome 实例，只登录一次
5. 在同一个浏览器会话中为该组所有账号刷新 session
6. 每个 session 获取后立即保存到文件
```

### 4.2 auto_checkin.py - 每日自动签到

**用途**：携带有效 session 执行每日签到（本地使用，同步 httpx + Node.js WAF）

**运行**：
```bash
python auto_checkin.py
```

**配置来源**（按优先级）：
1. 环境变量 `ANYROUTER_ACCOUNTS`（JSON 字符串）
2. 文件 `accounts.json`
3. 文件 `update_sessions.json`
4. 文件 `test_config.json`

> 为什么有 4 个备选文件：`accounts.json` 是标准配置，`update_sessions.json` 是 auto_refresh_chrome.py 刷新后的输出，`test_config.json` 是开发测试用。环境变量优先级最高，用于 CI 环境。

**WAF 处理方式**：使用 httpx 获取挑战页面 + Node.js 解析（不依赖浏览器）

```
1. httpx.get(domain) → 获取 acw_tc + cdn_sec_tc（Set-Cookie 自动获取）
                      → 获取 HTML 中的 <script> 内容
2. 从 HTML 中提取 WAF 挑战脚本（检测标志：'<script>' + 'arg1=' 存在）
   arg1 是阿里云 WAF 挑战脚本的固定特征变量名
3. subprocess 调用 node solve_waf.js（Python 侧 timeout=10s，JS 侧 timeout=5s）
4. 解析输出 JSON 获取 acw_sc__v2
```

> 与 checkin.py 的 WAF 处理不同：auto_checkin.py 用 Node.js 执行 WAF 脚本，不需要启动浏览器。详见 [4.6 脚本架构对比](#46-脚本架构对比)。

**二次 WAF 挑战处理**（关键机制，文档之前缺失）：

第一次 WAF 通过后，API 请求有时仍返回 WAF 挑战页面（而非 JSON）。auto_checkin.py 有重试机制：

```python
# 第一次请求 /api/user/self
resp = client.get(f'{domain}/api/user/self', ...)
if '<script>' in resp.text and 'arg1=' in resp.text:
    # API 响应是 WAF 挑战页面而非 JSON！
    # 重新提取脚本 → 重新调用 solve_waf_challenge() → 更新 cookies
    # 用新 cookies 重试请求
    resp = client.get(f'{domain}/api/user/self', ...)
```

> 为什么会出现二次挑战：阿里云 WAF 有时对不同路径（/ 和 /api/user/self）分别验证。第一次解析的 acw_sc__v2 可能只对首页有效，API 路径需要重新计算。

**工作流程**：
```
对每个账号:
    1. [AnyRouter] 获取 WAF cookies (solve_waf.js)
    2. 携带 session + WAF cookies 调用 /api/user/self 获取用户信息
    3. 如果遇到二次 WAF 挑战（响应是 HTML 且包含 arg1=），重新解析
    4. 调用 /api/user/sign_in 执行签到
    5. [AgentRouter] 直接用 session 调用 API（无需 WAF）
```

**超时配置**：
- WAF 请求：`timeout=15.0`（WAF 可能需要额外的服务端处理时间）
- API 请求：`timeout=30.0`（包含可能的二次 WAF 重试时间）
- Node.js 子进程：`timeout=10`（Python 侧），solve_waf.js 内部 `setTimeout(5000)`（JS 侧双层保护）

**注意：agentrouter 签到路径不一致**：auto_checkin.py 中 agentrouter 显式设置了 `sign_in_path='/api/user/sign_in'`，但 utils/config.py 中 agentrouter 的 `sign_in_path=None`（表示查询 /api/user/self 即自动签到）。实际行为取决于使用哪个脚本 -- auto_checkin.py 会显式调用签到接口，checkin.py 对 agentrouter 不调用签到接口。

### 4.3 solve_waf.js - WAF Cookie 求解器

**用途**：解析 AnyRouter 的阿里云 WAF 挑战脚本，输出 `acw_sc__v2` cookie

**单独测试**：
```bash
# 手动使用（通常不需要，脚本会自动调用）
node solve_waf.js 挑战脚本文件.js
# 输出: {"acw_sc__v2":"计算出的值"}
```

### 4.4 checkin.py - GitHub Actions 签到脚本

**用途**：设计用于 GitHub Actions 云端运行的签到脚本，是功能最完整的版本

**与 auto_checkin.py 的核心区别**：

| 维度 | checkin.py (CI 版) | auto_checkin.py (本地版) |
|------|-------------------|----------------------|
| WAF 绕过 | Playwright 内置 Chromium（`launch_persistent_context`） | httpx + Node.js solve_waf.js |
| 异步模型 | async/await | 同步 |
| 配置来源 | 环境变量 `ANYROUTER_ACCOUNTS` | 文件（accounts.json 等） |
| 通知功能 | 余额监控 + 多渠道通知 | 无 |
| 二次 WAF | 无（Playwright 自动处理） | 有（检测 HTML + 重新解析） |
| HTTP 版本 | HTTP/2（`http2=True`） | HTTP/1.1 |
| SSL 验证 | 禁用（`verify=False`） | 启用 |
| 依赖 | Playwright + Chromium | Node.js |

**WAF 绕过方式详解**：

```python
# checkin.py 用 Playwright 内置 Chromium 的 launch_persistent_context
# 不是 connect_over_cdp（不需要真实 Chrome）
browser = await playwright.chromium.launch_persistent_context(
    user_data_dir=tempdir,
    headless=True,  # CI 环境无头运行，可通过 HEADLESS 环境变量控制
    args=[
        '--disable-blink-features=AutomationControlled',  # 隐藏自动化标记
        '--disable-web-security',   # 禁用 CORS（WAF 需要）
        '--no-sandbox',             # CI 容器环境需要
        # ... 更多反检测参数
    ],
    viewport={'width': 1920, 'height': 1080},  # 模拟真实分辨率
)
```

> 为什么这里用 Playwright Chromium 而不是真实 Chrome？
> - GitHub Actions 环境没有真实 Chrome
> - 但只需要获取 WAF cookies（不需要通过 LinuxDO 的 Cloudflare Turnstile）
> - Playwright Chromium + 反检测参数足以通过阿里云 WAF
> - 而 auto_refresh_chrome.py 需要通过 LinuxDO Turnstile，所以必须用真实 Chrome

WAF cookie 完整性校验：
```python
# checkin.py 要求三个 cookie 全部存在才算通过
required = {'acw_tc', 'cdn_sec_tc', 'acw_sc__v2'}
if not required.issubset(cookies.keys()):
    # 校验失败 → 等待 3 秒后重试

# 而 auto_checkin.py 的容错更宽松：
# "不一定需要全部，继续尝试"
```

**余额哈希通知机制**（checkin.py 独有功能）：

```python
# 1. 生成当前余额的哈希指纹
def generate_balance_hash(accounts_data):
    # 对所有账号的余额排序后 SHA256，截断 16 字符
    # 截断到 16 字符是因为只需要检测变化，不需要密码学强度
    return hashlib.sha256(json.dumps(sorted_balances).encode()).hexdigest()[:16]

# 2. 从 balance_hash.txt 读取上次的哈希
old_hash = load_balance_hash()

# 3. 对比决定是否发送通知
new_hash = generate_balance_hash(results)
if old_hash != new_hash:  # 余额发生变化
    send_notification("余额变化", details)
    save_balance_hash(new_hash)
```

通知触发策略：
1. 签到失败 → 立即通知
2. 余额发生变化（哈希不匹配）→ 通知
3. 首次运行（无历史哈希）→ 强制通知
4. 全部成功且余额无变化 → 不通知（避免每天重复消息）

**多格式响应解析**：

```python
# checkin.py 兼容多种签到 API 返回格式
if result.get('ret') == 1:       # 旧版 API 格式
    success = True
elif result.get('code') == 0:    # 另一种旧版格式
    success = True
elif result.get('success'):      # new-api 标准格式
    success = True

# 非 JSON 响应也尝试文本匹配
if 'success' in response_text:
    success = True
```

> `ret` 和 `code` 是早期版本 API 的遗留格式，当前 new-api 框架统一使用 `success` 字段。

**额度换算**：

```python
quota_display = quota / 500000  # 显示为美元
```

> `500000` 是 new-api 框架的内部单位换算系数。new-api 中 1 美元 = 500,000 quota 单位。例如 `quota=7280991` 表示约 $14.56。auto_checkin.py 中同样使用此系数。

**环境变量**：
- `ANYROUTER_ACCOUNTS`: JSON 数组，账号配置
- `HEADLESS`: 是否无头模式（默认 `true`，调试时设为 `false`）
- `ENCRYPTION_KEY`: Fernet 加密密钥
- 通知相关：`SERVERPUSHKEY`、`PUSHPLUS_TOKEN`、`EMAIL_*` 等

### 4.5 probe_sites.py - 批量站点探测

**用途**：批量检测站点是否为 new-api 框架、是否支持签到、是否有 LinuxDO OAuth

**运行**：
```bash
python probe_sites.py
```

**探测逻辑**：

```
对每个站点域名:
    1. GET {domain}/api/status (timeout=10s, follow_redirects=True)
    2. 如果 HTTP 200 且响应是 JSON:
       - 检查 data.success == True → 判定为 new-api
       - 提取字段:
         - system_name: 站点自定义名称
         - version: new-api 版本号
         - linuxdo_oauth: 是否支持 LinuxDO OAuth
         - linuxdo_client_id: OAuth Client ID（添加配置的关键数据）
         - checkin_enabled: 是否开启签到功能
         - turnstile_check: 是否有 Turnstile 人机验证
         - linuxdo_minimum_trust_level: 最低信任等级要求
    3. 如果非 JSON 或状态码异常 → 判定为非 new-api 或死亡
```

**分类规则**：
- **A 类**：`is_newapi=True` 且 `checkin_enabled=True` 或 `checkin_enabled=None` → 可能有签到
  - `None` 保守归入"可能有签到"，因为旧版本 new-api 可能不返回此字段
- **B 类**：`is_newapi=True` 且 `checkin_enabled=False` → 明确无签到
- **C 类**：`alive=True` 但 `is_newapi=False` → WAF 拦截或非 new-api 框架
- **D 类**：`alive=False` → 无法访问

**输出**：
- 终端打印分类汇总
- `site_probe_results.json`：完整探测结果（67 个站点的详细数据）

**使用场景**：
```
工作流: probe_sites.py 探测 → 从 A 类中筛选 → 添加到 multi_site_checkin.py SITES 字典
                              ↓
                    site_probe_results.json → SITE_REGISTRY.md 的数据来源
```

**局限性**：
- 仅检查 `/api/status`，部分站点该路径不存在但站点活着（如 Sub2API 框架）
- httpx 无法绕过 Cloudflare/WAF，被拦截的站点会被误判为"非 new-api"
- `checkin_enabled=None` 不代表无签到，旧版 new-api 可能不返回此字段

### 4.6 脚本架构对比

系统有 4 个签到相关脚本，各有不同的设计目标和技术选型：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        脚本架构全景图                                  │
│                                                                     │
│  ┌─────────────────┐   ┌───────────────────┐   ┌────────────────┐  │
│  │  auto_checkin.py │   │    checkin.py      │   │ multi_site_    │  │
│  │  (本地签到)       │   │  (GitHub Actions)  │   │ checkin.py     │  │
│  ├─────────────────┤   ├───────────────────┤   ├────────────────┤  │
│  │ httpx (同步)     │   │ httpx (async)     │   │ Playwright     │  │
│  │ + Node.js WAF   │   │ + Playwright WAF  │   │ + 真实 Chrome   │  │
│  │                 │   │ + 通知 + 余额监控   │   │ + OAuth 全流程  │  │
│  ├─────────────────┤   ├───────────────────┤   ├────────────────┤  │
│  │ AnyRouter       │   │ AnyRouter         │   │ 7+ new-api 站  │  │
│  │ AgentRouter     │   │ AgentRouter       │   │ 5 LinuxDO 账号  │  │
│  └────────┬────────┘   └────────┬──────────┘   └───────┬────────┘  │
│           │                     │                      │           │
│           ▼                     ▼                      ▼           │
│  update_sessions.json    环境变量              checkin_results.json  │
│                                                                     │
│  ┌─────────────────────┐                                           │
│  │auto_refresh_chrome.py│  Session 过期时调用                        │
│  │  (Session 刷新)      │  真实 Chrome + CDP + OAuth                │
│  └─────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────┘
```

**关键技术决策对比**：

| 决策 | auto_checkin.py | checkin.py | multi_site_checkin.py | auto_refresh_chrome.py |
|------|----------------|------------|----------------------|----------------------|
| **浏览器** | 不需要 | Playwright Chromium | 真实 Chrome + CDP | 真实 Chrome + CDP |
| **为什么** | 已有 session，只需 WAF | CI 环境无真实 Chrome，WAF 不需要 Turnstile | 需要通过 LinuxDO Turnstile | 同左 |
| **WAF 方式** | Node.js eval | 浏览器自动执行 | 浏览器自动执行 | 浏览器自动执行 |
| **异步** | 同步 httpx | async（配合 Playwright） | async（配合 Playwright） | async |
| **登录** | 不登录（已有 session） | 不登录（已有 session） | 浏览器内 API 登录 | 浏览器内 API 登录 |
| **签到** | httpx API 调用 | httpx API 调用 | 浏览器内 fetch | 不签到（只刷新 session） |

**为什么需要真实 Chrome 而非 Playwright Chromium？**

```
LinuxDO Cloudflare Turnstile 检测:
  Playwright Chromium → navigator.webdriver === true → 拦截
  真实 Chrome + CDP   → navigator.webdriver === false → 通过

阿里云 WAF 检测:
  Playwright Chromium + 反检测参数 → 能通过（只需执行 JS 计算 cookie）
  httpx + Node.js                  → 能通过（直接 eval WAF 脚本）
```

因此：
- 需要通过 LinuxDO → 必须用真实 Chrome（multi_site_checkin.py、auto_refresh_chrome.py）
- 只需要 WAF cookies → Playwright Chromium 或 Node.js 都行（checkin.py、auto_checkin.py）

**URL 编码方式不一致**：
- auto_refresh_chrome.py: `redirect_uri.replace(':', '%3A').replace('/', '%2F')` — 手动编码
- multi_site_checkin.py: `urllib.parse.quote(redirect_uri, safe='')` — 标准库

两种方式功能等价，后者更规范。历史原因导致不一致，不影响功能。

---

## 五、完整工作流程

### 5.1 日常签到流程

```bash
# 1. 检查 session 是否有效 + 签到
python auto_checkin.py

# 如果提示 session 过期:
# 2. 自动刷新 session
python auto_refresh_chrome.py

# 3. 再次签到
python auto_checkin.py
```

### 5.2 一键自动化（推荐）

可以将两个脚本串联：
```bash
# 先刷新过期 session，再签到
python auto_refresh_chrome.py && python auto_checkin.py
```

### 5.3 OAuth 各平台参数

#### AnyRouter / AgentRouter

| 参数 | AnyRouter | AgentRouter |
|------|-----------|-------------|
| 域名 | `anyrouter.top` | `agentrouter.org` |
| OAuth Client ID | `8w2uZtoWH9AUXrZr1qeCEEmvXLafea3c` | `KZUecGfhhDZMVnv8UtEdhOhf9sNOhqVX` |
| 回调地址 | `anyrouter.top/oauth/linuxdo` | `agentrouter.org/oauth/linuxdo` |
| 需要 WAF | 是 | 否 |
| 签到接口 | `/api/user/sign_in` | `/api/user/sign_in` |
| State API | `/api/oauth/state` | `/api/oauth/state` |
| 用户信息 | `/api/user/self` | `/api/user/self` |

#### new-api 公益站

| 参数 | Einzieg | 摸鱼公益 | 老魔公益站 | WoW公益站 | Elysiver | WONG | 余额比寿命长 |
|------|---------|---------|-----------|----------|----------|------|----------|
| 域名 | `api.einzieg.site` | `clove.cc.cd` | `api.2020111.xyz` | `linuxdoapi.223384.xyz` | `elysiver.h-e.top` | `wzw.pp.ua` | `new.123nhh.xyz` |
| Client ID | `aBamb...RATf` | `Lr8C2...eL7` | `gnyvf...Vmmm` | `3fcFo...TwN` | 运行时获取 | `451Qx...yTQF` | `m17Y3...HXcy` |
| WAF | 无 | 无 | 无 | 无 | 阿里云 WAF | 无 | 无 |
| 签到接口 | `/api/user/checkin` | 同左 | 同左 | 同左 | 同左 | 同左 | 同左 |
| 认证方式 | session + New-Api-User 头部 | 同左 | 同左 | 同左 | 同左 | 同左 | 同左 |
| 特殊说明 | CF 不稳定 | - | - | - | WAF 严格 | 返回格式不同 | /api/status 慢 |

---

## 六、多站点签到系统

### 6.1 new-api 框架说明

当前已配置 26 个活跃公益站 + 7 个跳过站点，均基于 **new-api** 开源框架：

- 后端：Go（Gin 框架）
- 前端：React SPA
- 认证：LinuxDO OAuth + session cookie
- 签到：`POST /api/user/checkin`

> 完整站点列表见 SITE_REGISTRY.md 第四节。

### 6.2 认证机制详解

new-api 的 `authHelper()` 中间件（`middleware/auth.go`）要求请求同时满足：

1. **有效的 session cookie** - 通过 OAuth 登录后获得
2. **New-Api-User 请求头** - 值为用户 ID（整数）

```
❌ 只有 session cookie，没有 New-Api-User 头部:
POST /api/user/checkin
Cookie: session=MTc3MDk3OTg2Nn...
→ 401 "无权进行此操作，未提供 New-Api-User"

❌ 有 session 但 New-Api-User 不匹配:
POST /api/user/checkin
Cookie: session=MTc3MDk3OTg2Nn...
New-Api-User: 99999
→ 401 "无权进行此操作"

✅ session + 正确的 New-Api-User:
POST /api/user/checkin
Cookie: session=MTc3MDk3OTg2Nn...
New-Api-User: 360
→ 200 {"success": true, "message": "签到成功", "data": {"quota_awarded": 1028987}}
```

**替代方案**：也可使用 `Authorization: Bearer <access_token>` 头部替代 session + New-Api-User 组合。access_token 在 OAuth 回调响应中返回。

### 6.3 用户 ID 获取方式

OAuth 登录后，用户 ID 的获取有两种途径：

**方式 1：拦截 OAuth 回调响应（优先）**
```
浏览器监听 response 事件
→ 匹配 URL 包含 /api/oauth/ 且属于目标域名
→ 响应 body: {"success": true, "data": "eyJhbGciOiJ..."}
→ data 字段即为 access_token
```

**方式 2：从 localStorage 提取（备用）**
```
导航到 {domain}/console → 等待 React SPA 加载完成
→ 检查 localStorage 中的 key: user, userInfo, currentUser, user_info
→ 解析 JSON，提取 id 字段
→ 备用：遍历所有 localStorage key，查找包含 id + username 的对象
```

### 6.4 站点配置

当前 26 个活跃站点 + 7 个跳过站点，完整列表见 SITE_REGISTRY.md 第四节。

> Elysiver 的 client_id 不在代码中硬编码，通过浏览器访问 `/api/status` 接口在运行时获取。

### 6.5 LinuxDO 账号

multi_site_checkin.py 使用 4 个 LinuxDO 账号（并行执行）：

| 标签 | 邮箱 | 说明 |
|------|------|------|
| ZHnagsan | `2621097668@qq.com` | 主号，24/26 站点成功 |
| caijijiji | `dw2621097668@gmail.com` | 23/26 站点成功 |
| CaiWai | `daixiaowei985@gmail.com` | 22/26 站点成功 |
| heshangd | `2330702014@st.btbu.edu.cn` | 22/26 站点成功 |

> kefuka（`xiaoweidai998@163.com`）已封禁，已从脚本移除。

### 6.6 multi_site_checkin.py 工作流程

```
main():
  1. 杀死现有 Chrome 进程
  2. 对 4 个账号并行执行 (asyncio.gather, 端口 9222-9225):

process_account(account, debug_port):
  === Phase 1: httpx 缓存快速签到 ===
  3. 加载 sessions_cache.json 中该账号的缓存 session
  4. 对每个有缓存的站点:
     a. httpx 直接 POST /api/user/checkin（携带 session cookie + New-Api-User/Authorization）
     b. 检测过期：3xx 重定向 / 401 / HTML 响应 → 删除缓存
     c. POST 404 → 自动降级为 GET 重试
     d. 成功/已签到 → 记录结果，标记为已处理
  5. 统计：缓存命中 N 个，剩余 M 个需要浏览器

  === Phase 2: 浏览器 OAuth（仅处理剩余站点）===
  6. 启动 Chrome 实例（临时 profile + CDP debug_port）
  7. Playwright 通过 CDP 连接

  8. 登录 LinuxDO:
     a. 页面导航到 /session/csrf（建立 CF 信任）
     b. 导航到 /login，等待 CF 通过
     c. 单次 page.evaluate 完成 CSRF 获取 + POST 登录

  9. 对每个剩余站点:
     a. [Elysiver] 若无 client_id → 浏览器访问首页 → fetch /api/status → 获取 client_id
     b. 浏览器访问站点首页（建立 WAF session）
     c. 浏览器内 fetch /api/oauth/state → 获取 state
     d. 记录现有 session cookie 值（pre_oauth_sessions）
     e. 注册 response 监听器（捕获 access_token）
     f. 导航到 OAuth 授权 URL
     g. 等待 CF → 点击"允许" → 等待新 session cookie
     h. 对比 pre_oauth_sessions，只接受新产生的 session
     i. 若无 access_token → 导航到 /console → localStorage 提取用户 ID
     j. 携带 New-Api-User 或 Authorization 头部，POST /api/user/checkin
     k. 保存新 session 到 sessions_cache.json（load-merge-save 原子写入）
     l. 记录结果到 checkin_results.json

  10. 关闭 Chrome，清理临时目录
  11. 输出汇总报告
```

**性能对比**：

| 模式 | 耗时 | 说明 |
|------|------|------|
| 优化前（串行 5 账号，无缓存） | 96 分钟 | 每账号 ~20 分钟 |
| 并行 4 账号，无缓存（首次） | 22 分钟 | Phase 2 全量 OAuth |
| 并行 4 账号，有缓存（日常） | 7 分钟 | Phase 1 ~30s + Phase 2 少量 OAuth |
| 缓存全命中 | 1-2 分钟 | 仅 Phase 1 |

### 6.7 关键 Bug 及修复

#### Bug 1：签到 401 "未提供 New-Api-User"

**问题**：OAuth 登录成功获得 session cookie，但签到返回 401。

**根因**：new-api 的 `authHelper()` 要求请求同时携带 session cookie 和 `New-Api-User` 请求头。仅有 session cookie 不够。

**修复**：
- 在 OAuth 回调中拦截 access_token（response 监听器）
- 若无 access_token，从 localStorage 提取用户 ID
- 签到时携带 `Authorization: Bearer <token>` 或 `New-Api-User: <id>` 头部

#### Bug 2：捕获到旧的 state session cookie

**问题**：部分账号（已授权过，无需点击"允许"）OAuth 完成后签到仍返回 401 "未登录"。

**根因**：OAuth state 请求 (`/api/oauth/state`) 本身会在浏览器中设置一个 session cookie。当自动授权（跳过"允许"按钮）时，代码在 [2s] 时检测到这个 state session cookie，误认为是 OAuth 登录后的新 session。实际的 OAuth session 还没生成。

**修复**：在 OAuth 流程开始前，记录所有已存在的 session cookie 值到 `pre_oauth_sessions` 集合。检测 session cookie 时，只接受不在该集合中的新值：
```python
pre_oauth_sessions = set()
for c in await ctx.cookies():
    if c['name'] == 'session' and domain_host in c.get('domain', ''):
        pre_oauth_sessions.add(c['value'])
# ... OAuth 流程 ...
# 只接受新 session:
if c['value'] not in pre_oauth_sessions:
    return c['value'], captured_token[0]
```

#### Bug 3：kefuka 账号已封禁

**问题**：kefuka 账号 LinuxDO 登录返回 200，但后续 OAuth 授权时被重定向到 `linux.do/login`，所有站点 0 成功。

**结论**：用户确认该 LinuxDO 账号已被封禁。已从脚本中注释移除。

#### Bug 4：Einzieg Cloudflare 超时

**问题**：connect.linux.do 重定向到 Einzieg 时，Cloudflare 挑战页面停留超过 90 秒。

**状态**：间歇性问题，非代码 Bug。Einzieg 的 Cloudflare 配置有时对 OAuth 回调 URL 检查严格。部分账号可以通过，部分超时。

#### Bug 5：Session 文件并发写入竞争（已修复）

**问题**：4 账号并行执行时，每个账号各自加载 sessions_cache.json 的副本，保存时互相覆盖。

**修复**：将 `save_sessions(sessions)` 替换为 `save_session_entry(label, site_key, data)` 和 `delete_session_entry(label, site_key)`，每次写入都先 load 最新文件再 merge 再 save。asyncio 单线程模型下，await 点之间不会被打断，因此是原子安全的。

#### Bug 6：CDP 就绪检查阻塞事件循环（已修复）

**问题**：等待 Chrome CDP 就绪时使用同步 `httpx.get()`，阻塞整个 asyncio 事件循环，导致其他并行账号也被卡住。

**修复**：改为 `async with httpx.AsyncClient() as _client: await _client.get(...)`。

#### Bug 7：SecurityError 访问 localStorage（已修复）

**问题**：部分站点（如 Old API）在 `get_user_id_from_page()` 中访问 `localStorage` 时抛出 `SecurityError: Failed to read the 'localStorage' property from 'Window'`（跨域限制）。

**修复**：在 JavaScript evaluate 中添加 try/catch，Python 层也添加 try/except，失败时返回 None 而非崩溃。

### 6.8 最新运行结果（2026-02-14）

| 指标 | 值 |
|------|-----|
| 活跃站点 | 26 个 |
| 账号数 | 4 个（并行） |
| 总耗时（有缓存） | 437s（7.3 分钟） |
| 全部成功 | 21 个站点（4/4 账号） |
| 部分成功 | 4 个站点（CF 不稳定） |
| 全部失败 | 1 个站点（余额比寿命长） |
| 缓存命中 | 91/104 站点通过 httpx 直连完成 |

> 详细的每账号每站点结果见 SITE_REGISTRY.md 第十节。

### 6.9 输出文件

**checkin_results.json** - 每次运行的详细记录：
```json
[
  {
    "account": "ZHnagsan",
    "site": "Einzieg API",
    "site_key": "einzieg",
    "domain": "https://api.einzieg.site",
    "time": "2026-02-13 19:13:38",
    "login_ok": true,
    "checkin_ok": true,
    "session": "MTc3MDk4MDg5OXxEWDhFQVFMX2dBQUJFQUVR...",
    "checkin_msg": "签到成功",
    "quota": 7280991
  }
]
```

---

## 七、问题排查手册

### 7.1 Session 过期

**症状**：签到时提示"未登录"或 session 无效

**解决**：
```bash
python auto_refresh_chrome.py
```

**注意**：只有在 `LINUXDO_CREDENTIALS` 中配置了对应凭据的账号才能自动刷新。

### 7.2 Chrome CDP 连接失败

**症状**：`Chrome CDP 未就绪`

**原因**：已有 Chrome 实例占用了 9222 端口，或使用了真实 profile

**解决**：
```bash
# 关闭所有 Chrome 进程
taskkill /F /IM chrome.exe /T
# 重新运行
python auto_refresh_chrome.py
```

### 7.3 LinuxDO 登录失败

**症状**：`API 结果: {"error": "CSRF 403"}`

**原因**：Cloudflare 对 `/session/` 路径的 AJAX 限制

**脚本已内置解决方案**：
1. 先页面导航到 `/session/csrf` 建立 CF 信任
2. 然后在单次 `page.evaluate` 中完成 CSRF 获取 + 登录

如果仍然失败，可能是 Cloudflare 策略变更，需要：
- 确认 Chrome 是最新版本
- 尝试重新运行（CF 有时有延迟）

### 7.4 OAuth State 不匹配

**症状**：API 返回 `{"message":"state is empty or not same","success":false}`

**原因**：state 是通过 httpx 获取的，与浏览器的 WAF session 不一致

**脚本已内置解决方案**：使用 `get_state_via_browser()` 在浏览器内获取 state

### 7.5 WAF Cookie 解析失败

**症状**：`solve_waf.js` 返回空对象 `{}`

**排查**：
```bash
# 检查 Node.js 是否安装
node --version

# 手动测试 WAF 解析
# 1. 用浏览器访问 anyrouter.top
# 2. F12 查看第一次响应的 HTML
# 3. 复制 <script> 标签内容到文件 test.js
# 4. 运行:
node solve_waf.js test.js
```

### 7.6 "允许"按钮点击失败

**症状**：OAuth 停在 connect.linux.do 页面，没有点击"允许"

**原因/解决方案**：
- "允许"是 `<a>` 标签，必须用 `text=允许` 选择器
- Cloudflare 可能导致页面加载慢，脚本有 180 秒等待
- 如果首次授权，会显示"允许"按钮；已授权过可能自动跳过

### 7.7 无匹配凭据

**症状**：`过期 -> 无匹配凭据，跳过`

**原因**：账号名称中的邮箱在 `LINUXDO_CREDENTIALS` 中没有对应条目

**解决**：在 `auto_refresh_chrome.py` 的 `LINUXDO_CREDENTIALS` 中添加对应凭据：
```python
LINUXDO_CREDENTIALS = {
    '2621097668@qq.com': {'login': '...', 'password': '...'},
    'xiaoweidai998@163.com': {'login': '...', 'password': '...'},
    'dw2621097668@gmail.com': {'login': '...', 'password': '...'},
    # ...
}
```

### 7.8 多站点签到 401 "未提供 New-Api-User"

**症状**：multi_site_checkin.py 登录成功但签到返回 401

**原因**：new-api 需要 session cookie + `New-Api-User` 请求头双重认证

**解决**：脚本已内置修复。如果仍然出现：
1. 检查 localStorage 中是否写入了用户信息（SPA 可能加载失败）
2. 增加 `get_user_id_from_page` 中的等待时间
3. 检查 OAuth 回调响应中是否返回了 access_token

### 7.9 多站点签到捕获到旧 session

**症状**：OAuth 登录返回 session 但签到提示"未登录"

**原因**：捕获到的是 `/api/oauth/state` 接口设置的 session cookie，不是 OAuth 登录后的真正 session

**解决**：脚本已内置 `pre_oauth_sessions` 过滤机制。如果仍然出现，检查 `oauth_login_site` 函数中的 cookie 过滤逻辑。

---

## 八、配置参考

### 8.1 update_sessions.json 格式

```json
[
  {
    "name": "linuxdo_87247_ZHnagsan_2621097668@qq.com_AnyRouter",
    "provider": "anyrouter",
    "cookies": {
      "session": "MTc3MDk2OTIzNn..."
    },
    "api_user": "87247"
  },
  {
    "name": "linuxdo_34874_ZHnagsan_2621097668@qq.com_AgentRouter",
    "provider": "agentrouter",
    "cookies": {
      "session": "MTc3MDk2MjA5OH..."
    },
    "api_user": "34874"
  }
]
```

**字段说明**：
- `name`: 账号显示名称，**必须包含 LinuxDO 邮箱**以便匹配凭据
- `provider`: `anyrouter` 或 `agentrouter`
- `cookies.session`: session token（base64 编码，约 30 天有效期）
- `api_user`: 平台用户 ID

### 8.2 checkin_results.json 格式

由 `multi_site_checkin.py` 生成，记录每次运行的详细结果：

```json
[
  {
    "account": "ZHnagsan",
    "site": "摸鱼公益",
    "site_key": "moyu",
    "domain": "https://clove.cc.cd",
    "time": "2026-02-13 19:13:38",
    "login_ok": true,
    "checkin_ok": true,
    "session": "MTc3MDk4...",
    "checkin_msg": "签到成功",
    "quota": 1028987
  }
]
```

**字段说明**：
- `account`: LinuxDO 账号标签
- `site` / `site_key`: 站点名称 / 配置 key
- `login_ok`: OAuth 登录是否成功
- `checkin_ok`: 签到是否成功
- `quota`: 签到获得的额度
- `error`: 如果失败，错误信息

### 8.3 环境依赖

```
Python 3.10+
  - httpx
  - playwright

Node.js 16+
  - 无需额外包

Google Chrome (Windows)
  - 默认路径: C:\Program Files\Google\Chrome\Application\chrome.exe
```

### 8.4 utils/config.py - 配置数据类

`utils/config.py` 是 checkin.py（GitHub Actions 版）的配置层，定义了三个核心数据类：

**ProviderConfig - 平台配置**：

```python
@dataclass
class ProviderConfig:
    name: str                    # 平台名称
    domain: str                  # 域名（如 https://anyrouter.top）
    login_path: str = '/login'   # 登录页面路径
    sign_in_path: str = '/api/user/sign_in'  # 签到接口路径
                                 # 设为 None 表示查询 /api/user/self 即自动签到
    user_info_path: str = '/api/user/self'   # 用户信息接口
    api_user_key: str = 'new-api-user'       # 用户 ID 请求头名称
    bypass_method: str = None    # WAF 绕过方式：'waf_cookies' 或 None
```

**隐式设计耦合**：
```python
def needs_waf_cookies(self):
    return self.bypass_method == 'waf_cookies'

def needs_manual_check_in(self):
    return self.bypass_method == 'waf_cookies'  # 同样的条件！
```

> 这意味着 `needs_waf_cookies()` 和 `needs_manual_check_in()` 完全绑定：需要 WAF 的平台一定需要手动签到，不需要 WAF 的平台一定是自动签到。这个耦合是设计决策而非 Bug，但如果新增一个"需要 WAF 但自动签到"的平台，需要解耦这两个方法。

**默认平台配置**：

```python
# anyrouter: 需要 WAF + 手动签到
ProviderConfig(
    name='anyrouter', domain='https://anyrouter.top',
    sign_in_path='/api/user/sign_in',  # 显式签到
    bypass_method='waf_cookies',       # 需要 WAF
)

# agentrouter: 无 WAF + 自动签到
ProviderConfig(
    name='agentrouter', domain='https://agentrouter.org',
    sign_in_path=None,                 # 查询即签到，不调用签到接口
    bypass_method=None,                # 无 WAF
)
```

> **重要不一致**：auto_checkin.py 中 agentrouter 有显式 `sign_in_path='/api/user/sign_in'`（会调用签到接口），而这里是 `None`（不调用签到接口，查询自动签到）。实际效果一样（都能签到），但代码路径不同。

**AppConfig.load_from_env() - 配置加载逻辑**：

```python
# 1. 加载默认 providers (anyrouter + agentrouter)
# 2. 检查 PROVIDERS 环境变量，覆盖或新增 provider
#    格式: JSON 对象 {"platform_name": {"domain": "...", ...}}
# 3. 解析失败时回退到默认配置（不中断运行）
```

**AccountConfig - 账号配置**：

必须包含 `cookies`（dict 或 string 格式）和 `api_user` 字段。`name` 可选但非空。

cookies 字符串格式支持：`"session=MTc3MDk2OTIzNn...; other=value"` → 自动解析为 dict。

**load_accounts_config() - 账号加载**：

从 `ANYROUTER_ACCOUNTS` 环境变量读取 JSON 数组，逐条校验必须字段。

### 8.5 site_probe_results.json 格式

由 `probe_sites.py` 生成，记录所有探测站点的详细信息：

```json
{
  "name": "摸鱼公益",
  "domain": "https://clove.cc.cd",
  "alive": true,
  "is_newapi": true,
  "system_name": "摸鱼公益",
  "version": "v0.10.8-alpha.8",
  "linuxdo_oauth": true,
  "linuxdo_client_id": "Lr8C2Ny7JPr7c4YqysaDtVEqkO1a9eL7",
  "checkin_enabled": true,
  "turnstile_check": false,
  "min_trust_level": 1,
  "error": null
}
```

### 8.6 安全提醒与密码迁移方案

**当前安全问题**：

1. `multi_site_checkin.py` 第 73-79 行：5 个 LinuxDO 账号密码以**明文**硬编码在源码中
2. `auto_refresh_chrome.py` 第 48-53 行：同样明文硬编码
3. `update_sessions.json`：包含 session token
4. `checkin_results.json`：包含 session 前 50 字符

**`.gitignore` 已忽略的文件**：
- `.env`、`*.json`（配置文件）、`credentials.*`

**密码迁移方案**（推荐优先级）：

**方案 1：环境变量**（最简单）
```python
# 改造: 从环境变量读取
import os, json
LINUXDO_ACCOUNTS = json.loads(os.environ.get('LINUXDO_ACCOUNTS', '[]'))
```
- 本地：写入 `.env` 文件，用 `python-dotenv` 加载
- CI：配置 GitHub Secrets

**方案 2：Fernet 加密存储**（已有基础设施）
```python
# checkin.py 已使用 Fernet 加密，可复用
from cryptography.fernet import Fernet
key = os.environ['ENCRYPTION_KEY']  # 只需记住一个 key
fernet = Fernet(key)
passwords = json.loads(fernet.decrypt(encrypted_blob))
```

**方案 3：系统密钥环**
```python
import keyring
keyring.set_password('linuxdo', 'ZHnagsan', 'password')
password = keyring.get_password('linuxdo', 'ZHnagsan')
```

> 无论选哪种方案，核心原则：源码中不应包含任何明文密码。当前状态是临时开发方案，在公开仓库前必须迁移。

**SSL 验证禁用说明**：

checkin.py 使用 `verify=False` 禁用 SSL 证书验证（同时 `warnings.filterwarnings('ignore')` 静默警告）。原因：
- 部分公益站使用自签名或过期证书
- CI 环境的 CA 证书可能不完整
- 安全影响：理论上存在中间人攻击风险，但公益站的 session 价值有限，可接受

---

## 附录：踩坑记录

### A. WAF solve_waf.js 的 argv 索引

`process.argv[2]` 才是第一个用户参数（不是 `argv[1]`）：
```
argv[0] = node 可执行文件路径
argv[1] = 脚本文件路径 (solve_waf.js)
argv[2] = 第一个用户参数 (WAF 脚本文件路径)  ← 正确
```

### B. Chrome 临时 Profile 的必要性

真实 Chrome profile 被已运行的 Chrome 锁定，CDP 无法使用。必须用 `tempfile.mkdtemp()` 创建临时目录作为 `--user-data-dir`。

### C. Cloudflare AJAX 信任的"一次性"特性

通过页面导航建立的 CF 信任只能让后续的**第一个** AJAX 通过。因此 LinuxDO 登录必须在单个 `page.evaluate()` 中一次性完成 CSRF 获取 + POST 登录。

### D. OAuth Client ID 是平台特定的

每个平台有自己的 OAuth Client ID，不能混用。错误的 Client ID 会导致 OAuth 回调重定向到错误的平台。可通过各平台的 `/api/status` 接口查到正确的 Client ID。

### E. State 必须在浏览器内获取

如果用 httpx 获取 state，该 state 绑定在 httpx 的 WAF session 上。浏览器完成 OAuth 后回调时用的是浏览器的 WAF session，state 无法匹配。解决方案：在浏览器内通过 `fetch('/api/oauth/state')` 获取 state。

### F. new-api 签到需要双重认证

new-api 框架的 `authHelper()` 中间件同时检查 session cookie 和 `New-Api-User` 请求头。仅有 session cookie 会返回 401。解决方案：OAuth 登录后从 localStorage 提取用户 ID，或拦截 OAuth 回调获取 access_token。

### G. OAuth state 接口会设置 session cookie（旧 session 陷阱）

`/api/oauth/state` 请求会在浏览器中设置一个 session cookie。如果 OAuth 自动授权（跳过"允许"按钮），代码可能误捕获这个 state session 而非真正的 OAuth session。解决方案：在 OAuth 流程前记录所有已存在的 session cookie 值，之后只接受新出现的值。

### H. localStorage 用户 ID 提取需要等待 SPA 加载

OAuth 登录后导航到 `/console`，React SPA 需要数秒完成初始化并写入 localStorage。如果立即读取 localStorage 会返回 null。需要等待 5 秒左右让 SPA 完成加载和状态初始化。

### I. 全平台 OAuth 参数汇总

| 平台 | OAuth Client ID | redirect_uri | 签到接口 |
|------|-----------------|--------------|----------|
| AnyRouter | `8w2uZtoWH9AUXrZr1qeCEEmvXLafea3c` | `anyrouter.top/oauth/linuxdo` | `/api/user/sign_in` |
| AgentRouter | `KZUecGfhhDZMVnv8UtEdhOhf9sNOhqVX` | `agentrouter.org/oauth/linuxdo` | 查询自动签到 |
| Einzieg API | `aBambSqvDqCgTW8fCarJBeQji8M5RATf` | `api.einzieg.site/api/oauth/linuxdo` | `/api/user/checkin` |
| 摸鱼公益 | `Lr8C2Ny7JPr7c4YqysaDtVEqkO1a9eL7` | `clove.cc.cd/api/oauth/linuxdo` | `/api/user/checkin` |
| 老魔公益站 | `gnyvfmAfXrnYrt9ierq3Onj1ADvdVmmm` | `api.2020111.xyz/api/oauth/linuxdo` | `/api/user/checkin` |
| WoW公益站 | `3fcFoNvesssuyuFsvzBafjWivE4wvTwN` | `linuxdoapi.223384.xyz/api/oauth/linuxdo` | `/api/user/checkin` |
| Elysiver公益站 | `E2eaCQVl9iecd4aJBeTKedXfeKiJpSPF` | `elysiver.h-e.top/api/oauth/linuxdo` | `/api/user/checkin` |
| WONG公益站 | `451QxPCe4n9e7XrvzokzPcqPH9rUyTQF` | `wzw.pp.ua/api/oauth/linuxdo` | `/api/user/checkin` |
| 余额比寿命长 | `m17Y3zburaQfwCe53fWpae8tKPCuHXcy` | `new.123nhh.xyz/api/oauth/linuxdo` | `/api/user/checkin` |

### J. new-api 签到返回格式差异

不同版本的 new-api 签到成功后返回的 JSON 字段不同：

```
标准版 (v0.10.x):
  {"success": true, "message": "签到成功", "data": {"checkin_date": "2026-02-13", "quota_awarded": 1028987}}

dev 版 (WONG 公益站):
  {"success": true, "message": "", "data": {"checked_in": true, "quota": 3908710, "min_quota": 2500000, "max_quota": 5000000, "checked_at": 1770993990}}
```

脚本已兼容两种格式：优先读 `quota_awarded`，fallback 到 `quota`；空 `message` 默认显示"签到成功"。

### K. quota / 500000 额度换算系数

new-api 框架中 quota 使用内部整数单位，换算关系：

```
1 美元 = 500,000 quota 单位

示例:
  quota = 7,280,991 → $14.56
  quota = 3,908,710 → $7.82
  quota = 1,028,987 → $2.06
```

这个系数在 `checkin.py` 第 153 行和 `auto_checkin.py` 第 187 行均出现：`quota / 500000`。来源是 new-api 框架的 `model/user.go` 中的定义。

### L. 脚本间超时与等待时间对比

| 参数 | auto_checkin.py | checkin.py | multi_site_checkin.py | auto_refresh_chrome.py |
|------|----------------|------------|----------------------|----------------------|
| WAF 请求超时 | 15s | 30s | - | - |
| API 请求超时 | 30s | 30s | - | - |
| Node.js 子进程 | 10s | - | - | - |
| solve_waf.js 内部 | 5s | - | - | - |
| OAuth 总等待 | - | - | 120s | 180s |
| CF 通过等待循环 | - | - | 2s x 30 | 2s x 30 |
| 点击"允许"后等待 | - | - | 5s | 5s |
| SPA 加载等待 | - | - | 5s | - |
| WAF JS 执行等待 | - | - | 3s | 5s |
| probe 探测超时 | - | - | - | - |
| probe_sites.py | 10s | - | - | - |

> OAuth 总等待时间差异原因：auto_refresh_chrome.py 同时处理 AnyRouter 的 WAF（更慢），设 180s；multi_site_checkin.py 处理无 WAF 站点居多，设 120s。

> WAF JS 执行等待时间差异（3s vs 5s）：multi_site_checkin.py 处理的站点多数无 WAF，3s 足够；auto_refresh_chrome.py 处理 AnyRouter（重 WAF），5s 更保险。

### M. Discourse second_factor_method 枚举值

multi_site_checkin.py 登录请求中的 `second_factor_method=1`：

```
Discourse 二次验证方法枚举:
  0 = 无二次验证
  1 = TOTP (Time-based One-Time Password，如 Google Authenticator)
  2 = Backup codes
  3 = Security key (WebAuthn)
```

传 `1` 表示：如果账号开启了 TOTP 二次验证，告诉服务器期望的验证方式是 TOTP。对未开启二次验证的账号，此参数被忽略。

### N. Chrome CDP 端口 9222

```python
DEBUG_PORT = 9222
```

9222 是 Chrome DevTools Protocol 的**官方默认端口**。选择原因：
- Chrome 文档推荐的标准端口
- Playwright `connect_over_cdp` 的示例默认使用此端口
- 与 Chrome DevTools 的 Remote Debugging 端口一致

注意：同一时间只能有一个 Chrome 实例监听 9222 端口。multi_site_checkin.py 在每个账号处理前会 `kill_chrome()` 清理，避免端口冲突。

### O. checkin.py 的 HTTP/2 和反检测配置

```python
# checkin.py 独有配置
client = httpx.Client(http2=True, timeout=30.0, verify=False)
```

**http2=True**：启用 HTTP/2 协议。原因：
- 部分 WAF/CDN 对 HTTP/1.1 请求的检测更严格
- HTTP/2 的连接复用减少了 TLS 握手次数
- 某些 Cloudflare 配置对 HTTP/2 客户端更友好
- auto_checkin.py 不使用 HTTP/2 因为 Node.js WAF 解析不需要

**Playwright 反检测参数**（checkin.py）：
```
--disable-blink-features=AutomationControlled  # 隐藏 webdriver 标记
--disable-web-security                         # 禁用 CORS 检查
--no-sandbox                                   # CI 容器需要
--disable-dev-shm-usage                        # 避免 /dev/shm 空间不足
```

### P. kill_chrome() 的 gbk 编码

```python
subprocess.run(['taskkill', ...], encoding='gbk', errors='ignore')
```

Windows 中文系统的 `taskkill` 命令输出使用 GBK 编码（如"成功: 已终止进程..."）。如果不指定 `encoding='gbk'`，Python 在 UTF-8 模式下解码会报错。`errors='ignore'` 确保即使编码不匹配也不中断流程。
