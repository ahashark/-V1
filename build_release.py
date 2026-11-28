"""
Ubuntu 可发布版本编译与打包工具 (Release Compiler & Tarball Builder)

功能：
1. 调用 build_static_site() 完整渲染 18 个静态页面并生成最新 catalog.json；
2. 校验全项目 Python 字节码语法（py_compile）；
3. 预生成干净的只读展示 SQLite 数据库（atelier_fragrance.db）；
4. 强制将所有 Linux 部署脚本与配置文件规范化为 Unix LF (\n) 换行符并设置 0755/0644 权限；
5. 输出标准发布压缩包：dist/atelier-fragrance-ubuntu-release.tar.gz
"""
import io
import os
import py_compile
import shutil
import sqlite3
import tarfile
import tempfile
import time
from pathlib import Path

from build_static import build_static_site
from config import BASE_DIR
from core.seed import CATEGORIES_SEED, PRODUCTS_SEED

DIST_DIR = BASE_DIR / "dist"
ARCHIVE_NAME = "atelier-fragrance-ubuntu-release.tar.gz"
ROOT_PREFIX = "atelier-fragrance-release"

PROD_REQUIREMENTS = """Flask>=3.0.0
gunicorn>=21.2.0
"""

DEPLOY_README = """# MAISON L'ATELIER LONDON — Ubuntu 生产发布包部署说明

目标服务器：`192.168.118.128`（Ubuntu 20.04 / 22.04 / 24.04 均兼容）

## 方式一：在 Windows 本机一键上传并远程部署（推荐）

在项目根目录打开 PowerShell 执行（将 `ubuntu` 替换为您的虚拟机 SSH 用户名，如 `root`）：

```powershell
.\\deploy\\upload_and_deploy.ps1 -ServerIp 192.168.118.128 -User ubuntu
```

## 方式二：手动上传压缩包至 Ubuntu 虚拟机部署

1. 将 `atelier-fragrance-ubuntu-release.tar.gz` 上传至 Ubuntu 虚拟机（例如 `/tmp/`）：
   ```bash
   scp dist/atelier-fragrance-ubuntu-release.tar.gz ubuntu@192.168.118.128:/tmp/
   ```

2. SSH 登录至 `192.168.118.128`，解压并执行一键部署脚本：
   ```bash
   cd /tmp
   tar -xzf atelier-fragrance-ubuntu-release.tar.gz
   cd atelier-fragrance-release
   sudo bash deploy_ubuntu.sh
   ```

## 可选部署参数

- **默认全栈生产模式（Nginx + Gunicorn + Systemd 常驻服务，80 端口）**：
  ```bash
  sudo bash deploy_ubuntu.sh --host 192.168.118.128 --port 80 --mode full
  ```
- **纯静态极速模式（仅使用 Nginx 托管预编译静态包 `site/`，无需安装 pip 依赖，离线可用）**：
  ```bash
  sudo bash deploy_ubuntu.sh --host 192.168.118.128 --port 80 --mode static
  ```
- **更换监听端口（如 80 端口已被占用，改为 8080）**：
  ```bash
  sudo bash deploy_ubuntu.sh --host 192.168.118.128 --port 8080
  ```

部署完成后，局域网电脑与手机（连接同一路由/网段）可直接访问：
`http://192.168.118.128`
"""


def build_clean_sqlite(db_file: Path) -> None:
    """在临时目录生成一份干净、预写入全部种子数据的 SQLite 数据库。"""
    if db_file.exists():
        db_file.unlink()
    conn = sqlite3.connect(str(db_file))
    try:
        conn.executescript(
            """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name_en TEXT NOT NULL,
                name_zh TEXT NOT NULL,
                eyebrow TEXT NOT NULL,
                description TEXT NOT NULL,
                hero_image TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE products (
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
        for cat in CATEGORIES_SEED:
            conn.execute(
                """
                INSERT INTO categories (slug, name_en, name_zh, eyebrow, description, hero_image, sort_order)
                VALUES (:slug, :name_en, :name_zh, :eyebrow, :description, :hero_image, :sort_order)
                """,
                cat,
            )
        for prod in PRODUCTS_SEED:
            conn.execute(
                """
                INSERT INTO products (
                    slug, category_slug, collection, name_en, name_zh, subtitle,
                    scent_family, scent_family_zh, top_note, heart_note, base_note,
                    description, base_price, default_size, variants_json, image_url,
                    badge, is_bestseller, is_intense, allow_engraving, pair_with_slug, pairing_note
                ) VALUES (
                    :slug, :category_slug, :collection, :name_en, :name_zh, :subtitle,
                    :scent_family, :scent_family_zh, :top_note, :heart_note, :base_note,
                    :description, :base_price, :default_size, :variants_json, :image_url,
                    :badge, :is_bestseller, :is_intense, :allow_engraving, :pair_with_slug, :pairing_note
                )
                """,
                prod,
            )
        conn.commit()
    finally:
        conn.close()


def add_bytes_to_tar(tf: tarfile.TarFile, arcname: str, data: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name=arcname.replace("\\", "/"))
    info.size = len(data)
    info.mtime = int(time.time())
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    tf.addfile(info, io.BytesIO(data))


def add_file_to_tar(tf: tarfile.TarFile, src_path: Path, arcname: str, executable: bool = False) -> None:
    text_exts = {".py", ".sh", ".html", ".css", ".js", ".json", ".svg", ".txt", ".md", ".conf", ".service"}
    if src_path.suffix.lower() in text_exts:
        # 统一转换为 UTF-8 Unix LF (\n)，杜绝 Linux 下 CRLF 报错
        content = src_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        data = content.encode("utf-8")
    else:
        data = src_path.read_bytes()
    add_bytes_to_tar(tf, arcname, data, mode=0o755 if executable else 0o644)


def add_dir_tree_to_tar(tf: tarfile.TarFile, src_dir: Path, arc_prefix: str, exclude_names=None) -> int:
    exclude = set(exclude_names or [])
    count = 0
    for path in sorted(src_dir.rglob("*")):
        if any(part in exclude or part == "__pycache__" or part.endswith(".pyc") for part in path.parts):
            continue
        if path.is_file():
            rel = path.relative_to(src_dir).as_posix()
            add_file_to_tar(tf, path, f"{arc_prefix}/{rel}", executable=(path.suffix == ".sh"))
            count += 1
    return count


def build_release() -> Path:
    print("[1/4] 编译全站静态页面与前端数据集 (docs/)...")
    build_static_site()

    print("[2/4] 校验全项目 Python 源码字节码...")
    py_files = [
        BASE_DIR / "app.py",
        BASE_DIR / "wsgi.py",
        BASE_DIR / "config.py",
        BASE_DIR / "gunicorn.conf.py",
        *sorted((BASE_DIR / "core").glob("*.py")),
        *sorted((BASE_DIR / "routes").glob("*.py")),
    ]
    for pf in py_files:
        py_compile.compile(str(pf), doraise=True)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DIST_DIR / ARCHIVE_NAME

    print(f"[3/4] 组装 Ubuntu 发布压缩包 -> {archive_path} ...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "atelier_fragrance.db"
        build_clean_sqlite(tmp_db)

        file_count = 0
        with tarfile.open(archive_path, "w:gz") as tf:
            # 1) 核心 Python 应用代码
            for top_py in ["app.py", "wsgi.py", "config.py", "gunicorn.conf.py"]:
                add_file_to_tar(tf, BASE_DIR / top_py, f"{ROOT_PREFIX}/{top_py}")
                file_count += 1

            file_count += add_dir_tree_to_tar(tf, BASE_DIR / "core", f"{ROOT_PREFIX}/core")
            file_count += add_dir_tree_to_tar(tf, BASE_DIR / "routes", f"{ROOT_PREFIX}/routes")
            file_count += add_dir_tree_to_tar(tf, BASE_DIR / "templates", f"{ROOT_PREFIX}/templates")
            file_count += add_dir_tree_to_tar(tf, BASE_DIR / "static", f"{ROOT_PREFIX}/static")

            # 2) 预初始化 SQLite 商品数据库
            add_file_to_tar(tf, tmp_db, f"{ROOT_PREFIX}/instance/atelier_fragrance.db")
            file_count += 1

            # 3) 预编译纯静态版本 site/（供 --mode static 零依赖直接部署）
            file_count += add_dir_tree_to_tar(
                tf,
                BASE_DIR / "docs",
                f"{ROOT_PREFIX}/site",
                exclude_names={"CNAME", ".nojekyll"},
            )

            # 4) 生产依赖清单、Ubuntu 部署脚本与说明文档
            add_bytes_to_tar(
                tf,
                f"{ROOT_PREFIX}/requirements-prod.txt",
                PROD_REQUIREMENTS.replace("\r\n", "\n").encode("utf-8"),
            )
            add_file_to_tar(
                tf,
                BASE_DIR / "deploy" / "deploy_ubuntu.sh",
                f"{ROOT_PREFIX}/deploy_ubuntu.sh",
                executable=True,
            )
            add_bytes_to_tar(
                tf,
                f"{ROOT_PREFIX}/DEPLOY_README.md",
                DEPLOY_README.replace("\r\n", "\n").encode("utf-8"),
            )
            file_count += 3

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"[4/4] 发布包构建完成！共打包 {file_count} 个文件，体积 {size_mb:.2f} MB")
    print(f"[OK] 产物路径: {archive_path}")
    return archive_path


if __name__ == "__main__":
    build_release()
