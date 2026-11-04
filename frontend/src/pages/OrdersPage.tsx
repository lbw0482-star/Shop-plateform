import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, CalendarDays, Search } from 'lucide-react'
import { Button, Card, DatePicker, Empty, Input, Select, Space, Table, Tag, Typography, App as AntApp } from 'antd'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeOrderPage } from '../api/normalize'
import type { Order, PageResult } from '../types'
import { labelForStatus } from '../types'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHeader from '../components/PageHeader'

export default function OrdersPage() {
  const [keyword, setKeyword] = useState(''); const [status, setStatus] = useState<string>()
  const query = useQuery({ queryKey: queryKeys.orders({ keyword, status }), queryFn: async () => normalizeOrderPage(await api.get('/orders', { keyword: keyword || undefined, status })) })
  return <div className="member-page"><PageHeader eyebrow="YOUR JOURNEY" title="我的订单" description="每一份订单，都是认真生活的记录。" /><Card className="filter-card order-filter"><Input prefix={<Search size={17} />} placeholder="搜索订单号" value={keyword} onChange={(event) => setKeyword(event.target.value)} allowClear /><Select allowClear placeholder="全部状态" value={status} onChange={setStatus} options={['W', 'C', 'P', 'F', 'X', 'R', 'D'].map((value) => ({ label: labelForStatus(value), value }))} /><DatePicker suffixIcon={<CalendarDays size={16} />} placeholder="下单日期" /><Button type="primary" icon={<Search size={16} />} onClick={() => query.refetch()}>查询</Button></Card>{query.isLoading ? <LoadingState /> : query.isError ? <Empty description="订单加载失败，请稍后重试" /> : (query.data?.items ?? []).length === 0 ? <Card><EmptyState description="还没有订单，去挑选一件喜欢的东西吧" /></Card> : <Card className="table-card"><Table rowKey="id" dataSource={query.data?.items} pagination={{ pageSize: 10 }} columns={[{ title: '订单号', dataIndex: 'order_no', render: (value: string, record: Order) => <Link to={`/member/orders/${record.id ?? record.order_id}`}>{value}</Link> }, { title: '下单时间', dataIndex: 'order_time', render: (value: string) => new Date(value).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }) }, { title: '金额', dataIndex: 'total_amount', render: (value: number) => <Typography.Text strong>¥ {Number(value).toFixed(2)}</Typography.Text> }, { title: '状态', dataIndex: 'order_status', render: (value: string) => <Tag color={value === 'F' ? 'success' : value === 'X' || value === 'D' ? 'default' : 'processing'}>{labelForStatus(value)}</Tag> }, { title: '', render: (_: unknown, record: Order) => <Link to={`/member/orders/${record.id ?? record.order_id}`}><Button type="link" icon={<ArrowRight size={15} />} iconPosition="end">查看详情</Button></Link> }]} /></Card>}</div>
}
