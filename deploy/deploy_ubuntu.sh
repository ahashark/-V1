#!/usr/bin/env bash
# ==============================================================================
# MAISON L'ATELIER LONDON — Ubuntu 生产环境一键部署脚本
# 默认目标主机: 192.168.118.128 | 默认监听端口: 80
#
# 支持两种部署模式:
#   1. full   (默认): Nginx 反向代理 + Gunicorn + Systemd 常驻 Flask 服务 + SQLite
#                     (若系统 Nginx 配置异常未监听端口，自动回退为 Gunicorn 直连监听)
#   2. static (轻量): 纯 Nginx 高性能托管预编译静态站点
# ==============================================================================

set -euo pipefail

SERVER_HOST="192.168.118.128"
LISTEN_PORT="80"
BACKEND_PORT="8000"
DEPLOY_MODE="full"
APP_DIR="/opt/atelier-fragrance"
SERVICE_NAME="atelier-fragrance"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      SERVER_HOST="$2"
      shift 2
      ;;
    --port)
      LISTEN_PORT="$2"
      shift 2
      ;;
    --backend-port)
      BACKEND_PORT="$2"
      shift 2
      ;;
    --mode)
      DEPLOY_MODE="$2"
      shift 2
      ;;
    -h|--help)
      echo "用法: sudo bash $0 [--mode full|static] [--host 192.168.118.128] [--port 80] [--backend-port 8000]"
      exit 0
      ;;
    *)
      echo "[ERROR] 未知参数: $1"
      exit 1
      ;;
  esac
done

if [[ "$DEPLOY_MODE" != "full" && "$DEPLOY_MODE" != "static" ]]; then
  echo "[ERROR] --mode 仅支持 full 或 static，当前值: $DEPLOY_MODE"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "[INFO] 正在请求 sudo 管理员权限以执行系统服务配置..."
  exec sudo bash "$0" "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/wsgi.py" || -d "${SCRIPT_DIR}/site" ]]; then
  PKG_ROOT="${SCRIPT_DIR}"
elif [[ -f "${SCRIPT_DIR}/../wsgi.py" ]]; then
  PKG_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
  echo "[ERROR] 未找到发布包目录结构 (wsgi.py 或 site/)，请在解压后的发布包目录内执行本脚本。"
  exit 1
fi

PORT_SUFFIX=""
if [[ "${LISTEN_PORT}" != "80" ]]; then
  PORT_SUFFIX=":${LISTEN_PORT}"
fi
PUBLIC_URL="http://${SERVER_HOST}${PORT_SUFFIX}"

probe_http() {
  local url="$1"
  local code="000"
  for _ in {1..12}; do
    code="$(curl --noproxy '*' -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" || true)"
    if [[ "$code" == "200" ]]; then
      echo "200"
      return 0
    fi
    sleep 0.5
  done
  echo "${code:-000}"
  return 1
}

write_systemd_service() {
  local bind_addr="$1"
  cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Maison L'Atelier London Showcase Web Service (Gunicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}
Environment="HOME=${APP_DIR}"
Environment="PATH=${APP_DIR}/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="SITE_URL=${PUBLIC_URL}"
Environment="CUSTOM_DOMAIN=${SERVER_HOST}"
Environment="ATELIER_DB_PATH=${APP_DIR}/instance/atelier_fragrance.db"
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
ExecStart=${APP_DIR}/.venv/bin/gunicorn -c ${APP_DIR}/gunicorn.conf.py --bind ${bind_addr} wsgi:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}.service"
  systemctl restart "${SERVICE_NAME}.service"
}

echo "=================================================================="
echo "  MAISON L'ATELIER LONDON — Ubuntu 自动化部署"
echo "  部署模式 : ${DEPLOY_MODE}"
echo "  访问地址 : ${PUBLIC_URL}"
echo "  安装目录 : ${APP_DIR}"
echo "=================================================================="

# 1. 安装基础系统依赖
echo "[1/5] 检查并安装 Ubuntu 系统组件..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -qq
if [[ "${DEPLOY_MODE}" == "full" ]]; then
  apt-get install -y -qq nginx python3 python3-venv python3-pip curl iproute2
else
  apt-get install -y -qq nginx curl iproute2
fi

# 2. 部署应用文件
echo "[2/5] 同步发布版本文件至 ${APP_DIR}..."
mkdir -p "${APP_DIR}"

if [[ "${DEPLOY_MODE}" == "full" ]]; then
  for item in app.py wsgi.py config.py gunicorn.conf.py requirements-prod.txt core routes templates static instance; do
    if [[ -e "${PKG_ROOT}/${item}" ]]; then
      rm -rf "${APP_DIR:?}/${item}"
      cp -a "${PKG_ROOT}/${item}" "${APP_DIR}/"
    fi
  done

  # 兜底生成 gunicorn.conf.py（确保 Gunicorn 25.1+/27.x 禁用默认 control socket）
  if [[ ! -f "${APP_DIR}/gunicorn.conf.py" ]]; then
    cat > "${APP_DIR}/gunicorn.conf.py" <<'EOF'
workers = 2
threads = 2
timeout = 60
accesslog = "-"
errorlog = "-"
control_socket_disable = True
EOF
  fi

  echo "[3/5] 构建 Python 虚拟环境并安装生产依赖 (Flask + Gunicorn)..."
  if [[ ! -x "${APP_DIR}/.venv/bin/python" ]]; then
    python3 -m venv "${APP_DIR}/.venv"
  fi

  "${APP_DIR}/.venv/bin/pip" install --upgrade pip -q \
    -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn || true

  if ! "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements-prod.txt" -q \
    -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn; then
    echo "[WARN] 清华镜像源连接受限，正在尝试官方 PyPI 源..."
    "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements-prod.txt"
  fi

  mkdir -p "${APP_DIR}/instance"
  rm -f "${APP_DIR}/gunicorn.ctl"
  SITE_URL="${PUBLIC_URL}" CUSTOM_DOMAIN="${SERVER_HOST}" \
    "${APP_DIR}/.venv/bin/python" -c "from app import create_app; create_app()"
  chown -R www-data:www-data "${APP_DIR}"
  chmod -R 755 "${APP_DIR}"

  echo "[4/5] 配置 Systemd 守护进程 (${SERVICE_NAME}.service)..."
  write_systemd_service "127.0.0.1:${BACKEND_PORT}"

  BACKEND_CODE="$(probe_http "http://127.0.0.1:${BACKEND_PORT}/" || true)"
  if [[ "${BACKEND_CODE}" != "200" ]]; then
    echo "[ERROR] Gunicorn 后端启动失败 (127.0.0.1:${BACKEND_PORT} -> HTTP ${BACKEND_CODE})"
    systemctl status "${SERVICE_NAME}.service" --no-pager -l || true
    journalctl -u "${SERVICE_NAME}.service" -n 30 --no-pager || true
    exit 1
  fi
  echo "[INFO] Gunicorn 后端服务已就绪 (127.0.0.1:${BACKEND_PORT} -> HTTP 200)"
else
  if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
    systemctl stop "${SERVICE_NAME}.service" || true
    systemctl disable "${SERVICE_NAME}.service" || true
  fi

  SRC_STATIC="${PKG_ROOT}/site"
  if [[ ! -d "${SRC_STATIC}" && -d "${PKG_ROOT}/docs" ]]; then
    SRC_STATIC="${PKG_ROOT}/docs"
  fi
  if [[ ! -d "${SRC_STATIC}" ]]; then
    echo "[ERROR] 未找到预编译静态目录 site/ 或 docs/。"
    exit 1
  fi

  echo "[3/5] 部署预编译静态站点至 ${APP_DIR}/site..."
  rm -rf "${APP_DIR}/site"
  cp -a "${SRC_STATIC}" "${APP_DIR}/site"
  chown -R www-data:www-data "${APP_DIR}"
  chmod -R 755 "${APP_DIR}"
  echo "[4/5] 纯静态模式跳过 Python 守护进程配置..."
fi

# 5. 配置 Nginx 站点（自动兼容 GMSSH 面板 Nginx、标准 Ubuntu sites-enabled 及 conf.d 目录结构）
echo "[5/5] 配置对外 Web 端口监听 (0.0.0.0:${LISTEN_PORT})..."

DEFAULT_SERVER_FLAG=""
if [[ "${LISTEN_PORT}" == "80" ]]; then
  rm -f /etc/nginx/sites-enabled/default
  if [[ -f /etc/nginx/conf.d/default.conf ]]; then
    mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.disabled
  fi
  DEFAULT_SERVER_FLAG=" default_server"
fi

# 清理旧配置避免重复冲突
rm -f "/etc/nginx/sites-enabled/${SERVICE_NAME}.conf" \
      "/etc/nginx/conf.d/${SERVICE_NAME}.conf" \
      "/.__gmssh/data/plugin/xz/site/data/nginx/conf/vhost/${SERVICE_NAME}.conf"

NGINX_TEST_CMD=(nginx -t)
USE_SYMLINK=0

if [[ -x "/opt/gm/nginx/sbin/nginx" && -f "/opt/gm/nginx/conf/nginx.conf" ]]; then
  GM_VHOST_DIR="/.__gmssh/data/plugin/xz/site/data/nginx/conf/vhost"
  mkdir -p "${GM_VHOST_DIR}"
  NGINX_TARGET="${GM_VHOST_DIR}/${SERVICE_NAME}.conf"
  NGINX_TEST_CMD=(/opt/gm/nginx/sbin/nginx -t -p /opt/gm/nginx/ -c /opt/gm/nginx/conf/nginx.conf)
  echo "[INFO] 检测到 GMSSH 面板 Nginx，写入站点配置 -> ${NGINX_TARGET}"
elif grep -Eq '^[[:space:]]*include[[:space:]]+/etc/nginx/sites-enabled/' /etc/nginx/nginx.conf 2>/dev/null; then
  mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
  NGINX_TARGET="/etc/nginx/sites-available/${SERVICE_NAME}.conf"
  USE_SYMLINK=1
else
  mkdir -p /etc/nginx/conf.d
  NGINX_TARGET="/etc/nginx/conf.d/${SERVICE_NAME}.conf"
fi

if [[ "${DEPLOY_MODE}" == "full" ]]; then
  cat > "${NGINX_TARGET}" <<EOF
# atelier-fragrance managed vhost
server {
    listen 0.0.0.0:${LISTEN_PORT}${DEFAULT_SERVER_FLAG};
    server_name ${SERVER_HOST} sxy.ink _;

    charset utf-8;
    client_max_body_size 10M;

    location /static/ {
        alias ${APP_DIR}/static/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
EOF
else
  cat > "${NGINX_TARGET}" <<EOF
# atelier-fragrance managed vhost
server {
    listen 0.0.0.0:${LISTEN_PORT}${DEFAULT_SERVER_FLAG};
    server_name ${SERVER_HOST} sxy.ink _;

    root ${APP_DIR}/site;
    index index.html;
    charset utf-8;

    error_page 404 /404.html;

    location /static/ {
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        try_files \$uri \$uri/ /404.html;
    }
}
EOF
fi

if [[ "${USE_SYMLINK}" == "1" ]]; then
  ln -sf "${NGINX_TARGET}" "/etc/nginx/sites-enabled/${SERVICE_NAME}.conf"
fi

# 还原被禁用或遮蔽的 nginx 服务并启动
if [[ -f /etc/default/nginx ]]; then
  sed -i 's/^START=no/START=yes/g' /etc/default/nginx || true
fi
systemctl unmask nginx >/dev/null 2>&1 || true

NGINX_OK=0
if "${NGINX_TEST_CMD[@]}"; then
  systemctl enable nginx >/dev/null 2>&1 || true
  systemctl restart nginx || true
  HTTP_CODE="$(probe_http "http://127.0.0.1:${LISTEN_PORT}/" || true)"
  if [[ "${HTTP_CODE}" == "200" ]]; then
    NGINX_OK=1
  fi
fi

# 自愈兜底：若系统 Nginx 因历史自定义配置未能正常监听目标端口，在 full 模式下切换为 Gunicorn 直接监听对外端口
if [[ "${NGINX_OK}" != "1" && "${DEPLOY_MODE}" == "full" ]]; then
  echo "[WARN] 系统 Nginx 未监听 ${LISTEN_PORT} 端口，自动切换为 Gunicorn 直接绑定 0.0.0.0:${LISTEN_PORT}..."
  systemctl stop nginx >/dev/null 2>&1 || true
  pkill -f "nginx: master" >/dev/null 2>&1 || true
  write_systemd_service "0.0.0.0:${LISTEN_PORT}"
  HTTP_CODE="$(probe_http "http://127.0.0.1:${LISTEN_PORT}/" || true)"
fi

# 放行 UFW 防火墙
if command -v ufw >/dev/null 2>&1; then
  if ufw status | grep -Eq "Status: active|状态： 激活"; then
    ufw allow "${LISTEN_PORT}/tcp" >/dev/null 2>&1 || true
    echo "[INFO] 已在 UFW 防火墙放行端口 ${LISTEN_PORT}/tcp"
  fi
fi

if [[ "${HTTP_CODE:-000}" != "200" ]]; then
  echo "[ERROR] 部署后自检异常，HTTP 状态码: ${HTTP_CODE:-000}"
  echo "--- 当前端口监听情况 ---"
  ss -tlnp | grep -E ":${LISTEN_PORT}|:${BACKEND_PORT}" || true
  echo "--- Nginx 状态 ---"
  systemctl status nginx --no-pager -l || true
  if [[ "${DEPLOY_MODE}" == "full" ]]; then
    echo "--- Gunicorn 状态 ---"
    systemctl status "${SERVICE_NAME}.service" --no-pager -l || true
  fi
  exit 1
fi

DETECTED_IPS="$(hostname -I 2>/dev/null | xargs || echo "${SERVER_HOST}")"
echo ""
echo "=================================================================="
echo "  [OK] 部署成功！站点已启动并通过本机与端口自检 (HTTP 200)"
echo "  监听状态: $(ss -tlnp | grep ":${LISTEN_PORT} " | head -n 1 || echo "0.0.0.0:${LISTEN_PORT}")"
echo "  本机网卡IP: ${DETECTED_IPS}"
echo "  访问地址  : ${PUBLIC_URL}"
echo "------------------------------------------------------------------"
if [[ "${DEPLOY_MODE}" == "full" ]]; then
  echo "  查看后端状态: sudo systemctl status ${SERVICE_NAME} -l"
  echo "  查看运行日志: sudo journalctl -u ${SERVICE_NAME} -f"
fi
echo "=================================================================="
