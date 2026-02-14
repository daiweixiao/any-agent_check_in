# 🚀 GitHub Actions 自动签到配置指南

## 📋 概述

配置完成后，GitHub Actions 将：
- ⏰ 每6小时自动执行一次签到
- ☁️ 在云端运行，不占用本地资源
- 📱 支持多种通知方式
- 🔒 安全存储敏感信息

---

## 🎯 Step 1: 准备工作

### 1.1 创建 GitHub 账号（如果没有）

访问 https://github.com 注册账号（免费）

### 1.2 安装 Git（如果没有）

下载安装：https://git-scm.com/downloads

---

## 🎯 Step 2: 创建 GitHub 仓库

### 2.1 在 GitHub 创建新仓库

1. 访问 https://github.com/new
2. 填写信息：
   - Repository name: `anyrouter-checkin`
   - Description: `自动签到脚本`
   - ✅ 选择 **Private**（私有仓库，保护隐私）
   - ❌ 不要勾选 "Add a README file"
3. 点击 "Create repository"

### 2.2 上传代码到 GitHub

在项目目录打开 PowerShell，执行：

```powershell
# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: 自动签到脚本"

# 关联远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/anyrouter-checkin.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

**⚠️ 注意：** 将 `YOUR_USERNAME` 替换为你的 GitHub 用户名

---

## 🎯 Step 3: 配置 GitHub Secrets（重要！）

### 3.1 准备配置数据

从 `test_multi_accounts.py` 提取账号信息并转换为 JSON 格式：

```json
[
  {
    "name": "GitHub主号",
    "provider": "agentrouter",
    "linuxdo_username": "github_34327",
    "encrypted_password": "gAAAAABpAjDjwEzgLhzQXp5YGBH8tOdo1XdfxROvbad-s_TcNVLg2n0f7JvdN3MT6dgIsxIbpTtT6gFQayaOy60AmoEkP5NewQ==",
    "cookies": {
      "session": "你的session"
    },
    "api_user": "34327"
  }
]
```

### 3.2 添加 Secrets

1. 打开你的 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**

添加以下 Secrets：

#### **Secret 1: ANYROUTER_ACCOUNTS**

- Name: `ANYROUTER_ACCOUNTS`
- Secret: 粘贴完整的账号配置 JSON（包含所有11个账号）

#### **Secret 2: ENCRYPTION_KEY**

- Name: `ENCRYPTION_KEY`
- Secret: `Q94uwxjIRzf40zSpyBM3mczOhid4JmoGRM1hylSzJJM=`

#### **Secret 3: PROVIDERS（可选）**

如果需要自定义 provider 配置，添加此 Secret。

---

## 🎯 Step 4: 配置通知（可选）

### 方式1：Server酱（推荐）

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 获取 SendKey
4. 在 GitHub Secrets 中添加：
   - Name: `SERVERPUSHKEY`
   - Secret: 你的 SendKey

### 方式2：PushPlus

1. 访问 http://www.pushplus.plus/
2. 微信扫码登录
3. 获取 Token
4. 在 GitHub Secrets 中添加：
   - Name: `PUSHPLUS_TOKEN`
   - Secret: 你的 Token

### 方式3：邮件通知

在 GitHub Secrets 中添加：
- `EMAIL_USER`: 发送邮箱
- `EMAIL_PASS`: 邮箱密码或授权码
- `EMAIL_TO`: 接收邮箱

---

## 🎯 Step 5: 测试运行

### 5.1 手动触发测试

1. 打开 GitHub 仓库
2. 点击 **Actions** 标签
3. 选择 **AnyRouter 自动签到** workflow
4. 点击 **Run workflow** → **Run workflow**
5. 等待执行完成（约2-3分钟）

### 5.2 查看运行结果

1. 点击运行记录
2. 查看各个步骤的日志
3. 确认签到成功

---

## 🎯 Step 6: 配置定时任务

当前配置：**每6小时执行一次**

如果想修改执行时间，编辑 `.github/workflows/checkin.yml`：

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # 每6小时
    # - cron: '0 0 * * *'   # 每天0点
    # - cron: '0 8 * * *'   # 每天8点
```

---

## 📊 配置文件转换工具

我已经为你准备了一个转换工具，可以将 `test_multi_accounts.py` 转换为 GitHub Actions 需要的 JSON 格式。

运行：
```bash
python convert_config.py
```

---

## ❓ 常见问题

### Q1: 为什么要创建私有仓库？

A: 保护你的账号信息和密码不被他人看到。

### Q2: Secrets 安全吗？

A: 非常安全！GitHub Secrets 加密存储，只有你能看到，代码中无法直接访问。

### Q3: 会消耗多少免费额度？

A: 每次运行约1-2分钟，每月2000分钟足够使用。

### Q4: 如何停止自动签到？

A: 在 Actions 页面点击 "Disable workflow" 即可。

### Q5: 如何查看签到历史？

A: 在 Actions 页面可以看到所有运行记录和结果。

---

## 🎉 完成！

配置完成后，你的签到任务将：
- ✅ 每6小时自动执行
- ✅ 失败时自动重试
- ✅ 发送通知到微信/邮箱
- ✅ 保持 Session 活跃，不会过期

---

## 📝 下一步

1. ✅ 完成上述配置
2. 🧪 测试运行确认成功
3. 📱 配置通知方式
4. 🎯 放心使用，全自动签到！

有问题随时问我！
