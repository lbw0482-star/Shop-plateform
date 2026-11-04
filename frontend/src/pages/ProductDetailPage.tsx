import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Minus, Plus, ShoppingCart, Star } from 'lucide-react'
import { Alert, Button, Card, Divider, InputNumber, Skeleton, Tag, Typography, App as AntApp } from 'antd'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeProduct } from '../api/normalize'
import type { Product } from '../types'
import PageHeader from '../components/PageHeader'

export default function ProductDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const { message } = AntApp.useApp()
  const [quantity, setQuantity] = useState(1)
  const query = useQuery({ queryKey: queryKeys.product(id ?? ''), queryFn: async () => normalizeProduct(await api.get(`/products/${id}`)), enabled: Boolean(id) })
  const addMutation = useMutation({ mutationFn: () => api.post('/cart/items', { product_id: Number(id), quantity }), onSuccess: () => { client.invalidateQueries({ queryKey: queryKeys.cart }); message.success('已加入购物车') } })
  if (query.isLoading) return <div className="member-page"><Skeleton active /></div>
  if (query.isError || !query.data) return <div className="member-page"><Alert type="error" showIcon message="商品不存在或已下架" /><Link to="/member/products"><Button type="link" icon={<ArrowLeft size={16} />}>返回商品列表</Button></Link></div>
  const product = query.data
  return <div className="member-page"><PageHeader eyebrow="PRODUCT DETAIL" title={product.product_name} extra={<Link to="/member/products"><Button type="link" icon={<ArrowLeft size={16} />}>返回列表</Button></Link>} /><div className="detail-layout"><div className="detail-visual"><div className="detail-image">{product.recommend_flag && <Tag color="gold" className="detail-badge"><Star size={13} />会员推荐</Tag>}</div></div><Card className="detail-panel"><div className="eyebrow">{product.category_name ?? '精选好物'}</div><Typography.Title level={2}>{product.product_name}</Typography.Title><Typography.Paragraph className="detail-intro">{product.product_intro ?? '认真挑选的日常好物，适合送给自己，也适合分享给重要的人。'}</Typography.Paragraph><div className="detail-price">¥ {Number(product.unit_price).toFixed(2)}</div><div className="point-line"><span>购买可获得 {product.product_points} 积分 / 件</span><span className={product.stock_qty > 0 ? 'stock-ok' : 'stock-empty'}>{product.stock_qty > 0 ? `库存 ${product.stock_qty} 件` : '暂时缺货'}</span></div><Divider /><div className="quantity-row"><span>购买数量</span><InputNumber min={1} max={product.stock_qty} value={quantity} onChange={(value) => setQuantity(value ?? 1)} disabled={product.stock_qty < 1} addonBefore={<Minus size={14} />} addonAfter={<Plus size={14} />} /></div><Button type="primary" size="large" block icon={<ShoppingCart size={18} />} disabled={product.stock_qty < 1} loading={addMutation.isPending} onClick={() => addMutation.mutate()}>加入购物车</Button><Button size="large" block className="buy-now-button" disabled={product.stock_qty < 1} onClick={() => { addMutation.mutate(); navigate('/member/cart') }}>立即购买</Button></Card></div></div>
}
