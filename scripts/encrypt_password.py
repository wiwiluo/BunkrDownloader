#!/usr/bin/env python3
"""数据库密码加密工具。

首次部署时运行此脚本，生成加密后的密码并提示设置环境变量。

用法：
    python scripts/encrypt_password.py

前置条件：
    - 环境变量 BUNKR_DB_KEY 已设置（若未设置，脚本会自动生成一个）
"""

from __future__ import annotations

import os
import sys

from cryptography.fernet import Fernet

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crypto_utils import ENV_KEY, encrypt_password  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("BunkrDownloader 数据库密码加密工具")
    print("=" * 60)

    key = os.environ.get(ENV_KEY)
    if key:
        print(f"[✓] 已检测到环境变量 {ENV_KEY}")
    else:
        print(f"[!] 未检测到环境变量 {ENV_KEY}")
        key = Fernet.generate_key().decode()
        print(f"[→] 已生成新密钥: {key}")
        print(f"[→] 请执行: export {ENV_KEY}='{key}'")

    password = input("请输入数据库密码: ").strip()
    if not password:
        print("[✗] 密码不能为空")
        sys.exit(1)

    encrypted = encrypt_password(password, key)
    print(f"\n[✓] 加密成功！")
    print(f"[→] 加密后的密码: {encrypted}")
    print(f"\n请执行以下命令设置环境变量：")
    print(f"  export {ENV_KEY}='{key}'")
    print(f"  export BUNKR_DB_PASSWORD_ENC='{encrypted}'")
    print(f"\n建议将上述 export 命令添加到 ~/.bashrc 或启动脚本中。")


if __name__ == "__main__":
    main()
