import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Filter, Search, SlidersHorizontal } from 'lucide-react'
import { Button, Card, Col, Empty, Input, Pagination, Row, Select, Tag, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeProductPage } from '../api/normalize'
import type { Product, PageResult } from '../types'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHeader from '../components/PageHeader'

export default function ProductsPage() {
  const [keyword, setKeyword] = useState('')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string>()
  const [page, setPage] = useState(1)
  const params = { keyword: search || undefined, category_id: category, page, page_size: 12, status: 'O' }
  const productsQuery = useQuery({ queryKey: queryKeys.products(params), queryFn: async () => normalizeProductPage(await api.get('/products', params)) })
  const categories = useQuery({ queryKey: ['categories'], queryFn: () => api.get<Array<{ category_id: number; category_name: string }>>('/categories') })
  const items = productsQuery.data?.items ?? []
  function submitSearch() { setPage(1); setSearch(keyword.trim()) }
  return <div className="member-page"><PageHeader eyebrow="THE SHOP" title="发现好物" description="从每天会用到的东西开始，慢慢建立自己的生活清单。" />
    <Card className="filter-card"><div className="filter-main"><Input size="large" value={keyword} onChange={(e) => setKeyword(e.target.value)} onPressEnter={submitSearch} prefix={<Search size={18} />} placeholder="搜索商品名称" allowClear /><Button type="primary" size="large" onClick={submitSearch}>搜索</Button></div><div className="filter-options"><span><SlidersHorizontal size={16} />筛选</span><Select allowClear placeholder="全部分类" value={category} onChange={(value) => { setCategory(value); setPage(1) }} options={(categories.data ?? []).map((item) => ({ label: item.category_name, value: String(item.category_id) }))} /><Button icon={<Filter size={16} />} onClick={() => { setCategory(undefined); setSearch(''); setKeyword(''); setPage(1) }}>清除筛选</Button></div></Card>
    <div className="result-bar"><Typography.Text type="secondary">{productsQuery.data ? `共 ${productsQuery.data.total} 件商品` : '正在查找商品'}</Typography.Text><Select variant="borderless" defaultValue="recommend" options={[{ value: 'recommend', label: '推荐排序' }, { value: 'price_asc', label: '价格从低到高' }, { value: 'price_desc', label: '价格从高到低' }]} /></div>
    {productsQuery.isLoading ? <LoadingState /> : productsQuery.isError ? <Empty description="商品加载失败，请稍后重试" /> : items.length === 0 ? <EmptyState description="没有找到符合条件的商品" /> : <Row gutter={[20, 20]}>{items.map((product) => <Col xs={24} sm={12} lg={8} xl={6} key={product.id}><Link to={`/member/products/${product.id}`} className="product-card-link"><Card className="product-card" cover={<div className="product-image"><div className="product-image-label">{product.category_name ?? '精选'}</div></div>}><div className="product-card-meta"><span className="product-category">{product.category_name ?? '好物'}</span><Tag color="green">+{product.product_points}</Tag></div><Typography.Title level={4}>{product.product_name}</Typography.Title><Typography.Text type="secondary">{product.product_intro ?? '为日常挑选一件刚刚好的好物。'}</Typography.Text><div className="product-price">¥ {Number(product.unit_price).toFixed(2)}</div></Card></Link></Col>)}</Row>}
    {productsQuery.data && productsQuery.data.total > 0 && <div className="pagination-wrap"><Pagination current={page} pageSize={12} total={productsQuery.data.total} showSizeChanger={false} onChange={setPage} /></div>}
  </div>
}
