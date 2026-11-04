import { BarChart3, ClipboardList, LayoutGrid, LogOut, MessageSquareText, Package, Settings, Users } from 'lucide-react'
import { Avatar, Button, Layout, Menu, Space } from 'antd'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { useCurrentUser } from '../App'

const { Header, Sider, Content } = Layout

export default function AdminShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const client = useQueryClient()
  const { data: user } = useCurrentUser()
  const items = [
    { key: '/admin', icon: <BarChart3 size={17} />, label: <Link to="/admin">工作台</Link> },
    { key: '/admin/products', icon: <Package size={17} />, label: <Link to="/admin/products">商品管理</Link> },
    { key: '/admin/orders', icon: <ClipboardList size={17} />, label: <Link to="/admin/orders">订单管理</Link> },
    { key: '/admin/users', icon: <Users size={17} />, label: <Link to="/admin/users">会员管理</Link> },
    { key: '/admin/messages', icon: <MessageSquareText size={17} />, label: <Link to="/admin/messages">留言审核</Link> },
    { key: '/admin/settings', icon: <Settings size={17} />, label: <Link to="/admin/settings">系统设置</Link> },
  ]
  async function logout() {
    try { await api.post('/auth/logout') } finally {
      await client.invalidateQueries({ queryKey: queryKeys.me })
      navigate('/login')
    }
  }
  const selected = items.find((item) => location.pathname === item.key || (item.key !== '/admin' && location.pathname.startsWith(item.key)))?.key ?? '/admin'
  return (
    <Layout className="admin-layout">
      <Sider theme="dark" breakpoint="lg" collapsedWidth="0" className="admin-sider">
        <Link to="/admin" className="brand admin-brand"><span className="brand-mark">拾</span><span>拾光集后台</span></Link>
        <div className="admin-caption"><LayoutGrid size={14} /> OPERATIONS CONSOLE</div>
        <Menu theme="dark" mode="inline" selectedKeys={[selected]} items={items} />
        <div className="admin-sider-footer">课程设计 · 管理后台</div>
      </Sider>
      <Layout>
        <Header className="admin-header">
          <div><span className="admin-kicker">OPERATIONS</span><strong>业务控制台</strong></div>
          <Space><div className="admin-user"><Avatar size={30}>{user?.username?.slice(0, 1).toUpperCase()}</Avatar><span>{user?.display_name ?? user?.username}</span></div><Button type="text" danger icon={<LogOut size={17} />} onClick={logout} /></Space>
        </Header>
        <Content className="admin-content"><Outlet /></Content>
      </Layout>
    </Layout>
  )
}
