"""数据库密码加密/解密工具。

使用 Fernet 对称加密（AES-128-CBC + HMAC-SHA256）保护数据库密码。
密钥通过环境变量 BUNKR_DB_KEY 传入，加密后的密码通过 BUNKR_DB_PASSWORD_ENC 传入。
"""

from __future__ import annotations
from dotenv import load_dotenv

import os

from cryptography.fernet import Fernet

# 加载环境变量
load_dotenv()

# 环境变量名称常量
ENV_KEY = "BUNKR_DB_KEY"
ENV_PASSWORD_ENC = "BUNKR_DB_PASSWORD_ENC"


def get_db_password() -> str:
    """从环境变量中读取并解密数据库密码。

    Returns:
        解密后的明文密码。

    Raises:
        RuntimeError: 缺少环境变量或解密失败。
    """
    key = os.environ.get(ENV_KEY)
    encrypted = os.environ.get(ENV_PASSWORD_ENC)

    if not key:
        raise RuntimeError(f"缺少环境变量 {ENV_KEY}，请先设置加密密钥")
    if not encrypted:
        raise RuntimeError(f"缺少环境变量 {ENV_PASSWORD_ENC}，请先设置加密后的密码")

    try:
        cipher = Fernet(key.encode("utf-8"))
        return cipher.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"数据库密码解密失败：{exc}") from exc


def encrypt_password(plain_password: str, key: str | None = None) -> str:
    """加密数据库密码（供加密脚本使用）。

    Args:
        plain_password: 明文密码。
        key: Fernet 密钥，若为 None 则从环境变量读取。

    Returns:
        加密后的密码字符串。
    """
    if key is None:
        key = os.environ.get(ENV_KEY)
        if not key:
            raise RuntimeError(f"缺少环境变量 {ENV_KEY}")

    cipher = Fernet(key.encode("utf-8"))
    return cipher.encrypt(plain_password.encode("utf-8")).decode("utf-8")
