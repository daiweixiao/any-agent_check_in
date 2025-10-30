# WAF Cookies 缓存优化方案

## 🎯 优化目标

减少 AnyRouter 签到时的浏览器启动次数，通过缓存 WAF cookies 实现快速签到。

---

## 📊 现状分析

### **当前流程**
```
每次签到:
├─ 启动 Playwright 浏览器     ~20秒
├─ 访问登录页获取 WAF cookies  ~20秒
├─ 执行签到请求               ~1秒
└─ 总耗时: 40-60秒
```

### **优化后流程**
```
首次签到:
├─ 启动浏览器获取 WAF cookies  ~40秒
├─ 缓存 cookies 到文件
└─ 执行签到

后续签到:
├─ 读取缓存的 WAF cookies     ~0.1秒
├─ 尝试签到
├─ 如果失败 → 重新获取 WAF cookies
└─ 耗时: 1-2秒（成功时）
```

---

## 💡 实现方案

### **步骤 1: 创建 WAF Cookies 缓存模块**

```python
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class WAFCookieCache:
    """WAF Cookies 缓存管理器"""
    
    def __init__(self, cache_dir: str = '.waf_cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_file(self, account_name: str) -> Path:
        """获取账号的缓存文件路径"""
        safe_name = account_name.replace(' ', '_').replace('/', '_')
        return self.cache_dir / f'{safe_name}.json'
    
    def save(self, account_name: str, waf_cookies: dict):
        """保存 WAF cookies"""
        cache_data = {
            'cookies': waf_cookies,
            'timestamp': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=2)).isoformat()
        }
        
        cache_file = self.get_cache_file(account_name)
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f'[CACHE] {account_name}: WAF cookies saved to cache')
    
    def load(self, account_name: str) -> dict | None:
        """加载 WAF cookies（如果有效）"""
        cache_file = self.get_cache_file(account_name)
        
        if not cache_file.exists():
            print(f'[CACHE] {account_name}: No cache found')
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            
            if datetime.now() > expires_at:
                print(f'[CACHE] {account_name}: Cache expired')
                cache_file.unlink()  # 删除过期缓存
                return None
            
            print(f'[CACHE] {account_name}: Valid cache found')
            return cache_data['cookies']
        
        except Exception as e:
            print(f'[CACHE] {account_name}: Failed to load cache: {e}')
            return None
    
    def clear(self, account_name: str):
        """清除指定账号的缓存"""
        cache_file = self.get_cache_file(account_name)
        if cache_file.exists():
            cache_file.unlink()
            print(f'[CACHE] {account_name}: Cache cleared')
```

---

### **步骤 2: 修改签到逻辑**

```python
async def prepare_cookies_with_cache(
    account_name: str, 
    provider_config, 
    user_cookies: dict,
    cache_manager: WAFCookieCache
) -> dict | None:
    """准备 cookies（支持缓存）"""
    
    if not provider_config.needs_waf_cookies():
        # AgentRouter 无需 WAF
        return user_cookies
    
    # 尝试从缓存加载 WAF cookies
    waf_cookies = cache_manager.load(account_name)
    
    if waf_cookies:
        print(f'[INFO] {account_name}: Using cached WAF cookies')
        # 先尝试使用缓存的 cookies
        all_cookies = {**waf_cookies, **user_cookies}
        
        # 快速验证：尝试获取用户信息
        if await validate_cookies(account_name, provider_config, all_cookies):
            print(f'[SUCCESS] {account_name}: Cached cookies are valid')
            return all_cookies
        else:
            print(f'[WARNING] {account_name}: Cached cookies invalid, refreshing...')
            cache_manager.clear(account_name)
    
    # 缓存无效或不存在，启动浏览器获取
    print(f'[INFO] {account_name}: Getting fresh WAF cookies...')
    login_url = f'{provider_config.domain}{provider_config.login_path}'
    waf_cookies = await get_waf_cookies_with_playwright(account_name, login_url)
    
    if not waf_cookies:
        return None
    
    # 保存到缓存
    cache_manager.save(account_name, waf_cookies)
    
    return {**waf_cookies, **user_cookies}


async def validate_cookies(
    account_name: str,
    provider_config,
    cookies: dict
) -> bool:
    """快速验证 cookies 是否有效"""
    try:
        client = httpx.Client(http2=True, timeout=10.0)
        client.cookies.update(cookies)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        user_info_url = f'{provider_config.domain}{provider_config.user_info_path}'
        response = client.get(user_info_url, headers=headers)
        client.close()
        
        return response.status_code == 200 and response.json().get('success', False)
    except Exception:
        return False
```

---

### **步骤 3: 更新主函数**

```python
async def main():
    """主函数（支持缓存）"""
    print('[SYSTEM] AnyRouter.top multi-account auto check-in script started')
    
    # 初始化缓存管理器
    cache_manager = WAFCookieCache()
    
    app_config = AppConfig.load_from_env()
    accounts = load_accounts_config()
    
    for i, account in enumerate(accounts):
        account_name = account.get_display_name(i)
        provider_config = app_config.get_provider(account.provider)
        
        user_cookies = parse_cookies(account.cookies)
        
        # 使用缓存版本的 prepare_cookies
        all_cookies = await prepare_cookies_with_cache(
            account_name, 
            provider_config, 
            user_cookies,
            cache_manager  # 传入缓存管理器
        )
        
        # ... 继续签到流程
```

---

## 📊 性能对比

### **优化前**
```
签到 1: 浏览器启动 40秒 + 签到 1秒 = 41秒
签到 2: 浏览器启动 40秒 + 签到 1秒 = 41秒
签到 3: 浏览器启动 40秒 + 签到 1秒 = 41秒
总耗时: 123秒
```

### **优化后（缓存有效）**
```
签到 1: 浏览器启动 40秒 + 签到 1秒 + 缓存 = 41秒
签到 2: 读缓存 0.1秒 + 签到 1秒 = 1.1秒
签到 3: 读缓存 0.1秒 + 签到 1秒 = 1.1秒
总耗时: 43秒

⚡ 提速: 65% (123秒 → 43秒)
```

---

## ⚠️ 注意事项

### **优点**
✅ 大幅减少执行时间（首次后快 40 倍）
✅ 降低浏览器启动频率
✅ 自动处理缓存过期

### **缺点**
⚠️ 增加代码复杂度
⚠️ 需要维护缓存文件
⚠️ WAF 可能检测到缓存使用（小概率）

### **风险**
1. **WAF 策略变化**：阿里云可能调整验证策略
2. **缓存污染**：无效缓存可能导致签到失败
3. **存储需求**：需要持久化存储（GitHub Actions 需要 artifacts）

---

## 🎯 推荐做法

### **场景 1: GitHub Actions（不推荐缓存）**
- 每 6 小时执行一次
- 40 秒启动时间可接受
- 无需复杂缓存逻辑
- **建议：保持原样**

### **场景 2: 本地频繁测试（推荐缓存）**
- 开发调试时频繁运行
- 每次等 40 秒很烦
- 本地有文件系统缓存
- **建议：使用缓存优化**

### **场景 3: 多账号 AnyRouter（推荐缓存）**
- 有 5+ 个 AnyRouter 账号
- 总耗时会很长
- 缓存可以显著提速
- **建议：使用缓存优化**

---

## 🚀 快速决策

**问自己：**
1. 我有多少个 AnyRouter 账号？
   - 1-2 个 → 不需要优化
   - 3+ 个 → 考虑优化

2. 我多久运行一次？
   - GitHub Actions 自动 → 不需要
   - 本地频繁测试 → 需要优化

3. 我能接受 40 秒等待吗？
   - 可以接受 → 保持原样
   - 不能接受 → 实施优化

---

## 💡 最简单的优化

如果你只是想**偶尔手动运行**，最简单的方法是：

**把 WAF cookies 手动复制到配置中：**

```json
{
  "name": "AnyRouter 账号",
  "provider": "anyrouter",
  "cookies": {
    "session": "你的session",
    "acw_tc": "从浏览器复制",
    "cdn_sec_tc": "从浏览器复制",
    "acw_sc__v2": "从浏览器复制"
  },
  "api_user": "87260"
}
```

**优点：**
- 无需修改代码
- 立即生效
- 几小时内有效

**缺点：**
- 需要手动维护
- 过期后重新复制
- 不适合自动化
