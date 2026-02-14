#!/usr/bin/env python3
"""
密码加密工具
用于加密和解密账号密码
"""
from cryptography.fernet import Fernet
import os
import base64

# 生成或加载加密密钥
def get_or_create_key():
    """获取或创建加密密钥"""
    key_file = '.encryption_key'
    
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key = f.read()
        print(f"✅ 已加载现有密钥")
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        print(f"🔑 已生成新密钥并保存到: {key_file}")
        print(f"⚠️  请将此密钥添加到环境变量或 .env 文件中")
        print(f"密钥: {key.decode()}")
    
    return key

def encrypt_password(password: str, key: bytes) -> str:
    """加密密码"""
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    return encrypted.decode()

def decrypt_password(encrypted_password: str, key: bytes) -> str:
    """解密密码"""
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_password.encode())
    return decrypted.decode()

if __name__ == '__main__':
    # 获取或创建密钥
    key = get_or_create_key()
    
    # 加密密码
    password = "Dxw19980927.."
    encrypted = encrypt_password(password, key)
    
    print("\n" + "="*60)
    print("🔐 密码加密结果")
    print("="*60)
    print(f"原始密码: {password}")
    print(f"加密后: {encrypted}")
    print("="*60)
    
    # 验证解密
    decrypted = decrypt_password(encrypted, key)
    print(f"\n✅ 解密验证: {decrypted}")
    print(f"✅ 加密/解密{'成功' if decrypted == password else '失败'}！")
    
    print("\n" + "="*60)
    print("📋 使用说明")
    print("="*60)
    print("1. 将加密后的密码复制到配置文件中")
    print("2. 在配置中使用 'encrypted_password' 字段")
    print("3. 将密钥保存到 .env 文件: ENCRYPTION_KEY=<密钥>")
    print("="*60)
