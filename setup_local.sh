#!/usr/bin/env bash
# 会员制购物网站 —— 本地环境一键初始化脚本（幂等，可重复执行）
#
# 职责：检查工具链 → 创建 PostgreSQL 角色/数据库 → 后端依赖/Prisma 生成/迁移/种子 → 前端依赖
# 不做：启动前后端服务（启动命令见 docs/SETUP.md 第 ⑥ 步）
#
# 用法：在仓库根目录执行  ./setup_local.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# 与 backend/.env 的 DATABASE_URL 保持一致
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="shop_user"
DB_PASS="shop"
DB_NAME="shop_db"

info() { printf '\033[1;32m[OK]\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$1"; }
die()  { printf '\033[1;31m[FAIL]\033[0m %s\n' "$1" >&2; exit 1; }

echo "==> 项目根目录: $ROOT_DIR"

# ---------- 1. 工具链检查 ----------
need_cmd() { command -v "$1" >/dev/null 2>&1 || { warn "缺少命令 $1，请先安装（见 docs/SETUP.md 第①步）"; return 1; }; }

MISSING=0
need_cmd brew || MISSING=1
need_cmd psql || MISSING=1
need_cmd python3.12 || { warn "  macOS 安装：brew install python@3.12"; MISSING=1; }
need_cmd npm || MISSING=1
[ "$MISSING" -eq 0 ] || die "请先补齐上述工具再重新运行本脚本"

# ---------- 2. PostgreSQL 状态检查 ----------
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
  warn "PostgreSQL 未知状态，尝试启动 brew 服务..."
  brew services start postgresql@18 || die "PostgreSQL 启动失败，请手动检查：brew services list"
  sleep 2
fi
pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1 || die "PostgreSQL 未就绪 ($DB_HOST:$DB_PORT)"
info "PostgreSQL 已就绪 ($DB_HOST:$DB_PORT)"

# ---------- 3. 创建角色与数据库（幂等） ----------
if psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  info "数据库角色 $DB_USER 已存在，跳过创建"
else
  psql postgres -c "CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASS';" >/dev/null
  info "已创建数据库角色 $DB_USER"
fi

if psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
  info "数据库 $DB_NAME 已存在，跳过创建"
else
  createdb -O "$DB_USER" "$DB_NAME"
  info "已创建数据库 $DB_NAME（属主 $DB_USER）"
fi

if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1" >/dev/null 2>&1; then
  info "连接验证通过：postgresql://$DB_USER:***@$DB_HOST:$DB_PORT/$DB_NAME"
else
  die "TCP 连接失败，请核对密码：psql postgres -c \"ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';\""
fi

# ---------- 4. 后端初始化 ----------
echo "==> 后端（FastAPI + Prisma）"
cd "$BACKEND_DIR"

if [ ! -d .venv ]; then
  python3.12 -m venv .venv
  info "已创建虚拟环境 .venv (Python $(python3.12 --version | awk '{print $2}'))"
else
  info "虚拟环境 .venv 已存在，跳过创建"
fi
PY_BIN=".venv/bin"
"$PY_BIN/pip" install -q -U pip
"$PY_BIN/pip" install -q -r requirements.txt
info "Python 依赖安装完成（requirements.txt）"

if [ ! -f .env ]; then
  cp .env.example .env
  info "已根据 .env.example 生成 backend/.env"
else
  info "backend/.env 已存在，保持不变"
fi

"$PY_BIN/prisma" generate --schema prisma/schema.prisma >/dev/null && info "Prisma Client 生成完成"
"$PY_BIN/prisma" migrate deploy --schema prisma/schema.prisma >/dev/null && info "数据库迁移已应用（migrate deploy）"
"$PY_BIN/python" scripts/seed.py >/dev/null && info "种子数据写入完成（admin / Admin123!）"

# ---------- 5. 前端初始化 ----------
echo "==> 前端（React + Vite）"
NODE_MAJOR="$(node -e 'process.stdout.write(process.versions.node.split(".")[0])')"
if [ "$NODE_MAJOR" -lt 18 ]; then
  warn "当前 Node v$NODE_MAJOR (<18)，Vite 5 无法运行。请执行：nvm install 18 && nvm use 18 后重跑本脚本"
  warn "已跳过前端 npm install"
else
  cd "$FRONTEND_DIR"
  if [ ! -f .env ]; then cp .env.example .env; info "已生成 frontend/.env"; fi
  npm install --no-fund --no-audit
  info "前端依赖安装完成"
  cd "$ROOT_DIR"
fi

# ---------- 6. 完成 ----------
cat <<'EOF'

==================== 初始化完成，日常启动方式 ====================

  # 终端 1 —— 启动后端 (http://127.0.0.1:8001/docs)
  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001

  # 终端 2 —— 启动前端 (http://127.0.0.1:5173)
  cd frontend && npm run dev

  管理端默认账号：admin / Admin123!
  详细文档：docs/SETUP.md
=================================================================
EOF
