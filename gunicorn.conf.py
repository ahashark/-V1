"""
Gunicorn 生产环境配置文件 (兼容 Gunicorn 20.x ~ 27.x+)
禁用 Gunicorn 25.1+/27.x 默认开启的 Control Socket，避免 www-data 用户无权写入 /var/www/.gunicorn 报错。
"""
workers = 2
threads = 2
timeout = 60
accesslog = "-"
errorlog = "-"
control_socket_disable = True
