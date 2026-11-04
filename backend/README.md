# 会员制购物网站后端

这是课程设计版本的 FastAPI 服务。为了便于没有 PostgreSQL 的课堂演示，默认使用 `app.db.Store` 内存仓库；业务接口、Cookie 会话和状态流转与 PostgreSQL/Prisma 方案保持一致。连接数据库时，`prisma/schema.prisma` 是数据模型来源，生成客户端后可通过 `app.repositories.prisma.PrismaRepository` 接入。

## 启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

接口文档：<http://127.0.0.1:8000/docs>。

默认演示管理员为 `admin / Admin123!`。会员注册后使用 `member_session` HttpOnly Cookie；管理员使用独立的 `admin_session` Cookie。两类会话不会互相认证。

## Prisma/PostgreSQL

```bash
cp .env.example .env
prisma generate --schema prisma/schema.prisma
prisma migrate dev --schema prisma/schema.prisma --name init
```

图片上传默认写入 `backend/uploads`，API 返回 `/uploads/<filename>`。课程设计不包含 Docker 或线上部署配置。

## 检查

```bash
python -m compileall -q app seed.py tests
pytest -q
```

