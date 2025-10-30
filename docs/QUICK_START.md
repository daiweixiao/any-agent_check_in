# ⚡ GitHub Actions 快速开始（5分钟配置）

## 🎯 你将得到什么？

✅ 每6小时自动签到  
✅ 完全云端运行  
✅ 永久免费  
✅ 微信/邮件通知

---

## 📝 快速配置步骤

### Step 1: 创建 GitHub 仓库（2分钟）

1. 访问 https://github.com/new
2. 填写：
   - Repository name: `anyrouter-checkin`
   - 选择 **Private** ⬅️ 重要！
3. 点击 "Create repository"

### Step 2: 上传代码（1分钟）

在项目目录打开 PowerShell，复制粘贴执行：

```powershell
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/anyrouter-checkin.git
git branch -M main
git push -u origin main
```

**⚠️ 记得替换 `你的用户名`**

### Step 3: 配置 Secrets（2分钟）

#### 3.1 复制配置

运行命令打开配置文件：
```powershell
notepad github_actions_config.json
```

按 `Ctrl+A` 全选，`Ctrl+C` 复制

#### 3.2 添加到 GitHub

1. 打开你的 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. 填写：
   - Name: `ANYROUTER_ACCOUNTS`
   - Secret: 粘贴刚才复制的内容
5. 点击 **Add secret**

#### 3.3 添加加密密钥

再次点击 **New repository secret**：
- Name: `ENCRYPTION_KEY`
- Secret: `Q94uwxjIRzf40zSpyBM3mczOhid4JmoGRM1hylSzJJM=`

### Step 4: 测试运行（1分钟）

1. 点击 **Actions** 标签
2. 选择 **AnyRouter 自动签到**
3. 点击 **Run workflow** → **Run workflow**
4. 等待2分钟，查看结果 ✅

---

## 🎉 完成！

现在你的签到任务将：
- ⏰ 每6小时自动执行（0点、6点、12点、18点）
- ☁️ 在 GitHub 云端运行
- 📱 可配置通知到微信

---

## 📱 （可选）配置微信通知

### 使用 Server酱（推荐，1分钟）

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制你的 SendKey
4. 在 GitHub Secrets 添加：
   - Name: `SERVERPUSHKEY`
   - Secret: 你的 SendKey

完成！现在签到结果会推送到微信

---

## ❓ 遇到问题？

### 问题1: git 命令找不到

**解决：** 安装 Git https://git-scm.com/downloads

### 问题2: push 需要登录

**解决：** 
```powershell
# 使用个人访问令牌
# 1. GitHub → Settings → Developer settings → Personal access tokens → Generate new token
# 2. 勾选 repo 权限
# 3. 复制生成的 token
# 4. push 时使用 token 作为密码
```

### 问题3: Actions 没有运行

**检查：**
1. Settings → Actions → General
2. 确保 "Allow all actions and reusable workflows" 已选中
3. 保存设置

---

## 📖 详细文档

需要更多信息？查看：
- 📄 `GITHUB_ACTIONS_SETUP.md` - 完整配置指南
- 🔐 `PASSWORD_ENCRYPTION_GUIDE.md` - 密码加密说明

---

## 💡 提示

- 配置完成后，本地的 `test_multi_accounts.py` 可以继续用于本地测试
- GitHub Actions 和本地测试互不影响
- 可以随时在 Actions 页面查看运行历史

---

**🎊 开始配置吧！整个过程只需5分钟！**
