import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, ClipboardList, MessageSquareText, Package, Users } from 'lucide-react'
import { Card, Col, Row, Statistic, Table, Tag, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { normalizeOrderPage } from '../../api/normalize'
import { labelForStatus } from '../../types'
import PageHeader from '../../components/PageHeader'
import LoadingState from '../../components/LoadingState'

type Stats = { member_count: number; product_count: number; order_count: number; message_count: number; order_amount?: number; paid_amount?: number | string }
type RecentOrder = { id: number; order_no: string; username?: string; total_amount: number; order_status: string; order_time: string }

export default function AdminDashboardPage() {
  const stats = useQuery({ queryKey: ['admin', 'statistics'], queryFn: () => api.get<Stats>('/admin/statistics') })
  const recent = useQuery({ queryKey: ['admin', 'recent-orders'], queryFn: async () => normalizeOrderPage(await api.get('/admin/orders', { page_size: 5, sort: 'latest' })) })
  const values = stats.data ?? { member_count: 0, product_count: 0, order_count: 0, message_count: 0, paid_amount: 0 }
  return <div className="admin-page"><PageHeader eyebrow="OVERVIEW" title="工作台" description="查看店铺今日经营情况和待处理事项。" /><Row gutter={[16, 16]} className="admin-stat-row"><Col xs={12} lg={6}><Card className="admin-stat-card"><Statistic title="会员总数" value={values.member_count} prefix={<Users size={19} />} /><Link to="/admin/users">查看会员 <ArrowUpRight size={14} /></Link></Card></Col><Col xs={12} lg={6}><Card className="admin-stat-card"><Statistic title="在售商品" value={values.product_count} prefix={<Package size={19} />} /><Link to="/admin/products">管理商品 <ArrowUpRight size={14} /></Link></Card></Col><Col xs={12} lg={6}><Card className="admin-stat-card"><Statistic title="累计订单" value={values.order_count} prefix={<ClipboardList size={19} />} /><Link to="/admin/orders">查看订单 <ArrowUpRight size={14} /></Link></Card></Col><Col xs={12} lg={6}><Card className="admin-stat-card"><Statistic title="待审核留言" value={values.message_count} prefix={<MessageSquareText size={19} />} /><Link to="/admin/messages">处理留言 <ArrowUpRight size={14} /></Link></Card></Col></Row><Row gutter={[16, 16]}><Col xs={24} lg={16}><Card title="最近订单" className="table-card"><Table loading={recent.isLoading} rowKey="id" dataSource={recent.data?.items ?? []} pagination={false} columns={[{ title: '订单号', dataIndex: 'order_no', render: (value: string, record: RecentOrder) => <Link to={`/admin/orders?order=${record.id}`}>{value}</Link> }, { title: '会员', dataIndex: 'username', render: (value: string) => value || '匿名会员' }, { title: '金额', dataIndex: 'total_amount', render: (value: number) => `¥ ${Number(value).toFixed(2)}` }, { title: '状态', dataIndex: 'order_status', render: (value: string) => <Tag color={value === 'F' ? 'success' : 'processing'}>{labelForStatus(value)}</Tag> }, { title: '时间', dataIndex: 'order_time', render: (value: string) => new Date(value).toLocaleDateString('zh-CN') }]} /></Card></Col><Col xs={24} lg={8}><Card className="insight-card"><div className="eyebrow">TODAY'S NOTE</div><Typography.Title level={3}>把每一次服务，<br />做得再好一点。</Typography.Title><Typography.Paragraph type="secondary">从会员的留言和订单里，了解他们真正需要什么。</Typography.Paragraph><Link to="/admin/messages">去看看留言 <ArrowUpRight size={15} /></Link></Card><Card className="amount-card"><Typography.Text type="secondary">累计订单金额</Typography.Text><Typography.Title level={2}>¥ {Number(values.order_amount ?? values.paid_amount ?? 0).toFixed(2)}</Typography.Title><Typography.Text type="secondary">全部订单统计</Typography.Text></Card></Col></Row></div>
}
