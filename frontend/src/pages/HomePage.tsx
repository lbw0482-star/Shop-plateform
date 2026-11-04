import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ChevronRight, Sparkles, Star } from 'lucide-react'
import { Button, Card, Col, Row, Statistic, Tag, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeProductPage } from '../api/normalize'
import type { Product } from '../types'
import { useCurrentUser } from '../App'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHeader from '../components/PageHeader'

const fallbackProducts: Product[] = [
  { id: 1, product_code: 'SG-001', product_name: '晨雾手冲咖啡礼盒', category_id: 1, category_name: '日常好物', stock_qty: 28, unit_price: 128, product_intro: '来自山地小批次的明亮风味。', product_points: 12, recommend_flag: true, product_status: 'O' },
  { id: 2, product_code: 'SG-002', product_name: '白瓷晨光马克杯', category_id: 1, category_name: '日常好物', stock_qty: 16, unit_price: 88, product_intro: '一只适合每天使用的杯子。', product_points: 8, recommend_flag: true, product_status: 'O' },
  { id: 3, product_code: 'SG-003', product_name: '雪松与无花果香氛', category_id: 2, category_name: '香氛生活', stock_qty: 9, unit_price: 158, product_intro: '清冷木质调，留在房间里的安静气味。', product_points: 15, recommend_flag: true, product_status: 'O' },
]

export default function HomePage() {
  const { data: user } = useCurrentUser()
  const productsQuery = useQuery({ queryKey: queryKeys.products({ recommend: true }), queryFn: async () => normalizeProductPage(await api.get('/products', { recommend: true, page_size: 3 })) })
  const products = productsQuery.data?.items ?? fallbackProducts
  return (
    <div className="member-page">
      <PageHeader eyebrow="GOOD MORNING" title={`你好，${user?.username ?? '会员'}`} description="今天也为自己留一点挑选好物的时间。" extra={<Link to="/member/products"><Button type="link" icon={<ArrowRight size={16} />} iconPosition="end">浏览全部商品</Button></Link>} />
      <section className="welcome-banner">
        <div><div className="eyebrow light">MEMBER NOTE  /  11.04</div><h1>把喜欢的东西，<br /><em>慢慢带回家。</em></h1><p>精选日常好物，会员专享积分与礼遇。</p><Link to="/member/products"><Button ghost icon={<ArrowRight size={16} />} iconPosition="end">去逛逛</Button></Link></div>
        <div className="banner-stamp"><Sparkles size={22} /><span>今日<br />精选</span></div>
      </section>
      <Row gutter={[20, 20]} className="summary-row">
        <Col xs={24} sm={8}><Card className="summary-card"><Statistic title="当前积分" value={user?.total_points ?? 0} suffix="分" /><div className="summary-caption">再积 120 分升级银牌会员</div></Card></Col>
        <Col xs={24} sm={8}><Card className="summary-card"><Statistic title="会员等级" value={user?.level_name ?? '普通会员'} /><div className="summary-caption"><Star size={14} /> 享有会员专属礼遇</div></Card></Col>
        <Col xs={24} sm={8}><Card className="summary-card"><Statistic title="本月订单" value={0} suffix="单" /><div className="summary-caption">每一次下单都值得纪念</div></Card></Col>
      </Row>
      <div className="section-heading"><div><div className="eyebrow">CURATED FOR YOU</div><Typography.Title level={3}>今日推荐</Typography.Title></div><Link to="/member/products">查看全部 <ChevronRight size={16} /></Link></div>
      {productsQuery.isLoading ? <LoadingState /> : products.length === 0 ? <EmptyState description="暂时没有推荐商品" /> : <Row gutter={[20, 20]}>{products.map((product) => <Col xs={24} sm={12} lg={8} key={product.id}><ProductCard product={product} /></Col>)}</Row>}
    </div>
  )
}

function ProductCard({ product }: { product: Product }) {
  const image = product.main_image_url ? (product.main_image_url.startsWith('http') ? product.main_image_url : `/uploads/${product.main_image_url}`) : undefined
  return <Link to={`/member/products/${product.id}`} className="product-card-link"><Card className="product-card" cover={<div className="product-image" style={image ? { backgroundImage: `url(${image})` } : undefined}><div className="product-image-label">{product.category_name ?? '精选'}</div></div>}><div className="product-card-meta"><span className="product-category">{product.category_name ?? '日常好物'}</span><Tag color="green">+{product.product_points} 积分</Tag></div><Typography.Title level={4}>{product.product_name}</Typography.Title><Typography.Text type="secondary">{product.product_intro ?? '为日常挑选一件刚刚好的好物。'}</Typography.Text><div className="product-price">¥ {Number(product.unit_price).toFixed(2)}</div></Card></Link>
}
