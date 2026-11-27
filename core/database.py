"""
SQLite 只读商品目录与分类数据访问模块
仅保留分类（categories）与香氛作品（products）展示表，无用户、购物车及订单支付表。
"""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config


def get_db_connection() -> sqlite3.Connection:
    """获取带有 Row 字典访问能力的 SQLite 连接。"""
    db_path = Path(Config.DATABASE)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """将 sqlite3.Row 转换为普通字典，并解析容量规格列表。"""
    if row is None:
        return None
    data = dict(row)
    if "variants_json" in data and isinstance(data["variants_json"], str):
        try:
            data["variants"] = json.loads(data["variants_json"])
        except json.JSONDecodeError:
            data["variants"] = []
    return data


def init_db_schema() -> None:
    """初始化香氛展示目录表结构（幂等执行）。"""
    conn = get_db_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name_en TEXT NOT NULL,
                name_zh TEXT NOT NULL,
                eyebrow TEXT NOT NULL,
                description TEXT NOT NULL,
                hero_image TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                category_slug TEXT NOT NULL,
                collection TEXT NOT NULL,
                name_en TEXT NOT NULL,
                name_zh TEXT NOT NULL,
                subtitle TEXT NOT NULL,
                scent_family TEXT NOT NULL,
                scent_family_zh TEXT NOT NULL,
                top_note TEXT NOT NULL,
                heart_note TEXT NOT NULL,
                base_note TEXT NOT NULL,
                description TEXT NOT NULL,
                base_price REAL NOT NULL,
                default_size TEXT NOT NULL,
                variants_json TEXT NOT NULL,
                image_url TEXT NOT NULL,
                badge TEXT DEFAULT '',
                is_bestseller INTEGER DEFAULT 0,
                is_intense INTEGER DEFAULT 0,
                allow_engraving INTEGER DEFAULT 1,
                pair_with_slug TEXT DEFAULT '',
                pairing_note TEXT DEFAULT '',
                FOREIGN KEY (category_slug) REFERENCES categories (slug)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def fetch_categories() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM categories ORDER BY sort_order ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_category_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM categories WHERE slug = ?", (slug,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_products(
    category_slug: Optional[str] = None,
    scent_family: Optional[str] = None,
    bestsellers_only: bool = False,
    search_query: Optional[str] = None,
    sort_by: str = "featured",
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """香氛作品展示查询，支持分类过滤、香调筛选、关键词检索与排序。"""
    conn = get_db_connection()
    try:
        clauses = ["1=1"]
        params: List[Any] = []

        if category_slug:
            clauses.append("category_slug = ?")
            params.append(category_slug)
        if scent_family:
            clauses.append("scent_family = ?")
            params.append(scent_family)
        if bestsellers_only:
            clauses.append("is_bestseller = 1")
        if search_query:
            q = f"%{search_query.strip()}%"
            clauses.append(
                "(name_en LIKE ? OR name_zh LIKE ? OR scent_family_zh LIKE ? OR top_note LIKE ? OR heart_note LIKE ? OR base_note LIKE ?)"
            )
            params.extend([q, q, q, q, q, q])

        order_sql = "is_bestseller DESC, id ASC"
        if sort_by == "name_asc":
            order_sql = "name_en ASC"
        elif sort_by == "newest":
            order_sql = "id DESC"

        sql = f"SELECT * FROM products WHERE {' AND '.join(clauses)} ORDER BY {order_sql}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        rows = conn.execute(sql, params).fetchall()
        return [row_to_dict(r) for r in rows if r is not None]
    finally:
        conn.close()


def fetch_product_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM products WHERE slug = ?", (slug,)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()
