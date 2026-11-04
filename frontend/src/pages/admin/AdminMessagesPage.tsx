import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, EyeOff, MessageSquareReply, Search, Trash2 } from 'lucide-react'
import { Button, Card, Input, List, Modal, Tag, Typography, Form, App as AntApp } from 'antd'
import { useState } from 'react'
import { api } from '../../api/client'
import type { Message } from '../../types'
import { normalizeMessages } from '../../api/normalize'
import PageHeader from '../../components/PageHeader'

type AdminMessage = Message & { username?: string }

export default function AdminMessagesPage() {
  const [keyword, setKeyword] = useState(''); const [selected, setSelected] = useState<AdminMessage | null>(null); const [form] = Form.useForm<{ content: string }>(); const client = useQueryClient(); const { message } = AntApp.useApp()
  const query = useQuery({ queryKey: ['admin', 'messages', keyword], queryFn: async () => normalizeMessages(await api.get('/admin/messages', { keyword: keyword || undefined })) as AdminMessage[] })
  const action = useMutation({ mutationFn: ({ id, actionName, body }: { id: number; actionName: string; body?: object }) => api.post(`/admin/messages/${id}/${actionName}`, body), onSuccess: () => { setSelected(null); form.resetFields(); client.invalidateQueries({ queryKey: ['admin', 'messages'] }); message.success('留言已更新') } })
  return <div className="admin-page"><PageHeader eyebrow="COMMUNITY" title="留言审核" description="审核会员留言，并及时回复每一份反馈。" /><Card className="admin-toolbar"><Input prefix={<Search size={16} />} placeholder="搜索留言标题或内容" value={keyword} onChange={(event) => setKeyword(event.target.value)} allowClear /></Card><Card className="message-admin-card"><List loading={query.isLoading} dataSource={query.data ?? []} renderItem={(item: AdminMessage) => <List.Item actions={[item.message_status === 'P' && <Button type="link" icon={<Check size={15} />} onClick={() => action.mutate({ id: item.id, actionName: 'approve' })}>通过</Button>, <Button type="link" icon={<MessageSquareReply size={15} />} onClick={() => { setSelected(item); form.resetFields() }}>回复</Button>, <Button type="link" icon={<EyeOff size={15} />} onClick={() => action.mutate({ id: item.id, actionName: 'hide' })}>隐藏</Button>, <Button type="link" danger icon={<Trash2 size={15} />} onClick={() => action.mutate({ id: item.id, actionName: 'delete' })}>删除</Button>]}><List.Item.Meta title={<div className="message-title"><Typography.Text strong>{item.title}</Typography.Text><Tag>{item.message_status === 'P' ? '待审核' : item.message_status === 'A' ? '已公开' : '已隐藏'}</Tag></div>} description={<><Typography.Text type="secondary">{item.username || '会员'} · {new Date(item.created_time).toLocaleString('zh-CN')}</Typography.Text><Typography.Paragraph ellipsis={{ rows: 2 }}>{item.content}</Typography.Paragraph></>} /></List.Item>} /></Card><Modal open={Boolean(selected)} title={`回复：${selected?.title}`} okText="发送回复" cancelText="取消" confirmLoading={action.isPending} onCancel={() => setSelected(null)} onOk={() => form.submit()}><Form form={form} onFinish={(values) => selected && action.mutate({ id: selected.id, actionName: 'reply', body: values })}><Form.Item name="content" rules={[{ required: true, message: '请输入回复内容' }]}><Input.TextArea rows={5} maxLength={2000} showCount placeholder="写下你的回复" /></Form.Item></Form></Modal></div>
}
