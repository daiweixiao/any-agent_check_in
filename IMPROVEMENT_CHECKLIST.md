# 快速改进清单

## ✅ 已完成

### 1. 标记不可达站点为 skip
- [x] 摸鱼公益 (https://clove.cc.cd)
- [x] 佬友freestyle (https://api.freestyle.cc.cd)
- [x] New API (https://openai.api-test.us.ci)

**效果**: 减少 12 次无效尝试（3 站点 × 4 账号），节省约 2-3 分钟运行时间

---

## 📋 待实施优化

### 短期优化（1-2 天，预期提升至 65-70%）

#### 2. 增加 OAuth 重试机制
**位置**: `multi_site_checkin.py:655` (`oauth_login_site()`)

```python
async def oauth_login_site(page, ctx, domain, client_id, max_wait=60, max_retries=2):
    """OAuth 登录，支持重试"""
    for attempt in range(max_retries):
        try:
            # 现有逻辑
            session, token = await _do_oauth_login(page, ctx, domain, client_id, max_wait)
            if session:
                return session, token

            # 第一次失败，重试
            if attempt < max_retries - 1:
                log.warning(f'    [RETRY] OAuth 失败，3秒后重试 ({attempt+1}/{max_retries})')
                await asyncio.sleep(3)
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                log.warning(f'    [RETRY] OAuth 异常: {e}，3秒后重试')
                await asyncio.sleep(3)
                continue
            else:
                log.error(f'    [FAIL] OAuth 失败，已达最大重试次数')

    return None, None
```

**预期效果**: OAuth 失败率从 23 次降至 10-15 次

#### 3. LinuxDO 登录详细错误处理
**位置**: `multi_site_checkin.py:580` (`do_login()`)

```python
# 在 result = await page.evaluate(login_js, credentials) 后添加
if result:
    status = result.get('status')
    if status == 429:
        log.error(f'    [FAIL] LinuxDO 登录限流（429），请稍后重试')
    elif status == 403:
        log.error(f'    [FAIL] LinuxDO 账号被封禁或需要验证（403）')
    elif status == 401:
        log.error(f'    [FAIL] LinuxDO 账号密码错误（401）')
    elif status == 200:
        log.info(f'    [OK] LinuxDO 登录成功')
    else:
        log.error(f'    [FAIL] LinuxDO 登录失败: {result}')
```

**预期效果**: 更清晰的错误信息，便于排查问题

#### 4. 增加站点健康度检测
**位置**: `multi_site_checkin.py:285` (`sync_site_info()`)

```python
def update_site_health(info, site_key, success):
    """更新站点健康度"""
    site = info.get(site_key, {})
    health = site.get('health', {'total': 0, 'success': 0, 'consecutive_fails': 0})

    health['total'] += 1
    if success:
        health['success'] += 1
        health['consecutive_fails'] = 0
    else:
        health['consecutive_fails'] += 1

    health['success_rate'] = health['success'] / health['total']
    site['health'] = health

    # 连续失败 5 次 → 自动 skip 7 天
    if health['consecutive_fails'] >= 5:
        site['skip'] = True
        site['skip_reason'] = f"连续失败 {health['consecutive_fails']} 次，自动跳过"
        site['skip_until'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        log.warning(f'  [AUTO-SKIP] {site.get("name")} 连续失败 {health["consecutive_fails"]} 次，跳过 7 天')
```

**预期效果**: 自动识别问题站点，避免浪费时间

---

### 中期优化（3-7 天，预期提升至 75-80%）

#### 5. 智能重试策略
- OAuth 失败 → 等待 5 秒重试 1 次
- LinuxDO 登录失败 → 切换到下一个账号组
- 站点不可达 → 立即跳过

#### 6. 增加通知推送
```python
# 在 main() 结束时
if summary.get('failed', 0) > 30:
    await send_notification(
        title=f"⚠️ 签到失败率过高",
        content=f"成功: {summary['success']}, 失败: {summary['failed']}"
    )
```

#### 7. Session 过期预警
- 检测 session 即将过期（25 天后）→ 提前刷新
- 记录 session 刷新历史

---

### 长期优化（1-2 周，预期提升至 85-90%）

#### 8. Web Dashboard
- 实时查看签到状态
- 站点健康度可视化
- 手动触发单个站点签到

#### 9. 自动降级策略
- 健康度 < 50% → 降低优先级
- 连续失败 3 次 → 自动 skip 7 天
- 7 天后自动重新尝试

#### 10. 多账号智能调度
- 根据站点限流情况动态调整并发数
- 失败账号自动切换到备用账号

---

## 📊 预期改进效果

| 阶段 | 当前成功率 | 预期成功率 | 提升 | 时间 |
|------|-----------|-----------|------|------|
| **已完成** | 53.9% | 55-57% | +1-3% | 立即 |
| **短期优化** | 55-57% | 65-70% | +10-13% | 1-2天 |
| **中期优化** | 65-70% | 75-80% | +10% | 3-7天 |
| **长期优化** | 75-80% | 85-90% | +10% | 1-2周 |

**注意**: AgentRouter 的 5 个账号（约 3% 任务）因技术限制无法自动化。

---

## 🎯 下一步行动

### 立即执行
1. ✅ 标记不可达站点为 skip（已完成）
2. 提交配置变更到 Git
3. 等待下次自动运行验证效果

### 本周内
4. 实施 OAuth 重试机制
5. 增强 LinuxDO 登录错误处理
6. 添加站点健康度检测

### 本月内
7. 实现智能重试策略
8. 增加通知推送
9. Session 过期预警

---

**生成时间**: 2026-02-17
**下次更新**: 实施短期优化后
