import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Minus, Plus, Trash2 } from 'lucide-react'
import { Alert, Button, Card, Checkbox, Col, Divider, Empty, InputNumber, Row, Skeleton, Space, Table, Tag, Typography, App as AntApp } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeCart } from '../api/normalize'
import type { CartItem } from '../types'
import EmptyState from '../components/EmptyState'
import PageHeader from '../components/PageHeader'

export default function CartPage() {
  const client = useQueryClient(); const navigate = useNavigate(); const { message } = AntApp.useApp()
  const [selected, setSelected] = useState<number[]>([])
  const cartQuery = useQuery({ queryKey: queryKeys.cart, queryFn: async () => normalizeCart(await api.get('/cart')) })
  const update = useMutation({ mutationFn: ({ itemId, quantity }: { itemId: number; quantity: number }) => api.patch(`/cart/items/${itemId}`, { quantity }), onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.cart }) })
  const remove = useMutation({ mutationFn: (itemId: number) => api.delete(`/cart/items/${itemId}`), onSuccess: (_, itemId) => { setSelected((current) => current.filter((id) => id !== itemId)); client.invalidateQueries({ queryKey: queryKeys.cart }); message.success('已移除商品') } })
  const items = cartQuery.data?.items ?? []
  const allSelected = items.length > 0 && selected.length === items.length
  const selectedItems = items.filter((item) => selected.includes(item.id))
  const total = useMemo(() => selectedItems.reduce((sum, item) => sum + Number(item.subtotal), 0), [selectedItems])
  function checkout() { if (!selected.length) { message.warning('请先选择要结算的商品'); return }; navigate('/member/checkout', { state: { itemIds: selected } }) }
  return <div className="member-page"><PageHeader eyebrow="YOUR SELECTION" title="购物车" description="选好今天想带回家的东西。" extra={<Link to="/member/products"><Button type="link" icon={<ArrowRight size={16} />} iconPosition="end">继续购物</Button></Link>} />
    {cartQuery.isLoading ? <Card><Skeleton active /></Card> : cartQuery.isError ? <Alert type="error" showIcon message="购物车加载失败，请刷新重试" /> : items.length === 0 ? <Card><EmptyState description="购物车还是空的，去挑一些喜欢的吧" /><div className="empty-action"><Link to="/member/products"><Button type="primary">去逛逛</Button></Link></div></Card> : <><Card className="cart-card"><div className="cart-select-all"><Checkbox checked={allSelected} onChange={(event) => setSelected(event.target.checked ? items.map((item) => item.id) : [])}>全选</Checkbox><Typography.Text type="secondary">共 {items.length} 件商品</Typography.Text></div><Table rowKey="id" dataSource={items} pagination={false} scroll={{ x: 720 }} rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }} columns={[{ title: '商品', dataIndex: 'product_name', render: (value: string, item: CartItem) => <div className="cart-product"><div className="cart-thumb" /><div><Typography.Text strong>{value}</Typography.Text><div className="product-category">现货 · {item.stock_qty} 件</div></div></div> }, { title: '单价', dataIndex: 'unit_price', render: (value: number) => `¥ ${Number(value).toFixed(2)}` }, { title: '数量', dataIndex: 'quantity', render: (value: number, item: CartItem) => <InputNumber min={1} max={item.stock_qty} value={value} controls addonBefore={<Minus size={13} />} addonAfter={<Plus size={13} />} onChange={(quantity) => quantity && update.mutate({ itemId: item.id, quantity })} /> }, { title: '小计', dataIndex: 'subtotal', render: (value: number) => <Typography.Text strong>¥ {Number(value).toFixed(2)}</Typography.Text> }, { title: '', key: 'action', render: (_: unknown, item: CartItem) => <Button type="text" danger icon={<Trash2 size={16} />} onClick={() => remove.mutate(item.id)} aria-label="删除商品" /> }]} /></Card><Row gutter={[20, 20]} className="cart-bottom"><Col xs={24} md={15}><Card className="cart-note"><div className="eyebrow">SHOPPING NOTE</div><Typography.Paragraph type="secondary">商品库存会在提交订单时再次校验。订单未付款前，你可以修改联系人和商品数量。</Typography.Paragraph></Card></Col><Col xs={24} md={9}><Card className="cart-total"><div className="total-line"><span>已选商品</span><span>{selected.length} 件</span></div><div className="total-line"><span>商品总额</span><strong>¥ {total.toFixed(2)}</strong></div><Divider /><Button type="primary" size="large" block icon={<ArrowRight size={17} />} iconPosition="end" onClick={checkout}>去结算</Button></Card></Col></Row></>}
  </div>
}
