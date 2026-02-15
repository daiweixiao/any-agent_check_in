# 站点信息注册表

> 最后更新: 2026-02-16
> 配套技术文档: [TECHNICAL_GUIDE.md](./TECHNICAL_GUIDE.md)

---

## 目录

- [一、文档说明](#一文档说明)
- [二、账号总览](#二账号总览)
- [三、站点统计](#三站点统计)
- [四、已配置站点（自动签到就绪）](#四已配置站点自动签到就绪)
- [五、待添加站点（new-api + 签到 + 无障碍）](#五待添加站点new-api--签到--无障碍)
- [六、需特殊处理站点](#六需特殊处理站点)
- [七、无签到功能站点](#七无签到功能站点)
- [八、非 new-api 站点](#八非-new-api-站点)
- [九、死亡站点](#九死亡站点)
- [十、账号-站点注册映射](#十账号-站点注册映射)
- [十一、技术问题索引](#十一技术问题索引)
- [十二、操作指引](#十二操作指引)

---

## 一、文档说明

### 1.1 本文档与技术文档的关系

| 文档 | 定位 | 内容 |
|------|------|------|
| **SITE_REGISTRY.md（本文档）** | 运营信息手册 | 站点清单、状态、账号映射、问题索引 |
| **TECHNICAL_GUIDE.md** | 技术实现手册 | 代码原理、绕过方案、脚本使用、踩坑记录 |

**查找路径**：本文档发现问题 -> 查看"技术问题"列 -> 跳转到 TECHNICAL_GUIDE.md 对应章节

### 1.2 站点状态说明

| 标记 | 含义 |
|------|------|
| 已配置 | 在 `sites.json` 中已有配置，可直接运行 |
| **待添加** | 已探测确认可用，只需添加配置即可 |
| **需处理** | 有 Turnstile / 未知签到 / WAF 等障碍，需额外工作 |
| **无签到** | 站点正常但明确不支持签到功能 |
| **非标准** | 不是 new-api 框架，需要独立的签到方案 |
| **死亡** | 服务器不可达，域名失效 |

### 1.3 信任等级（TL）说明

LinuxDO 论坛的用户信任等级，部分站点有最低等级要求：

| TL | 等级 | 大致要求 |
|----|------|----------|
| 0 | 新用户 | 注册即可 |
| 1 | 基本用户 | 浏览一定时间 |
| 2 | 成员 | 活跃参与讨论 |
| 3 | 资深成员 | 长期活跃 |

---

## 二、账号总览

### 2.1 LinuxDO 账号

| 编号 | 标签 | 邮箱 | TL 等级 | 状态 | 备注 |
|------|------|------|---------|------|------|
| 1 | ZHnagsan | `2621097668@qq.com` | **待确认** | 正常 | 主号 |
| 2 | caijijiji | `dw2621097668@gmail.com` | **待确认** | 正常 | |
| 3 | CaiWai | `daixiaowei985@gmail.com` | **待确认** | 正常 | |
| 4 | heshangd | `2330702014@st.btbu.edu.cn` | **待确认** | 正常 | |
| ~~5~~ | ~~kefuka~~ | ~~`xiaoweidai998@163.com`~~ | - | **已封禁** | LinuxDO 账号被封，已从脚本移除 |

> **重要**: 每个账号的 TL 等级直接决定可用站点范围。
> 确认方法: 浏览器登录 LinuxDO -> 用户设置页查看信任等级。
> TL2 站点（dev88、ThatAPI、MTU、六哥API）在账号 TL 不足时 OAuth 会被拒绝。

### 2.2 账号信任等级影响

| 最低 TL 要求 | 可用站点数 | 说明 |
|-------------|----------|------|
| TL0 | 所有站点 | 无限制 |
| TL1 | 大部分站点 | 排除 TL2/TL3 站点 |
| TL2 | 需确认 | dev88、六哥API、MTU、ThatAPI、AmazonQ2API 等 |
| TL3 | 仅 Nyxar API | 极高门槛 |

> 如果账号 TL 不够，OAuth 登录会被站点拒绝。需确认每个账号的实际 TL 等级。

---

## 三、站点统计

| 分类 | 数量 | 说明 |
|------|------|------|
| 已配置 - 活跃 | 27 | 自动签到运行中 |
| 已配置 - 跳过 | 6 | 已配置但因权限/域名等问题跳过 |
| 需特殊处理 | 5 | Turnstile / WAF |
| 无签到功能 | 9 | 站点正常但不支持签到 |
| 非 new-api | 12 | 不同框架，需独立方案 |
| 死亡 | 7 | 服务器不可达（2026-02-13 二次确认） |
| **合计** | **66** | |

> **数据来源**: `site_info.json` + `checkin_results.json`（2026-02-16 运行结果）
> **数据新鲜度**: 公益站状态变化快，建议每周运行 `probe_sites.py` 刷新

---

## 四、已配置站点（33 个）

当前 `sites.json` 中已配置 33 个站点：27 个活跃 + 6 个跳过。

### 4.1 活跃站点（27 个）

#### 全部账号签到成功（21 个）

| # | 站点名 | 域名 | TL | Client ID | 状态 |
|---|--------|------|-----|-----------|------|
| 1 | 老魔公益站 | `api.2020111.xyz` | 1 | `gnyvfmAfXrnYrt9ierq3Onj1ADvdVmmm` | 4/4 成功 |
| 2 | WoW公益站 | `linuxdoapi.223384.xyz` | 0 | `3fcFoNvesssuyuFsvzBafjWivE4wvTwN` | 4/4 成功 |
| 3 | Elysiver公益站 | `elysiver.h-e.top` | ? | 运行时获取 | 4/4 成功 |
| 4 | WONG公益站 | `wzw.pp.ua` | 1 | `451QxPCe4n9e7XrvzokzPcqPH9rUyTQF` | 4/4 成功 |
| 5 | 余额比寿命长 | `new.123nhh.xyz` | 1 | `m17Y3zburaQfwCe53fWpae8tKPCuHXcy` | 4/4 成功 |
| 6 | HotaruAPI | `hotaruapi.com` | 1 | `qVGkHnU8fLzJVEMgHCuNUCYifUQwePWn` | 4/4 成功 |
| 7 | KFC公益站 | `kfc-api.sxxe.net` | 0 | `UZgHjwXCE3HTrsNMjjEi0d8wpcj7d4Of` | 4/4 成功 |
| 8 | duckcoding黄鸭 | `free.duckcoding.com` | 1 | `XNJfOdoSeXkcx80mDydoheJ0nZS4tjIf` | 4/4 成功 |
| 9 | duckcoding-jp | `jp.duckcoding.com` | 0 | `MGPwGpfcyKGHsdnsY0BMpt6VZPrkxOBd` | 4/4 成功 |
| 10 | 小呆API-base | `api.daiju.live` | 1 | `Bl5uJRVkjxVpGC2MDw3UZdzb89RMguVa` | 4/4 成功 |
| 11 | Embedding公益站 | `router.tumuer.me` | 1 | `L3bf5EA8RoJJObIJ2W7g1CaVAZNEqM4M` | 4/4 成功 |
| 12 | Huan API | `ai.huan666.de` | 1 | `FNvJFnlfpfDM2mKDp8HTElASdjEwUriS` | 4/4 成功 |
| 13 | 慕鸢公益站 | `newapi.linuxdo.edu.rs` | 1 | `rxyZeu4Wg8HNzwaG6YCj6OnFvap7ZfRU` | 4/4 成功 |
| 14 | NPC API | `npcodex.kiroxubei.tech` | 1 | `APUcB3LChvSGi3FmkODZx6Ij2038mkHY` | 4/4 成功 |
| 15 | Jarvis API | `ai.ctacy.cc` | 1 | `vtdgTJlFRj6WZjCfjuNucKeNXn5rplzV` | 4/4 成功 |
| 16 | 云端API | `cloudapi.wdyu.eu.cc` | 1 | `RLuQBBcU7LkZmed1mvqiktf2O5lhjbVv` | 4/4 成功 |
| 17 | ibsgss公益站 | `codex.ibsgss.uk` | 1 | `F3kKRQ29SJGivfhtIpjE0W0tAyxbvR2X` | 4/4 成功 |
| 18 | 星野Ai新站 | `api.hoshino.edu.rs` | 1 | `XPXmWksr3NcH2aiz0MgqK5jtEmfdfZ0Q` | 4/4 成功 |
| 19 | Zer0by公益站 | `new-api.oseeue.com` | 1 | `03yHVaQuD9VhIZM63IL8xHne3wiCGxCI` | 4/4 成功 |
| 20 | Old API | `sakuradori.dpdns.org` | 1 | `QSRbjIGtYWCdyd0SPEiXGN4HlK4k0n7Z` | 4/4 成功 |
| 21 | 纳米哈基米 | `free.nanohajimi.mom` | 1 | `svkUqtRyhOJMULQ1Zfnfhvv9ALSnANhf` | 4/4 成功 |

#### 部分账号成功（3 个）- CF 验证不稳定

| # | 站点名 | 域名 | TL | Client ID | ZHnagsan | caijijiji | CaiWai | heshangd | 问题 |
|---|--------|------|-----|-----------|----------|-----------|--------|----------|------|
| 22 | Einzieg API | `api.einzieg.site` | 1 | `aBambSqvDqCgTW8fCarJBeQji8M5RATf` | OK | OK | X | X | CF 超时 |
| 23 | dev88公益站 | `api.dev88.tech` | **2** | `E8gcZeQkasYqaNiM2GwjUbV1ztY1owAc` | OK | OK | X | X | TL2 + CF |
| 24 | ThatAPI | `gyapi.zxiaoruan.cn` | **2** | `doAqU5TVU6L7sXudST9MQ102aaJObESS` | OK | OK | X | X | TL2 + CF |

> 这 3 个站点不是固定失败，是 CF/WAF 验证超时导致，下次运行可能成功。

#### 站点不可达（3 个）- 服务端问题

| # | 站点名 | 域名 | 问题 |
|---|--------|------|------|
| 25 | 摸鱼公益 | `clove.cc.cd` | 站点无法连接 |
| 26 | 佬友freestyle | `api.freestyle.cc.cd` | 站点无法连接 |
| 27 | New API | `openai.api-test.us.ci` | 站点无法连接 |

### 4.2 跳过站点（6 个）

已配置但因权限不足、域名异常等原因标记为 `skip`：

| # | 站点名 | 域名 | 跳过原因 |
|---|--------|------|----------|
| 1 | uibers | `www.uibers.com` | OAuth 始终失败，原因未知 |
| 2 | 小呆API | `new.184772.xyz` | 重定向到 api.daiju.live，与 xiaodai_base 重复 |
| 3 | MTU公益 | `jiuuij.de5.net` | 需 TL2，所有账号均不满足 |
| 4 | 略貌取神 | `lmq.kangnaixi.xyz` | 签到返回「权限不足」，多账号均不满足 TL 要求 |
| 5 | 六哥API | `api.crisxie.top` | 需 TL2，签到返回「权限不足」 |
| 6 | 不知名公益站 | `api.agentify.top` | 签到返回「权限不足」 |

> 这些站点可能需要更高的 TL 等级，或站点管理员限制了 OAuth 注册。

### 4.3 最近运行结果（2026-02-16）

> 数据来源: `site_info.json` + `checkin_results.json` | 运行模式: 4 账号并行 + Session 缓存

| 指标 | 值 |
|------|-----|
| 总耗时 | 189s（3.2 分钟） |
| 活跃站点 | 27 个 |
| 全部成功 | 21 个站点（4/4 账号） |
| 部分成功 | 3 个站点（CF 不稳定） |
| 站点不可达 | 3 个站点 |
| 有效完成 | 90/108 (83%) |

---

## 五、待添加站点

原有 23 个待添加站点已全部配置到 `multi_site_checkin.py` 中。
当前无待添加站点。如需添加新站点，运行 `probe_sites.py` 探测后在 `sites.json` 中添加：

```json
"site_key": {
    "domain": "https://example.com",
    "name": "站点名称",
    "client_id": "xxx"
}
```

> `domain` 必填，`name`/`client_id` 可选（运行时自动获取）。运行脚本时 `sync_site_info()` 自动检测新站点。

---

## 六、需特殊处理站点

### 6.1 有 Turnstile 验证

Turnstile 是 Cloudflare 的人机验证，签到时可能需要额外处理。

| # | 站点名 | 域名 | TL | Client ID | 签到 | 系统名 | 问题描述 |
|---|--------|------|-----|-----------|------|--------|----------|
| 1 | AmazonQ2API / 随时跑路 | `runanytime.hxi.me` | **2** | `AHjK9O3FfbCXKpF6VXGBC60K21yJ2fYk` | 有 | 随时跑路公益站 | Turnstile + TL2 双重门槛 |
| 2 | lhyb公益站 | `api.lhyb.dpdns.org` | **2** | `oIKl9QwICthtBMXvdNxfh9ATkok8dR7i` | 无 | SWT-API（Free） | Turnstile + 无签到，价值低 |
| 3 | lhyb备用站 | `new-api.koyeb.app` | **2** | `oIKl9QwICthtBMXvdNxfh9ATkok8dR7i` | 无 | SWT-API（Free） | 同上（与 lhyb 共享 client_id） |

> **AmazonQ2API 和 随时跑路是同一站点**（域名 `runanytime.hxi.me`），probe_sites.py 中重复列出。
> -> 技术参考: 当前脚本不支持 Turnstile 绕过，需开发。可能的方案见 TECHNICAL_GUIDE.md 3.2

### 6.2 签到状态未知（需实测）

~~以下 3 个站点已实测，均返回"权限不足"，已移入第四节跳过列表：略貌取神、六哥API、不知名公益站。~~

当前无待测站点。

### 6.3 有 WAF 拦截

| # | 站点名 | 域名 | 探测错误 | 问题描述 |
|---|--------|------|----------|----------|
| 1 | AmazonQ2API-veloera | `veloera.henryyang.net` | HTTP 403 (CF) | CF WAF 403，httpx 无法直接访问，需浏览器判断框架 |
| 2 | 星野Ai | `api.feisakura.fun` | HTTP 403 (非JSON) | CF 403 Forbidden，httpx 无法访问，需浏览器判断框架 |

> Elysiver 已解决（运行时获取 client_id），已在第四节活跃站点中。
> -> 技术参考: TECHNICAL_GUIDE.md 3.2 Cloudflare 绕过

---

## 七、无签到功能站点

以下站点确认 `checkin_enabled=false`，不支持签到。保留记录供查阅。

| # | 站点名 | 域名 | TL | 系统名 | 版本 | Client ID |
|---|--------|------|-----|--------|------|-----------|
| 1 | 薄荷API | `x666.me` | 0 | 薄荷 API | v0.10.6-alpha.3 | `4OtAotK6cp4047lgPD4kPXNhWRbRdTw3` |
| 2 | 曼波公益站 | `ai.dik3.cn` | 1 | New API | v0.10.7-alpha.2 | `TFZYenTLVo2Ccstnn1hCGvUKZ9YLvUFb` |
| 3 | Nyxar API | `api.nyxar.org` | **3** | Nyxar API | v0.10.9-alpha.4 | `J3FchPMGNbhC1xsPPIybn2XSbb7rOcOa` |
| 4 | SlapqAPI | `api.slapq.top` | 2 | New API | v0.10.7-alpha.2 | `1wJQoP1NtcbRQtsduJ81IMsUM1p5kgcG` |
| 5 | OAI-FREE | `newapi.zhx47.xyz` | 1 | OAI-FREE | v0.10.9-alpha.6 | `gvlcRLQo0yVPTrd5GeOOI8LfAf7tT6hz` |
| 6 | WEBSEE公益站 | `newapi.websee.top` | 1 | New API | 0.4.15-patch.1 | `T84bj40oLmv0nfeGtMt4DimDid2rDOCB` |
| 7 | yx公益站 | `api.dx001.ggff.net` | 1 | yx | v0.10.6-alpha.3 | `WkF9VyuufVWPV8FnBeQUlRxlvmLqWYi4` |
| 8 | 玩玩公益站 | `api.zwd5168.cn` | 0 | 玩玩 | v0.10.9-alpha.3 | *(无 OAuth)* |
| 9 | ManyRouter | `manyrouter.chaosyn.com` | 0 | ManyRouter | v0.10.8-alpha.7 | *(无 OAuth)* |

> 注: 玩玩公益站和 ManyRouter 虽是 new-api 但无 LinuxDO OAuth（无 client_id），属于纯 API 站。
> Nyxar API 要求 TL3，门槛极高。
> 这些站点虽然无签到功能，但保留 client_id 记录便于将来站点开启签到时快速配置。

---

## 八、非 new-api 站点

### 8.1 有 LinuxDO OAuth 但非标准框架

| # | 站点名 | 域名 | 框架 | 签到 | 探测结果 | 说明 |
|---|--------|------|------|------|----------|------|
| 1 | GGBOOM签到站 | `sign.qaq.al` | 自研（Discourse SSO + PoW） | 有（独立机制） | / 返回 200, title="GGBOOM公益签到站" | 完成 PoW 计算领余额 |
| 2 | 随时跑路福利站 | `fuli.hxi.me` | 未知（HTML SPA） | 未知 | / 返回 200, 非 JSON 的 HTML | 需浏览器进一步分析 |

> GGBOOM签到站使用 Discourse SSO 而非 OAuth2，签到需要完成 PoW（Proof of Work）计算，无法用当前脚本。
> 实测：浏览器访问 `/auth/login` 可触发 Discourse SSO 登录。
> -> 需独立开发签到方案

### 8.2 new-api 但无 LinuxDO OAuth

这些站点是 new-api 但不支持 LinuxDO OAuth 登录，需要其他登录方式（邮箱/密码/token）。

| # | 站点名 | 域名 | 系统名 | 版本 | 签到 | Turnstile | 说明 |
|---|--------|------|--------|------|------|-----------|------|
| 1 | 哈基咪 | `api.gemai.cc` | 哈基米API站 | v0.10.9-alpha.2 | **有** | 无 | 需邮箱/密码登录 |
| 2 | Code Router | `api.codemirror.codes` | Code Router | - | 未知 | 无 | 无 OAuth |
| 3 | 黑与白 | `ai.hybgzs.com` | 黑与白公益站 | v1.20.29 | 未知 | **有** | Turnstile + 无 OAuth |
| 4 | 熊猫API | `api520.pro` | 熊猫API | v0.0.0 | 未知 | 无 | 无 OAuth |
| 5 | WindHub公益站 | `api.224442.xyz` | Wind Hub | v0.0.0 | 未知 | 无 | 无 OAuth |
| 6 | Code反重力 | `code.claudex.us.ci` | Code公益站-反重力号池 | v1.10.27 | 未知 | 无 | 无 OAuth，版本异常高 |

> 哈基咪确认有签到（`checkin_enabled=true`），但无 LinuxDO OAuth，需要其他登录方式获取 session。

### 8.3 完全非 new-api 框架

| # | 站点名 | 域名 | 框架 | 探测结果 | 说明 |
|---|--------|------|------|----------|------|
| 1 | OhMyGPT | `www.ohmygpt.com` | 自有商业平台 | / 返回 200 HTML (zh-CN) | 非 new-api，前端自研 |
| 2 | 学渣助手 | `gptkey.eu.org` | Gemini Business2API (FastAPI) | / 返回 200, /api/* 返回 FastAPI JSON | 完全不同的后端框架 |
| 3 | GGBOOM公益站 | `ai.qaq.al` | Sub2API | / 返回 200, title="Sub2API - AI API Gateway" | 非 new-api，Go 后端 |
| 4 | easychat | `easychat.site` | 未知（HTML SPA） | / 返回 200 HTML | 非 new-api |

---

## 九、死亡站点

经二次确认（2026-02-13 多路径重检），以下站点确认不可达：

| # | 站点名 | 域名 | 死因 | 重检结果 |
|---|--------|------|------|----------|
| 1 | lhyb副站 | `api2.lhyb.dpdns.org` | DNS/连接失败 | 全路径连接失败 |
| 2 | 23公益站 | `sdwfger.edu.kg` | 服务器宕机 | 521 Web server is down |
| 3 | 兰兰公益站 | `api.venlacy.top` | Tunnel 断开 | 530 Cloudflare Tunnel error |
| 4 | ICAT公益站 | `icat.pp.ua` | DNS/连接失败 | 全路径连接失败 |
| 5 | 佬友API | `lyclaude.site` | DNS/连接失败 | 全路径连接失败 |
| 6 | 太子公益API | `taizi.api.51yp.de5.net` | SSL 故障 | SSL handshake failure |
| 7 | FKAI公益站 | `orchids.fuckai.me` | 服务器宕机 | 522 Connection timed out |
| 8 | 莹和兰(旧) | `api.hotaruapi.top` | 域名迁移 | 403 Forbidden，新域名 hotaruapi.com 已在活跃站点 |

> 公益站随时可能恢复或永久关闭。建议每周运行一次 `probe_sites.py` 复查。

---

## 十、账号-站点注册映射

> 数据来源: `site_info.json`（2026-02-16 运行结果）
> "Y" = 登录+签到成功, "~" = 登录成功但签到异常, "X" = OAuth 失败, "D" = 站点不可达, "S" = 跳过

| 站点 | ZHnagsan | caijijiji | CaiWai | heshangd |
|------|:--------:|:---------:|:------:|:--------:|
| 老魔公益站 | Y | Y | Y | Y |
| WoW公益站 | Y | Y | Y | Y |
| Elysiver公益站 | Y | Y | Y | Y |
| WONG公益站 | Y | Y | Y | Y |
| 余额比寿命长 | Y | Y | Y | Y |
| HotaruAPI | Y | Y | Y | Y |
| KFC公益站 | Y | Y | Y | Y |
| duckcoding黄鸭 | Y | Y | Y | Y |
| duckcoding-jp | Y | Y | Y | Y |
| 小呆API-base | Y | Y | Y | Y |
| Embedding公益站 | Y | Y | Y | Y |
| Huan API | Y | Y | Y | Y |
| 慕鸢公益站 | Y | Y | Y | Y |
| NPC API | Y | Y | Y | Y |
| Jarvis API | Y | Y | Y | Y |
| 云端API | Y | Y | Y | Y |
| ibsgss公益站 | Y | Y | Y | Y |
| 星野Ai新站 | Y | Y | Y | Y |
| Zer0by公益站 | Y | Y | Y | Y |
| Old API | Y | Y | Y | Y |
| 纳米哈基米 | Y | Y | Y | Y |
| Einzieg API | Y | Y | X | X |
| dev88公益站 | Y | Y | X | X |
| ThatAPI | Y | Y | X | X |
| 摸鱼公益 | D | D | D | D |
| 佬友freestyle | D | D | D | D |
| New API | D | D | D | D |
| uibers | S | S | S | S |
| 小呆API | S | S | S | S |
| MTU公益 | S | S | S | S |
| 略貌取神 | S | S | S | S |
| 六哥API | S | S | S | S |
| 不知名公益站 | S | S | S | S |

> kefuka 账号已封禁，已从脚本移除。

---

## 十一、技术问题索引

按问题类型分类，指向 TECHNICAL_GUIDE.md 对应章节：

### 11.1 认证类

| 问题 | 涉及站点 | 解决方案位置 |
|------|----------|-------------|
| OAuth 全站失败（如 kefuka） | 所有站点 | TECHNICAL_GUIDE.md 7.3 LinuxDO 登录失败, 7.6 "允许"按钮 |
| OAuth 获取 session 失败 | Einzieg（CaiWai/heshangd） | TECHNICAL_GUIDE.md 7.4, 附录G state session 陷阱 |
| 签到 401 "未提供 New-Api-User" | 所有 new-api 站点 | TECHNICAL_GUIDE.md 6.2 认证机制, 7.8, 附录F |
| access_token 捕获 | 所有 new-api 站点 | TECHNICAL_GUIDE.md 6.3 方式1 (response 拦截) |
| 用户 ID 从 localStorage 提取 | 所有 new-api 站点 | TECHNICAL_GUIDE.md 6.3 方式2, 附录H |
| state session 陷阱（捕获旧 cookie） | 所有 new-api 站点 | TECHNICAL_GUIDE.md 附录G |

### 11.2 防护/拦截类

| 问题 | 涉及站点 | 解决方案位置 |
|------|----------|-------------|
| Cloudflare 拦截（不稳定） | Einzieg API | TECHNICAL_GUIDE.md 3.2 Cloudflare 绕过, 附录C |
| 阿里云 WAF | Elysiver公益站 | TECHNICAL_GUIDE.md 3.2, 附录E |
| Cloudflare WAF（403） | AmazonQ2API-veloera, 星野Ai | TECHNICAL_GUIDE.md 3.2 |
| Turnstile 人机验证 | AmazonQ2API, lhyb公益站/备用站, 黑与白 | 当前脚本不支持，需开发 |
| AnyRouter WAF（acw_sc__v2） | anyrouter.top | TECHNICAL_GUIDE.md 3.1 |

### 11.3 格式/兼容类

| 问题 | 涉及站点 | 解决方案位置 |
|------|----------|-------------|
| 签到返回 `quota` 而非 `quota_awarded` | WONG公益站 | TECHNICAL_GUIDE.md 附录J |
| 签到返回空 `message` | WONG公益站 | TECHNICAL_GUIDE.md 附录J |
| /api/status 响应超时 | 余额比寿命长 | TECHNICAL_GUIDE.md 附录L（timeout 需 >10s）|
| client_id 需运行时获取 | Elysiver公益站 | TECHNICAL_GUIDE.md 6.4 站点配置, 附录E |
| 小呆API 两站共享 client_id | 小呆API, 小呆API-base | 可能共享用户系统，需实测 |
| quota/500000 换算 | 所有签到站点 | TECHNICAL_GUIDE.md 附录K（500000 = $1） |

### 11.4 框架差异类

| 问题 | 涉及站点 | 说明 |
|------|----------|------|
| Discourse SSO + PoW | GGBOOM签到站 | 完全不同的认证机制，需独立方案 |
| Sub2API 框架 | GGBOOM公益站 | 非 new-api，API 结构不同 |
| FastAPI 后端 | 学渣助手 | Gemini Business2API，无签到 |
| 自有平台 | OhMyGPT | 商业平台，非开源框架 |
| 无 OAuth 的 new-api | 哈基咪, Code Router, 熊猫API 等 | 需其他登录方式（邮箱/密码/token） |

### 11.5 规模扩展类（已解决）

| 问题 | 说明 | 解决方案 |
|------|------|----------|
| 27 站点 x 4 账号 = 108 签到任务 | 串行执行耗时 96 分钟 | 已实现：Session 缓存 + httpx 直连（30s 完成缓存命中站点） |
| 多账号排队等待 | 4 账号串行，每个 20+ 分钟 | Windows：asyncio.gather 并行，4 账号同时执行（端口 9222-9225） |
| Linux 服务器内存不足 | 多 Chrome 实例 OOM | 已实现：自动检测内存 < 3GB 切换串行模式（单 Chrome，端口 9222），或 `--serial` 手动指定 |
| Linux 环境适配 | Chrome 路径/headless/进程管理 | 已实现：`shutil.which` 自动检测路径，headless + `--no-sandbox`，`pkill` 替代 `taskkill` |
| Chrome 内存占用 | 长时间运行 Chrome 可能泄漏 | 每账号独立 Chrome 实例（临时 profile），运行后自动关闭 |
| 站点宕机导致超时阻塞 | 死站超时 10-20s | skip 标记机制 + OAuth 超时 78s 自动跳过 |
| Session 文件并发写入 | 并行账号同时写 site_info.json | save_site_info() 原子模式（asyncio 单线程安全） |

---

## 十二、操作指引

### 12.1 环境准备

```bash
# Windows
pip install httpx playwright
playwright install chromium
# 确认 Chrome 路径: C:\Program Files\Google\Chrome\Application\chrome.exe

# Linux（阿里云等服务器）
pip install httpx playwright
sudo dnf install -y chromium        # CentOS/RHEL/Alibaba Cloud Linux
# 或 sudo apt install -y chromium-browser  # Ubuntu/Debian
```

### 12.2 日常签到

```bash
# 运行多站点签到（27 个活跃站点 x 4 个账号）
python multi_site_checkin.py

# Linux 服务器：内存 < 3GB 自动串行，也可手动指定
python multi_site_checkin.py --serial

# 执行流程:
# Phase 1: httpx 直连（用缓存 session，~30s 完成大部分站点）
# Phase 2: 浏览器 OAuth（仅处理无缓存/缓存过期的站点）
#
# Windows 并行模式:
#   首次运行: ~22 分钟 | 日常: ~7 分钟 | 缓存全命中: ~1-2 分钟
# Linux 串行模式:
#   日常: ~10 分钟 | 缓存全命中: ~2-3 分钟
#
# 输出文件:
# - checkin_results.json  签到结果
# - site_info.json        Session 缓存 + 运行数据（自动维护）
# - logs/checkin_*.log    详细日志
```

### 12.3 添加新站点

在 `sites.json` 中追加：

```json
"site_key": {
    "domain": "https://域名",
    "name": "站点中文名",
    "client_id": "xxx"
}
```

> `domain` 必填，`name`/`client_id` 可选（运行时自动获取）。
> 如需跳过某站点，添加 `"skip": true, "skip_reason": "原因"`。
> 如需限制账号，添加 `"accounts": ["ZHnagsan", "caijijiji"]`。

### 12.4 探测站点状态

```bash
# 全量探测（检查所有站点存活、版本、签到状态）
python probe_sites.py
# 建议频率: 每周一次
```

### 12.5 排查问题流程

```
签到失败
  |
  +-- OAuth 失败 --> 检查 LinuxDO 登录是否正常
  |                   --> 检查账号 TL 是否满足站点要求
  |                   --> 参考 TECHNICAL_GUIDE.md 7.x
  |
  +-- Session 过期 --> 脚本会自动删除缓存并走 OAuth 重新获取
  |                   --> 如果反复过期，检查站点是否正常
  |
  +-- 签到 401 --> 检查 access_token / New-Api-User
  |               --> 参考 TECHNICAL_GUIDE.md 6.2, 附录F
  |
  +-- 站点无响应 --> 运行 probe_sites.py 检查存活
  |                --> 可能站点已死，添加 skip: True
  |
  +-- CF/WAF 拦截 --> 参考 TECHNICAL_GUIDE.md 3.x
```

---

## 附录：站点域名速查表

按拼音/字母排序，快速查找站点所在章节：

| 站点 | 域名 | 所在章节 |
|------|------|----------|
| AmazonQ2API / 随时跑路 | runanytime.hxi.me | 六.1 (Turnstile) |
| Code Router | api.codemirror.codes | 八.2 |
| Code反重力 | code.claudex.us.ci | 八.2 |
| dev88公益站 | api.dev88.tech | 四.1 (TL2) |
| duckcoding-jp | jp.duckcoding.com | 四.1 |
| duckcoding黄鸭 | free.duckcoding.com | 四.1 |
| easychat | easychat.site | 八.3 |
| Einzieg API | api.einzieg.site | 四.1 |
| Elysiver公益站 | elysiver.h-e.top | 四.1 |
| Embedding公益站 | router.tumuer.me | 四.1 |
| FKAI公益站 | orchids.fuckai.me | 九 |
| GGBOOM公益站 | ai.qaq.al | 八.3 |
| GGBOOM签到站 | sign.qaq.al | 八.1 |
| Huan API | ai.huan666.de | 四.1 |
| HotaruAPI | hotaruapi.com | 四.1 |
| ibsgss公益站 | codex.ibsgss.uk | 四.1 |
| ICAT公益站 | icat.pp.ua | 九 |
| Jarvis API | ai.ctacy.cc | 四.1 |
| KFC公益站 | kfc-api.sxxe.net | 四.1 |
| lhyb公益站 | api.lhyb.dpdns.org | 六.1 |
| lhyb副站 | api2.lhyb.dpdns.org | 九 |
| lhyb备用站 | new-api.koyeb.app | 六.1 |
| ManyRouter | manyrouter.chaosyn.com | 七 |
| MTU公益 | jiuuij.de5.net | 四.2 (跳过, TL2) |
| New API | openai.api-test.us.ci | 四.1 |
| NPC API | npcodex.kiroxubei.tech | 四.1 |
| Nyxar API | api.nyxar.org | 七 (TL3) |
| OAI-FREE | newapi.zhx47.xyz | 七 |
| OhMyGPT | www.ohmygpt.com | 八.3 |
| Old API | sakuradori.dpdns.org | 四.1 |
| SlapqAPI | api.slapq.top | 七 |
| ThatAPI | gyapi.zxiaoruan.cn | 四.1 (TL2) |
| uibers | www.uibers.com | 四.2 (跳过) |
| WEBSEE公益站 | newapi.websee.top | 七 |
| WindHub公益站 | api.224442.xyz | 八.2 |
| WONG公益站 | wzw.pp.ua | 四.1 |
| WoW公益站 | linuxdoapi.223384.xyz | 四.1 |
| Zer0by公益站 | new-api.oseeue.com | 四.1 |
| yx公益站 | api.dx001.ggff.net | 七 |
| 不知名公益站 | api.agentify.top | 四.2 (跳过) |
| 余额比寿命长 | new.123nhh.xyz | 四.1 |
| 佬友API | lyclaude.site | 九 |
| 佬友freestyle | api.freestyle.cc.cd | 四.1 |
| 六哥API | api.crisxie.top | 四.2 (跳过, TL2) |
| 兰兰公益站 | api.venlacy.top | 九 |
| 哈基咪 | api.gemai.cc | 八.2 |
| 太子公益API | taizi.api.51yp.de5.net | 九 |
| 学渣助手 | gptkey.eu.org | 八.3 |
| 小呆API | new.184772.xyz | 四.2 (跳过) |
| 小呆API-base | api.daiju.live | 四.1 |
| 慕鸢公益站 | newapi.linuxdo.edu.rs | 四.1 |
| 摸鱼公益 | clove.cc.cd | 四.1 |
| 曼波公益站 | ai.dik3.cn | 七 |
| 星野Ai | api.feisakura.fun | 六.3 |
| 星野Ai新站 | api.hoshino.edu.rs | 四.1 |
| 略貌取神 | lmq.kangnaixi.xyz | 四.2 (跳过) |
| 玩玩公益站 | api.zwd5168.cn | 七 |
| 熊猫API | api520.pro | 八.2 |
| 纳米哈基米 | free.nanohajimi.mom | 四.1 |
| 老魔公益站 | api.2020111.xyz | 四.1 |
| 莹和兰 | api.hotaruapi.top | 九 (域名已迁移) |
| 薄荷API | x666.me | 七 |
| 随时跑路福利站 | fuli.hxi.me | 八.1 |
| 云端API | cloudapi.wdyu.eu.cc | 四.1 |
| 黑与白 | ai.hybgzs.com | 八.2 |
| 23公益站 | sdwfger.edu.kg | 九 |
