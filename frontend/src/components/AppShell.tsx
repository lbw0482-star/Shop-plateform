import { ShoppingBag, LayoutDashboard, MessageSquareText, PackageCheck, UserRound, LogOut, ShoppingCart } from 'lucide-react'
import { Avatar, Badge, Button, Layout, Menu, Space, Typography } from 'antd'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { useCurrentUser } from '../App'

const { Header, Sider, Content } = Layout

export default function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const client = useQueryClient()
  const { data: user } = useCurrentUser()
  const menuItems = [
    { key: '/member/home', icon: <LayoutDashboard size={17} />, label: <Link to="/member/home">会员首页</Link> },
    { key: '/member/products', icon: <ShoppingBag size={17} />, label: <Link to="/member/products">发现好物</Link> },
    { key: '/member/cart', icon: <ShoppingCart size={17} />, label: <Link to="/member/cart">购物车</Link> },
    { key: '/member/orders', icon: <PackageCheck size={17} />, label: <Link to="/member/orders">我的订单</Link> },
    { key: '/member/messages', icon: <MessageSquareText size={17} />, label: <Link to="/member/messages">留言板</Link> },
    { key: '/member/profile', icon: <UserRound size={17} />, label: <Link to="/member/profile">个人资料</Link> },
  ]
  async function logout() {
    try { await api.post('/auth/logout') } finally {
      await client.invalidateQueries({ queryKey: queryKeys.me })
      navigate('/login')
    }
  }
  const selected = menuItems.find((item) => location.pathname.startsWith(item.key))?.key ?? '/member/home'
  return (
    <Layout className="app-layout">
      <Sider breakpoint="lg" collapsedWidth="0" theme="light" className="app-sider">
        <Link to="/member/home" className="brand">
          <span className="brand-mark">拾</span>
          <span>拾光集</span>
        </Link>
        <div className="sider-caption">MEMBER SHOP</div>
        <Menu mode="inline" selectedKeys={[selected]} items={menuItems} />
        <div className="sider-note"><strong>本月会员礼</strong><span>满 3 单赠限定香氛</span></div>
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="header-context"><span className="header-dot" />今日精选 · 为生活留一点余地</div>
          <Space size={18}>
            <Badge count={0} showZero size="small"><Link to="/member/cart" className="header-icon"><ShoppingCart size={19} /></Link></Badge>
            <div className="user-chip"><Avatar size={32} className="user-avatar">{user?.username?.slice(0, 1).toUpperCase()}</Avatar><span>{user?.username ?? '会员'}</span></div>
            <Button type="text" icon={<LogOut size={17} />} onClick={logout} aria-label="退出登录" />
          </Space>
        </Header>
        <Content className="app-content"><Outlet /></Content>
      </Layout>
    </Layout>
  )
}
