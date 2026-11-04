# 实现说明

## 已落地的技术选择

| 领域 | 实现 |
| --- | --- |
| 前端 | React、TypeScript、Vite、React Router、TanStack Query、Ant Design |
| 后端 | FastAPI、Pydantic、服务层与 Repository 分层 |
| 数据模型 | Prisma Schema，目标数据库 PostgreSQL |
| 登录态 | 服务端 `auth_session` + HttpOnly Cookie |
| 文件 | 本地 `backend/uploads`，数据库保存相对地址 |
| 交付方式 | 本地课程设计运行，不配置 Docker 或线上部署 |

## 后端模块

- `app/api/v1`：认证、商品、购物车、订单、留言和后台接口。
- `app/services`：订单状态、库存、积分、权限等业务规则。
- `app/repositories`：统一封装 Prisma Client 访问。
- `app/core`：配置、会话 Cookie、统一异常和响应模型。
- `prisma/schema.prisma`：业务表、会话表和积分流水表。

## 订单一致性

订单创建时服务层会重新读取并校验购物车商品，按商品编号排序后锁定库存，创建订单快照并扣减库存。支付、取消和退款都校验前置状态，并使用请求幂等键避免重复处理。

## 与原 SRS 的对应关系

原 SRS 中的 JSP、Servlet、JDBC 和 SQL Server 2000 只作为业务需求来源；实现层替换为 React、FastAPI、Prisma Schema 和 PostgreSQL 类型。状态代码、权限边界、订单快照、积分等级和留言审核规则保持一致。
