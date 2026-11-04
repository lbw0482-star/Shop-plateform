import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, CreditCard, RotateCcw, Truck } from 'lucide-react'
import { Alert, Button, Card, Col, Descriptions, Divider, Row, Steps, Tag, Typography, App as AntApp } from 'antd'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeOrder } from '../api/normalize'
import { labelForStatus } from '../types'
import type { Order } from '../types'
import LoadingState from '../components/LoadingState'
import PageHeader from '../components/PageHeader'

export default function OrderDetailPage() {
  const { id } = useParams(); const navigate = useNavigate(); const client = useQueryClient(); const { message } = AntApp.useApp()
  const query = useQuery({ queryKey: queryKeys.order(id ?? ''), queryFn: async () => normalizeOrder(await api.get(`/orders/${id}`)), enabled: Boolean(id) })
  const cancel = useMutation({ mutationFn: () => api.post(`/orders/${id}/cancel`, { reason: '会员主动取消' }), onSuccess: () => { message.success('订单已取消'); client.invalidateQueries({ queryKey: queryKeys.order(id ?? '') }); client.invalidateQueries({ queryKey: queryKeys.orders({}) }) } })
  const pay = useMutation({ mutationFn: () => api.post(`/orders/${id}/pay?success=true`), onSuccess: () => { message.success('模拟支付成功'); client.invalidateQueries({ queryKey: queryKeys.order(id ?? '') }) } })
  if (query.isLoading) return <div className="member-page"><LoadingState /></div>
  if (query.isError || !query.data) return <div className="member-page"><Alert type="error" message="订单不存在或无权查看" showIcon /><Link to="/member/orders"><Button type="link" icon={<ArrowLeft size={16} />}>返回订单列表</Button></Link></div>
  const order = query.data; const canCancel = order.order_status === 'W'; const canPay = order.order_status === 'W' && order.payment_status === 'U'; const current = order.order_status === 'W' ? 0 : order.order_status === 'C' ? 1 : order.order_status === 'P' ? 2 : order.order_status === 'F' ? 3 : -1
  return <div className="member-page"><PageHeader eyebrow="ORDER DETAIL" title={order.order_no} extra={<Link to="/member/orders"><Button type="link" icon={<ArrowLeft size={16} />}>返回订单</Button></Link>} /><Card className="order-status-card"><div className="status-card-top"><div><Typography.Text type="secondary">当前状态</Typography.Text><div><Tag color={order.order_status === 'F' ? 'success' : 'processing'}>{labelForStatus(order.order_status)}</Tag></div></div><div className="status-actions">{canPay && <Button type="primary" icon={<CreditCard size={16} />} loading={pay.isPending} onClick={() => pay.mutate()}>模拟支付</Button>}{canCancel && <Button danger icon={<RotateCcw size={16} />} loading={cancel.isPending} onClick={() => cancel.mutate()}>取消订单</Button>}</div></div><Steps current={current} status={current < 0 ? 'error' : 'process'} items={[{ title: '待付款', icon: <CreditCard size={17} /> }, { title: '待确认', icon: <CheckCircle2 size={17} /> }, { title: '处理中', icon: <Truck size={17} /> }, { title: '已完成', icon: <CheckCircle2 size={17} /> }]} /></Card><Row gutter={[20, 20]}><Col xs={24} lg={15}><Card title="商品明细" className="table-card">{(order.items ?? []).map((item, index) => <div className="order-item" key={`${item.product_name_snapshot}-${index}`}><div className="order-item-thumb" /><div className="order-item-info"><Typography.Text strong>{item.product_name_snapshot}</Typography.Text><Typography.Text type="secondary">¥ {Number(item.unit_price).toFixed(2)} × {item.quantity}</Typography.Text></div><Typography.Text strong>¥ {Number(item.subtotal).toFixed(2)}</Typography.Text></div>)}<Divider /><div className="total-line"><span>订单总额</span><strong className="large-total">¥ {Number(order.total_amount).toFixed(2)}</strong></div></Card></Col><Col xs={24} lg={9}><Card title="收货信息" className="table-card"><Descriptions column={1} size="small"><Descriptions.Item label="联系人">{order.receiver_name}</Descriptions.Item><Descriptions.Item label="联系电话">{order.receiver_phone}</Descriptions.Item><Descriptions.Item label="收货地址">{order.receiver_address}</Descriptions.Item><Descriptions.Item label="下单时间">{new Date(order.order_time).toLocaleString('zh-CN')}</Descriptions.Item><Descriptions.Item label="获得积分">+{order.earned_points} 分</Descriptions.Item></Descriptions></Card></Col></Row></div>
}
