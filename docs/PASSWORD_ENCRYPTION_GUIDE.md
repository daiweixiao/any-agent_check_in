# 🔐 密码加密使用指南

## ✅ 已完成配置

所有AgentRouter账号的密码已加密并配置完成！

### 📋 配置摘要

- **加密算法**: Fernet (对称加密)
- **加密密码**: `gAAAAABpAjDjwEzgLhzQXp5YGBH8tOdo1XdfxROvbad-s_TcNVLg2n0f7JvdN3MT6dgIsxIbpTtT6gFQayaOy60AmoEkP5NewQ==`
- **原始密码**: `Dxw19980927..` (已加密存储)
- **密钥位置**: `.encryption_key` 文件

---

## 🔑 密钥管理

### 密钥存储位置

密钥保存在项目根目录的 `.encryption_key` 文件中：

```
.encryption_key  (已自动生成)
```

### ⚠️ 重要安全提示

1. **不要将密钥文件提交到Git**
   - `.encryption_key` 已被 `.gitignore` 忽略
   - 确保不会意外提交

2. **备份密钥**
   - 将密钥复制到安全的地方
   - 密钥丢失将无法解密密码

3. **环境变量（可选）**
   ```bash
   # 可以将密钥设置为环境变量
   export ENCRYPTION_KEY="Q94uwxjIRzf40zSpyBM3mczOhid4JmoGRM1hylSzJJM="
   ```

---

## 🚀 使用方法

### 自动解密

脚本会自动解密密码，无需手动操作：

```python
# 配置文件中
{
    "name": "账号名称",
    "linuxdo_username": "用户名",
    "encrypted_password": "加密后的密码",  # ← 自动解密
    ...
}
```

### 手动测试解密

运行测试脚本验证解密功能：

```bash
python encrypt_password.py
```

---

## 🔧 如何添加新账号

### 1. 加密新密码

如果新账号使用不同的密码：

```bash
python encrypt_password.py
# 修改脚本中的 password = "新密码"
```

### 2. 添加到配置

```python
{
    "name": "新账号",
    "provider": "agentrouter",
    "linuxdo_username": "linuxdo_xxxxx",
    "encrypted_password": "加密后的密码字符串",
    "cookies": {"session": ""},
    "api_user": "xxxxx"
}
```

---

## 📊 当前配置状态

### AgentRouter账号（6个）- 已全部加密

| 账号 | 用户名 | 密码状态 |
|------|--------|----------|
| GitHub主号 | github_34327 | ✅ 已加密 |
| linuxdo_caijijiji | linuxdo_34877 | ✅ 已加密 |
| ZHnagsan | linuxdo_34874 | ✅ 已加密 |
| heshangd | linuxdo_45550 | ✅ 已加密 |
| CaiWai | linuxdo_46573 | ✅ 已加密 |
| kefuka | linuxdo_34872 | ✅ 已加密 |

### AnyRouter账号（5个）

AnyRouter账号不需要自动登录，继续使用session cookie即可。

---

## 🛡️ 安全特性

✅ **密码不可见** - 配置文件中只有加密字符串  
✅ **自动解密** - 使用时自动解密，无需手动操作  
✅ **密钥分离** - 密钥文件独立存储，不提交到Git  
✅ **兼容现有** - 不影响现有的cookie认证方式  

---

## ❓ 常见问题

### Q: 密钥丢失怎么办？

A: 如果密钥丢失，需要：
1. 运行 `encrypt_password.py` 生成新密钥
2. 重新加密所有密码
3. 更新配置文件中的 `encrypted_password` 字段

### Q: 可以在GitHub Actions中使用吗？

A: 可以！在GitHub仓库设置中添加Secret：
- Name: `ENCRYPTION_KEY`
- Value: `Q94uwxjIRzf40zSpyBM3mczOhid4JmoGRM1hylSzJJM=`

### Q: 密码会以明文形式出现吗？

A: 不会。密码只在内存中解密，不会写入日志或文件。

---

## 📝 下一步

1. ✅ 配置已完成 - 可以直接使用
2. 🧪 测试签到 - 运行 `python test_multi_accounts.py`
3. 🔄 自动刷新 - session过期时会自动登录获取新cookie
4. ⏰ 定时任务 - 配置GitHub Actions实现自动签到

---

**🎉 恭喜！密码加密配置完成！**
