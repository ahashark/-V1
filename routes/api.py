"""
只读展示辅助接口蓝图 (Read-Only Showcase API Blueprint)
仅保留作品搜索建议与香氛叠穿品鉴层次展示接口，不包含登录注册、购物车或订单支付逻辑。
"""
from flask import Blueprint, jsonify, request

from core.database import fetch_product_by_slug, fetch_products

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/search", methods=["GET"])
def api_search():
    """实时检索香氛图鉴接口：按中英文名、香调或前中后调匹配作品。"""
    query = request.args.get("q", "").strip()
    if not query:
        featured = fetch_products(bestsellers_only=True, limit=4)
        return jsonify({"query": "", "results": featured})

    results = fetch_products(search_query=query, limit=6)
    return jsonify({"query": query, "results": results})


@api_bp.route("/scent-pairing", methods=["POST"])
def api_scent_pairing():
    """香氛叠穿品鉴接口：展示两款香氛混搭后的前中后调融合效果。"""
    payload = request.get_json(silent=True) or {}
    base_slug = str(payload.get("base_slug", "")).strip()
    layer_slug = str(payload.get("layer_slug", "")).strip()

    base_prod = fetch_product_by_slug(base_slug)
    layer_prod = fetch_product_by_slug(layer_slug)
    if not base_prod or not layer_prod:
        return jsonify({"error": "请选择有效的两款香氛"}), 400

    if base_slug == layer_slug:
        harmony_title = f"纯粹双重浓韵 · Pure {base_prod['scent_family']}"
        harmony_desc = (
            f"同款叠喷「{base_prod['name_zh']}」可强化{base_prod['top_note']}的明快开篇，"
            f"并令尾调{base_prod['base_note']}在肌肤上更加深邃持久。"
        )
    else:
        harmony_title = f"{base_prod['scent_family_zh']} × {layer_prod['scent_family_zh']} 专属定制香印"
        harmony_desc = (
            f"先以「{base_prod['name_zh']}」的{base_prod['base_note']}铺垫温润底色，"
            f"再叠穿「{layer_prod['name_zh']}」的{layer_prod['top_note']}与{layer_prod['heart_note']}，"
            f"交织出冷暖平衡、独树一帜的英伦高定层次。"
        )

    return jsonify(
        {
            "harmony_title": harmony_title,
            "harmony_desc": harmony_desc,
            "combined_notes": {
                "top": f"{base_prod['top_note']} · {layer_prod['top_note']}",
                "heart": f"{base_prod['heart_note']} · {layer_prod['heart_note']}",
                "base": f"{base_prod['base_note']} · {layer_prod['base_note']}",
            },
            "base_product": base_prod,
            "layer_product": layer_prod,
        }
    )
