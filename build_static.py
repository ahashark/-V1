"""
Python 静态网站构建器 (Static Site Exporter for GitHub Pages)
将 Flask 渲染的所有页面、静态资源、前端检索数据集 catalog.json 以及自定义域名 CNAME (sxy.ink)
一键导出至 docs/ 目录，可直接托管于 GitHub Pages。
"""
import json
import shutil
from pathlib import Path

from app import create_app
from config import BASE_DIR, STATIC_BUILD_DIR, Config
from core.database import fetch_categories, fetch_products


def write_route_html(client, route_path: str, output_file: Path, expected_status: int = 200) -> None:
    """请求指定 Flask 路由并将渲染后的 HTML 写入目标静态文件。"""
    resp = client.get(route_path)
    if resp.status_code != expected_status:
        raise RuntimeError(
            f"构建路由 {route_path} 失败：期望状态码 {expected_status}，实际为 {resp.status_code}"
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(resp.get_data(as_text=True), encoding="utf-8")


def build_static_site() -> None:
    app = create_app()
    categories = fetch_categories()
    products = fetch_products()

    # 1. 生成前端检索与筛选所需的静态 JSON 数据集（同步写入源码 static/data 以方便本地调试）
    catalog_payload = {
        "domain": Config.CUSTOM_DOMAIN,
        "categories": categories,
        "products": products,
    }
    src_data_dir = BASE_DIR / "static" / "data"
    src_data_dir.mkdir(parents=True, exist_ok=True)
    (src_data_dir / "catalog.json").write_text(
        json.dumps(catalog_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2. 清空并重建 docs/ 输出目录
    if STATIC_BUILD_DIR.exists():
        shutil.rmtree(STATIC_BUILD_DIR)
    STATIC_BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # 3. 复制全部静态资源 (CSS / JS / Images / catalog.json)
    shutil.copytree(BASE_DIR / "static", STATIC_BUILD_DIR / "static")

    # 4. 渲染所有展示页面为静态 HTML 目录结构
    generated_pages = []
    with app.test_client() as client:
        core_routes = [
            ("/", STATIC_BUILD_DIR / "index.html"),
            ("/shop/", STATIC_BUILD_DIR / "shop" / "index.html"),
            ("/services/", STATIC_BUILD_DIR / "services" / "index.html"),
        ]
        for route, target in core_routes:
            write_route_html(client, route, target, 200)
            generated_pages.append(route)

        for cat in categories:
            route = f"/category/{cat['slug']}/"
            target = STATIC_BUILD_DIR / "category" / cat["slug"] / "index.html"
            write_route_html(client, route, target, 200)
            generated_pages.append(route)

        for prod in products:
            route = f"/product/{prod['slug']}/"
            target = STATIC_BUILD_DIR / "product" / prod["slug"] / "index.html"
            write_route_html(client, route, target, 200)
            generated_pages.append(route)

        # 生成 GitHub Pages 原生支持的 404.html
        write_route_html(client, "/__404_export__", STATIC_BUILD_DIR / "404.html", 404)
        generated_pages.append("/404.html")

    # 5. 写入 GitHub Pages 自定义域名文件 CNAME 与 .nojekyll
    (STATIC_BUILD_DIR / "CNAME").write_text(f"{Config.CUSTOM_DOMAIN}\n", encoding="utf-8")
    (STATIC_BUILD_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"[OK] 静态站点构建完成 -> {STATIC_BUILD_DIR}")
    print(f"[OK] 自定义域名 CNAME -> {Config.CUSTOM_DOMAIN}")
    print(f"[OK] 共导出 {len(generated_pages)} 个静态页面：{generated_pages}")


if __name__ == "__main__":
    build_static_site()
