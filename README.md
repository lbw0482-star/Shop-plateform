# 会员制购物网站

这是根据 `docs/SRS_MemberShoppingWebsite.md` 实现的课程设计项目，采用 React + TypeScript、FastAPI、Prisma Schema 和 PostgreSQL 的前后端分离结构。

## 目录

```text
backend/    FastAPI 后端、Prisma 数据模型、种子数据
frontend/   React + Vite 前端（会员端和管理端）
docs/       需求规格说明书和实现说明
```

## 本地运行

完整的环境依赖安装、PostgreSQL 数据库本地化创建和首次初始化步骤，见 **[docs/SETUP.md](docs/SETUP.md)**；也可在仓库根目录执行一键初始化脚本（幂等）：

```bash
./setup_local.sh
```

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 将 DATABASE_URL 改为本机 PostgreSQL 连接串
prisma generate --schema prisma/schema.prisma
prisma migrate deploy --schema prisma/schema.prisma
python scripts/seed.py
uvicorn app.main:app --reload --port 8001
```

后端 API 文档：<http://127.0.0.1:8001/docs>

### 前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

前端默认访问 <http://127.0.0.1:5173>，通过 Vite 代理访问后端 `/api`。

## 课程设计默认账号

种子脚本会创建一个超级管理员：

```text
用户名：admin
密码：Admin123!
```

首次登录后应立即修改密码。生产环境不要使用该默认账号和密码。

## 设计约定

- 登录态保存在服务端 `auth_session` 表中，浏览器只保存 `HttpOnly` Cookie。
- 会员和管理员使用不同 Cookie 名称和会话类型。
- 商品图片在后端 `uploads/` 目录保存，数据库只保存相对路径。
- 订单创建、库存扣减、积分结算在 Service 层执行，并通过事务和幂等键保护。
- 本项目面向课程设计和本地演示，不包含真实支付、物流、短信或对象存储部署。

## 检查命令

```bash
cd backend && python -m compileall app scripts
cd frontend && npm run build
```
