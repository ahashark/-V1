"""
应用主入口 (Application Entrypoint)
基于 Python Flask 构建的英伦奢华香氛纯展示型网站框架（无注册登录、无购物车与订单支付模块）。
"""
from flask import Flask, render_template

from config import Config
from core.database import fetch_categories
from core.seed import seed_database
from routes.api import api_bp
from routes.pages import pages_bp


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    # 启动时确保只读商品展示目录已就绪
    seed_database()

    # 注册页面与只读展示接口蓝图
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_site_globals():
        """注入全站共享的品牌名称、自定义域名、公告文案与导航分类。"""
        return {
            "brand_name": app.config["BRAND_NAME"],
            "brand_origin": app.config["BRAND_ORIGIN"],
            "site_url": app.config["SITE_URL"],
            "custom_domain": app.config["CUSTOM_DOMAIN"],
            "announcements": app.config["ANNOUNCEMENTS"],
            "nav_categories": fetch_categories(),
        }

    @app.errorhandler(404)
    def page_not_found(_error):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
