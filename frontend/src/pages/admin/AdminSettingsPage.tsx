import { useQuery } from '@tanstack/react-query'
import { Card, Col, Descriptions, Row, Table, Tag, Typography } from 'antd'
import { api } from '../../api/client'
import PageHeader from '../../components/PageHeader'

type Level = { level_id: number; level_name: string; min_points: number; max_points?: number | null; status: string }

export default function AdminSettingsPage() {
  const levels = useQuery({ queryKey: ['admin', 'levels'], queryFn: () => api.get<Level[]>('/admin/levels') })
  return <div className="admin-page"><PageHeader eyebrow="SYSTEM" title="系统设置" description="查看会员等级规则和当前系统配置。" /><Row gutter={[16, 16]}><Col xs={24} lg={14}><Card title="会员等级规则" className="table-card"><Table rowKey="level_id" loading={levels.isLoading} dataSource={levels.data ?? []} pagination={false} columns={[{ title: '等级', dataIndex: 'level_name', render: (value: string) => <Tag color="gold">{value}</Tag> }, { title: '积分下限', dataIndex: 'min_points' }, { title: '积分上限', dataIndex: 'max_points', render: (value: number | null) => value ?? '不设上限' }, { title: '状态', dataIndex: 'status', render: (value: string) => value === 'A' ? <Tag color="success">启用</Tag> : <Tag>停用</Tag> }]} /></Card></Col><Col xs={24} lg={10}><Card title="课程设计配置"><Descriptions column={1} size="small"><Descriptions.Item label="认证方式">HttpOnly Cookie 会话</Descriptions.Item><Descriptions.Item label="图片存储">本地 uploads 目录</Descriptions.Item><Descriptions.Item label="支付方式">模拟支付</Descriptions.Item><Descriptions.Item label="数据库">PostgreSQL</Descriptions.Item><Descriptions.Item label="运行方式">本地开发环境</Descriptions.Item></Descriptions><Typography.Paragraph type="secondary" className="settings-note">超级管理员可以在后端维护等级区间、管理员账号和角色权限。</Typography.Paragraph></Card></Col></Row></div>
}
