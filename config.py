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

    # 顶部轮播品牌导览文案（纯展示）
    ANNOUNCEMENTS = [
        "英伦高定香氛典藏：甄选纯粹自然原料，诠释当代极简调香美学 | British Bespoke Perfumery",
        "探索 Scent Pairing™ 香氛叠穿艺术，自由混搭缔造独一无二的私人香印 | The Art of Scent Pairing",
        "标志性暖奶油色礼盒与黑色罗纹丝带，致敬源自伦敦的优雅礼赠传统 | Iconic British Craftsmanship",
    ]
