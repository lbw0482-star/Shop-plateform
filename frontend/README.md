# 拾光集前端

本目录是会员制购物网站的 React + TypeScript 前端，面向课程设计交付。

## 本地运行

需要 Node.js 18+。复制 `.env.example` 为 `.env` 后安装依赖：

```bash
npm install
npm run dev
```

开发服务器默认运行在 `http://localhost:5173`，`/api` 和 `/uploads` 会代理到 FastAPI 的 `http://127.0.0.1:8001`。浏览器请求使用 `credentials: include`，会员和管理员登录态由后端 HttpOnly Cookie 维护。

## 页面范围

- 会员端：登录、注册、商品浏览和搜索、商品详情、购物车、结算、模拟支付、订单、留言、个人资料。
- 管理端：工作台、商品、订单、会员、留言审核和系统设置。

商品图片使用后端的本地 `uploads` 目录地址。接口错误会显示页面级错误状态，空列表会显示引导操作。
