import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageCircle, Plus, Send, Trash2 } from 'lucide-react'
import { Button, Card, Empty, Form, Input, List, Modal, Tag, Typography, App as AntApp } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { queryKeys } from '../api/queryKeys'
import { normalizeMessages } from '../api/normalize'
import type { Message } from '../types'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHeader from '../components/PageHeader'

export default function MessagesPage() {
  const [open, setOpen] = useState(false); const [form] = Form.useForm<{ title: string; content: string }>(); const client = useQueryClient(); const { message } = AntApp.useApp()
  const query = useQuery({ queryKey: queryKeys.messages('member'), queryFn: async () => normalizeMessages(await api.get('/member/messages')) })
  const create = useMutation({ mutationFn: (values: { title: string; content: string }) => api.post('/member/messages', values), onSuccess: () => { setOpen(false); form.resetFields(); client.invalidateQueries({ queryKey: queryKeys.messages('member') }); message.success('留言已提交，等待管理员审核') } })
  const remove = useMutation({ mutationFn: (id: number) => api.delete(`/member/messages/${id}`), onSuccess: () => { client.invalidateQueries({ queryKey: queryKeys.messages('member') }); message.success('留言已删除') } })
  return <div className="member-page"><PageHeader eyebrow="A NOTE TO US" title="留言板" description="分享你的想法，我们会认真阅读。" extra={<Button type="primary" icon={<Plus size={16} />} onClick={() => setOpen(true)}>写留言</Button>} />{query.isLoading ? <LoadingState /> : (query.data ?? []).length === 0 ? <Card><EmptyState description="还没有留言，写下你的第一条想法吧" /></Card> : <Card className="message-list-card"><List dataSource={query.data} renderItem={(item: Message) => <List.Item actions={item.message_status === 'P' ? [<Button type="text" danger icon={<Trash2 size={15} />} onClick={() => remove.mutate(item.id)}>删除</Button>] : []}><List.Item.Meta avatar={<div className="message-avatar"><MessageCircle size={17} /></div>} title={<SpaceTitle title={item.title} status={item.message_status} />} description={<><Typography.Paragraph ellipsis={{ rows: 2 }}>{item.content}</Typography.Paragraph><Typography.Text type="secondary">{new Date(item.created_time).toLocaleString('zh-CN')}</Typography.Text>{item.reply_content && <div className="message-reply"><Send size={14} /><span>{item.reply_content}</span></div>}</>} /></List.Item>} /></Card>}<Modal open={open} title="写一条留言" okText="提交审核" cancelText="取消" confirmLoading={create.isPending} onCancel={() => setOpen(false)} onOk={() => form.submit()}><Form form={form} layout="vertical" onFinish={(values) => create.mutate(values)}><Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}><Input maxLength={100} placeholder="给这条留言起个标题" /></Form.Item><Form.Item name="content" label="内容" rules={[{ required: true, message: '请输入留言内容' }]}><Input.TextArea rows={6} maxLength={2000} showCount placeholder="想和我们分享什么？" /></Form.Item></Form></Modal></div>
}

function SpaceTitle({ title, status }: { title: string; status: string }) {
  return <div className="message-title"><Typography.Text strong>{title}</Typography.Text><Tag color={status === 'A' ? 'success' : status === 'H' ? 'default' : 'processing'}>{status === 'A' ? '已公开' : status === 'H' ? '已隐藏' : '待审核'}</Tag></div>
}
