"""
生产环境 WSGI 启动入口 (Gunicorn / uWSGI Production Entrypoint)
示例启动命令：gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:app
"""
from app import create_app

app = create_app()
