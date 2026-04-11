"""
Trae 账号注册工具 - EXE 打包脚本
"""
import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"

def clean_build_dirs():
    """清理构建目录"""
    print("清理旧的构建文件...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

def build_exe():
    """构建 EXE"""
    print("=" * 60)
    print("开始打包 Trae 账号注册工具...")
    print("=" * 60)
    
    # 清理旧文件
    clean_build_dirs()
    
    # PyInstaller 命令
    cmd = [
        "pyinstaller",
        "--name=TraeAccountCreator",
        "--onefile",
        "--windowed",  # 不显示控制台
        "--icon=NONE",  # 可以添加图标
        "--add-data=index.html;.",  # 包含 HTML 文件
        "--hidden-import=aiohttp",
        "--hidden-import=playwright",
        "--hidden-import=colorama",
        "--hidden-import=httpx",
        f"--workpath={BUILD_DIR}",
        f"--distpath={DIST_DIR}",
        "--specpath=.",
        "--clean",
        "server.py"
    ]
    
    print(f"执行命令：{' '.join(cmd)}")
    print()
    
    # 执行打包
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✅ 打包成功！")
        print(f"EXE 文件位置：{DIST_DIR / 'TraeAccountCreator.exe'}")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ 打包失败！请检查错误信息")
        print("=" * 60)
    
    return result.returncode

if __name__ == "__main__":
    build_exe()
