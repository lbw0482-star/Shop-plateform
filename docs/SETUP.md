# 本地环境搭建与启动指南（Shop-platform）

> 适用：macOS + Homebrew。其他系统请替换对应包管理器命令（Windows 建议 WSL2 + apt，或直接使用 PostgreSQL 官方安装包）。
>
> 所有数据库连接信息以 `backend/.env` 为准：`postgresql://shop_user:shop@localhost:5432/shop_db`

## 启动流程总览

```text
① 安装基础工具链（Homebrew / Python 3.12 / Node 18+）        —— 全新机器执行一次
② 安装并启动 PostgreSQL                                       —— 全新机器执行一次
③ 创建数据库用户和数据库（shop_user / shop_db）               —— 全新机器执行一次
④ 后端：虚拟环境 → 依赖 → Prisma 生成 → 迁移 → 种子数据       —— 换机器/首次执行
⑤ 前端：Node 18 → npm install                                 —— 换机器/首次执行
⑥ 日常启动：终端 1 起后端（8001），终端 2 起前端（5173）       —— 每次开发执行
⑦ 验证：API 文档 / 前端首页 / 默认账号登录
```

懒人版：④⑤ 的全部命令已封装为一键脚本，在仓库根目录执行 `./setup_local.sh`（幂等，可重复运行），然后直接跳到第 ⑥ 步。

---

## ① 安装基础工具

| 软件 | 版本要求 | 说明 |
| --- | --- | --- |
| Homebrew | 最新 | macOS 包管理器 |
| Python | **3.12**（推荐） | 后端运行时；`prisma==0.15.0` 已在 3.12 验证通过，新版 Python（3.13/3.15）可能出现依赖不兼容 |
| Node.js | **≥ 18** | 前端 Vite 5 的硬性要求，Node 16 会启动失败 |
| PostgreSQL | ≥ 16（本机使用 18） | 项目数据库 |

```bash
# Homebrew（已安装则跳过）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.12（Homebrew 安装后命令为 python3.12）
brew install python@3.12

# Node 18+（推荐 nvm 管理多版本；也可 brew install node@18）
brew install nvm
mkdir -p ~/.nvm
cat >> ~/.zshrc <<'EOF'
export NVM_DIR="$HOME/.nvm"
source "$(brew --prefix nvm)/nvm.sh"
EOF
source ~/.zshrc
nvm install 18
nvm alias default 18      # 将默认版本切到 18，避免项目误用旧版本
```

验证：

```bash
python3.12 --version    # ≥ 3.12.x
node --version          # ≥ v18
npm --version
```

---

## ② 安装并启动 PostgreSQL

```bash
# 安装（本机示例为 18，装其他大版本同理）
brew install postgresql@18

# 配置命令行（postgresql@18 是 keg-only，bin 需手动加入 PATH）
echo 'export PATH="/opt/homebrew/opt/postgresql@18/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 设为开机自启并立即启动
brew services start postgresql@18

# 验证：应输出 accepting connections
pg_isready -h localhost -p 5432
```

> 停止/重启：`brew services stop postgresql@18` / `brew services restart postgresql@18`；
> 查看状态：`brew services list | grep postgres`

## ③ 创建数据库用户和数据库

用户名/密码/库名与 `backend/.env` 的 `DATABASE_URL` 一一对应，执行一次即可（已存在时命令可安全重复）：

```bash
# 1. 创建登录角色 shop_user（密码 shop），已存在则跳过
psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='shop_user'" | grep -q 1 || \
  psql postgres -c "CREATE ROLE shop_user LOGIN PASSWORD 'shop';"

# 2. 创建数据库 shop_db，属主为 shop_user，已存在则跳过
psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='shop_db'" | grep -q 1 || \
  createdb -O shop_user shop_db

# 3. 用与后端相同的连接方式验证（应打印成功）
PGPASSWORD=shop psql -h localhost -p 5432 -U shop_user -d shop_db -c "SELECT 'DB OK';"
```

> 若第 3 步报密码错误：`psql postgres -c "ALTER ROLE shop_user WITH LOGIN PASSWORD 'shop';"` 后重试。

---

## ④ 后端初始化（FastAPI + Prisma）

```bash
cd backend

# 1. 创建虚拟环境（务必用 python3.12）
python3.12 -m venv .venv
source .venv/bin/activate

# 2. 安装 Python 依赖（fastapi、prisma、pwdlib 等，见 requirements.txt）
pip install -U pip
pip install -r requirements.txt

# 3. 配置环境变量（已有 .env 则跳过）
cp -n .env.example .env
#   DATABASE_URL=postgresql://shop_user:shop@localhost:5432/shop_db

# 4. 生成 Prisma Client（首次会下载查询引擎，需联网）
prisma generate --schema prisma/schema.prisma

# 5. 执行数据库迁移（建表；首次也可用 prisma migrate dev --name init）
prisma migrate deploy --schema prisma/schema.prisma

# 6. 写入种子数据（等级/角色/管理员/分类/商品/演示会员，幂等可重复执行）
python scripts/seed.py

# 7. 启动后端开发服务
uvicorn app.main:app --reload --port 8001
```

启动成功标志：终端出现 `Uvicorn running on http://127.0.0.1:8001`，打开 <http://127.0.0.1:8001/docs> 能看到 Swagger 文档。

## ⑤ 前端初始化（React + Vite）

```bash
# 确认 Node ≥ 18（本机 nvm 默认版本过旧时必须先切换）
node --version                      # < v18 则执行：nvm use 18

cd ../frontend                      # 即仓库的 frontend/ 目录

# 1. 安装依赖（antd、react-router、react-query 等，见 package.json）
npm install

# 2. 配置环境变量（已有 .env 则跳过）
cp -n .env.example .env             # VITE_API_BASE_URL=/api/v1

# 3. 启动前端开发服务
npm run dev
```

启动成功标志：终端输出 `Local: http://localhost:5173/`。`/api` 与 `/uploads` 由 Vite 自动代理到 `127.0.0.1:8001`，无需额外配置。

---

## ⑥ 日常启动流程（每次开发）

保持 PostgreSQL 由 brew services 托管即可，两个终端分别执行：

```bash
# 终端 1 —— 后端
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8001

# 终端 2 —— 前端
cd frontend && nvm use 18 2>/dev/null
npm run dev
```

访问入口：

| 入口 | 地址 |
| --- | --- |
| 前端（会员端 + 管理端） | <http://127.0.0.1:5173> |
| 后端 API 文档（Swagger） | <http://127.0.0.1:8001/docs> |
| 商品列表冒烟接口 | <http://127.0.0.1:8001/api/v1/products> |

## ⑦ 验证与默认账号

命令行冒烟：

```bash
curl -s http://127.0.0.1:8001/api/v1/products | head -c 200   # 返回商品 JSON 即正常
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5173 # 200 即前端正常
```

种子数据内置账号（课程演示用，首次登录后请修改密码）：

| 角色 | 用户名 | 密码 | 登录位置 |
| --- | --- | --- | --- |
| 超级管理员 | `admin` | `Admin123!` | 前端管理端登录页 |
| 普通管理员 | `operator` | `Oper12345!` | 前端管理端登录页 |
| 普通会员 | 注册页面自行创建 | —— | 前端会员端登录页 |

## 附：质量自检命令

```bash
cd backend && .venv/bin/python -m compileall -q app scripts   # Python 语法检查
cd backend && .venv/bin/python -m pytest -q                   # 后端接口测试
cd backend && .venv/bin/prisma validate --schema prisma/schema.prisma   # 数据模型校验
cd frontend && npm run build                                  # 前端类型检查 + 构建
```

## 常见问题排查

| 现象 | 原因与处理 |
| --- | --- |
| `psql: error: FATAL: role "libowen" does not exist` | 未显式指定目标库，改用 `psql postgres`（brew 初始化的默认超级用户是本机用户名） |
| Prisma 报 `Can't reach database server` | PostgreSQL 未启动：`brew services start postgresql@18`，再 `pg_isready -h localhost` 确认 |
| 连接报密码认证失败 | 重置角色密码：`psql postgres -c "ALTER ROLE shop_user WITH LOGIN PASSWORD 'shop';"`，并核对 `backend/.env` |
| 前端启动报 `crypto.hash is not a function` / 引擎不兼容 | Node 版本低于 18：`nvm use 18`（建议 `nvm alias default 18`） |
| `pip install` 或 `prisma generate` 报错 | Python 版本过新，用 3.12 重建虚拟环境：`rm -rf .venv && python3.12 -m venv .venv` |
| 端口被占用（8001/5173） | `lsof -i :8001` 找到进程后 `kill <pid>`，或换端口：`uvicorn app.main:app --port 8002` |
| 商品图片显示裂图 | `backend/uploads/` 下无种子图片文件（种子仅存相对路径占位），属课程演示预期行为，可通过管理端上传真实图片 |
| `pip install` 找不到 `prisma==0.15.0` | 网络问题，配置 PyPI 镜像后重试：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
