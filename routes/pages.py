"""
页面视图路由蓝图 (Showcase Page Views Blueprint)
统一使用尾部斜杠路径（如 /shop/、/category/<slug>/），完美兼容 GitHub Pages 静态目录托管。
"""
from flask import Blueprint, abort, render_template, request

from core.database import (
    fetch_categories,
    fetch_category_by_slug,
    fetch_product_by_slug,
    fetch_products,
)

pages_bp = Blueprint("pages", __name__)

SCENT_FAMILIES = [
    {"key": "Fruity", "label": "Fruity · 果香"},
    {"key": "Woody", "label": "Woody · 木质"},
    {"key": "Floral", "label": "Floral · 花香"},
    {"key": "Citrus", "label": "Citrus · 柑橘"},
    {"key": "Amber", "label": "Amber · 琥珀"},
]


@pages_bp.route("/")
def index():
    """网站首页：主视觉海报、代表作精选、四大香氛领域、芳醇黑瓶专区、香氛叠穿品鉴与礼盒美学。"""
    categories = fetch_categories()
    bestsellers = fetch_products(bestsellers_only=True, limit=4)
    colognes_for_pairing = fetch_products(category_slug="colognes")
    intense_featured = [p for p in colognes_for_pairing if p.get("is_intense")]
    return render_template(
        "index.html",
        categories=categories,
        bestsellers=bestsellers,
        colognes_for_pairing=colognes_for_pairing,
        intense_featured=intense_featured,
    )


@pages_bp.route("/shop/")
def shop_all():
    """全系列香氛图鉴页：支持按香调过滤、关键词检索与排序展示。"""
    scent = request.args.get("scent", "").strip() or None
    sort_by = request.args.get("sort", "featured").strip()
    q = request.args.get("q", "").strip() or None

    products = fetch_products(
        scent_family=scent,
        search_query=q,
        sort_by=sort_by,
    )
    virtual_category = {
        "slug": "all",
        "name_en": "All Creations",
        "name_zh": "全部香氛与奢护典藏",
        "eyebrow": "THE COMPLETE ARCHIVE",
        "description": "Explore our complete archive of classic colognes, rich Cologne Intense, home candles, and signature gifts. · 探索经典古龙水、芳醇黑瓶、居室香氛与典藏礼盒全系作品。",
        "hero_image": "/static/images/hero_editorial.jpg",
    }
    return render_template(
        "category.html",
        category=virtual_category,
        products=products,
        scent_families=SCENT_FAMILIES,
        current_scent=scent or "",
        current_sort=sort_by,
        search_query=q or "",
        is_shop_all=True,
    )


@pages_bp.route("/category/<slug>/")
def category_detail(slug: str):
    """分类展示页：/category/colognes/, /category/home/, /category/bath-body/, /category/gifts/"""
    category = fetch_category_by_slug(slug)
    if not category:
        abort(404)

    scent = request.args.get("scent", "").strip() or None
    sort_by = request.args.get("sort", "featured").strip()

    products = fetch_products(
        category_slug=slug,
        scent_family=scent,
        sort_by=sort_by,
    )
    return render_template(
        "category.html",
        category=category,
        products=products,
        scent_families=SCENT_FAMILIES,
        current_scent=scent or "",
        current_sort=sort_by,
        search_query="",
        is_shop_all=False,
    )


@pages_bp.route("/product/<slug>/")
def product_detail(slug: str):
    """香氛作品详情展示页：调香灵感、瓶身规格一览、前中后调品鉴与叠穿推荐。"""
    product = fetch_product_by_slug(slug)
    if not product:
        abort(404)

    paired_product = None
    if product.get("pair_with_slug"):
        paired_product = fetch_product_by_slug(product["pair_with_slug"])

    related_products = [
        p
        for p in fetch_products(category_slug=product["category_slug"], limit=5)
        if p["slug"] != product["slug"]
    ][:3]

    category = fetch_category_by_slug(product["category_slug"])
    return render_template(
        "product.html",
        product=product,
        category=category,
        paired_product=paired_product,
        related_products=related_products,
    )


@pages_bp.route("/services/")
def services_page():
    """品牌工艺与英伦美学展示页。"""
    return render_template("services.html")
