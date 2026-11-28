"""
全局配置文件 (Global Configuration)
支持本地 Flask 预览、Ubuntu 生产环境部署与导出静态站点托管至 GitHub Pages。
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "atelier_fragrance.db"
STATIC_BUILD_DIR = BASE_DIR / "docs"


class Config:
    DATABASE = os.environ.get("ATELIER_DB_PATH", str(DATABASE_PATH))

    # 站点域名与基础地址（支持通过环境变量覆盖为内网或生产地址，如 http://192.168.118.128）
    CUSTOM_DOMAIN = os.environ.get("CUSTOM_DOMAIN", "sxy.ink")
    SITE_URL = os.environ.get("SITE_URL", "https://sxy.ink").rstrip("/")

    # 品牌基础设定（参考 jomalone.co.uk 英伦奢华香氛视觉定位）
    BRAND_NAME = "MAISON L'ATELIER"
    BRAND_ORIGIN = "LONDON"

    # 顶部轮播品牌导览文案（英文主导，中文辅助）
    ANNOUNCEMENTS = [
        "British Bespoke Perfumery — Crafted in London with pure botanical ingredients · 英伦高定调香典藏",
        "Discover Scent Pairing™ — Layer fragrances to compose your personal signature · 自由叠穿艺术",
        "Iconic Presentation — Signature monochrome box hand-tied with grosgrain ribbon · 标志性礼盒美学",
    ]
