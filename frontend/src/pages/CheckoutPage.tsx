import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, MapPin, ShieldCheck } from 'lucide-react'
import { Alert, Button, Card, Col, Divider, Form, Input, Radio, Row, Skeleton, Space, Steps, Typography, App as AntApp } from 'antd'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeCart } from '../api/normalize'
import type { CartItem } from '../types'
import PageHeader from '../components/PageHeader'

type CheckoutValues = { receiver_name: string; receiver_phone: string; receiver_address: string; payment_method: string; remark?: string }

export default function CheckoutPage() {
  const location = useLocation(); const navigate = useNavigate(); const client = useQueryClient(); const { message } = AntApp.useApp()
  const itemIds = (location.state as { itemIds?: number[] } | null)?.itemIds ?? []
  const [form] = Form.useForm<CheckoutValues>(); const [submitted, setSubmitted] = useState(false)
  const cartQuery = useQuery({ queryKey: queryKeys.cart, queryFn: async () => normalizeCart(await api.get('/cart')) })
  const createOrder = useMutation({ mutationFn: (values: CheckoutValues) => api.post<any>('/orders', { ...values, item_ids: itemIds }), onSuccess: (raw) => { const order = raw?.order_id ? raw : raw?.order ?? raw; setSubmitted(true); client.invalidateQueries({ queryKey: queryKeys.cart }); message.success('订单创建成功'); setTimeout(() => navigate(`/member/orders/${order.order_id ?? order.id}`), 650) } })
  const items = (cartQuery.data?.items ?? []).filter((item) => itemIds.includes(item.id))
  const total = items.reduce((sum, item) => sum + Number(item.subtotal), 0)
  if (submitted) return <div className="member-page"><Card className="success-panel"><div className="success-icon"><Check size={28} /></div><Typography.Title level={3}>订单已提交</Typography.Title><Typography.Paragraph type="secondary">正在为你打开订单详情…</Typography.Paragraph></Card></div>
  return <div className="member-page"><PageHeader eyebrow="CHECKOUT" title="确认订单" extra={<Link to="/member/cart"><Button type="link" icon={<ArrowLeft size={16} />}>返回购物车</Button></Link>} /><Steps current={0} items={[{ title: '确认信息' }, { title: '模拟支付' }, { title: '等待确认' }]} className="checkout-steps" /><Form form={form} layout="vertical" size="large" onFinish={(values) => createOrder.mutate(values)} initialValues={{ payment_method: 'SIMULATED_ONLINE' }}><Row gutter={[20, 20]}><Col xs={24} lg={15}><Card title={<Space><MapPin size={17} />收货信息</Space>} className="form-card"><Row gutter={16}><Col xs={24} sm={12}><Form.Item label="联系人" name="receiver_name" rules={[{ required: true, message: '请输入联系人' }]}><Input placeholder="请输入联系人姓名" /></Form.Item></Col><Col xs={24} sm={12}><Form.Item label="联系电话" name="receiver_phone" rules={[{ required: true, message: '请输入联系电话' }]}><Input placeholder="请输入联系电话" /></Form.Item></Col></Row><Form.Item label="收货地址" name="receiver_address" rules={[{ required: true, message: '请输入收货地址' }]}><Input.TextArea rows={3} placeholder="请输入详细地址" /></Form.Item><Form.Item label="付款方式" name="payment_method"><Radio.Group><Radio value="SIMULATED_ONLINE">模拟在线支付</Radio><Radio value="SIMULATED_BALANCE">模拟余额支付</Radio></Radio.Group></Form.Item><Form.Item label="订单备注" name="remark"><Input.TextArea rows={3} showCount maxLength={500} placeholder="给商家的留言（选填）" /></Form.Item></Card></Col><Col xs={24} lg={9}><Card title="订单摘要" className="order-summary-card">{cartQuery.isLoading ? <Skeleton active /> : items.length === 0 ? <Alert type="warning" showIcon message="没有选中的商品" /> : <>{items.map((item) => <div className="summary-product" key={item.id}><div><Typography.Text strong>{item.product_name}</Typography.Text><div className="product-category">× {item.quantity}</div></div><span>¥ {Number(item.subtotal).toFixed(2)}</span></div>)}<Divider /><div className="total-line"><span>订单总额</span><strong className="large-total">¥ {total.toFixed(2)}</strong></div><div className="secure-note"><ShieldCheck size={15} /> 提交后库存将被锁定</div><Button type="primary" htmlType="submit" size="large" block loading={createOrder.isPending} disabled={!items.length}>提交订单</Button></>}</Card></Col></Row></Form></div>
}
