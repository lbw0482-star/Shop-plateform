import { useState } from 'react'
import { ArrowRight, Eye, LockKeyhole, UserRound } from 'lucide-react'
import { Alert, Button, Card, Form, Input, Segmented, Typography, App as AntApp } from 'antd'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { queryKeys } from '../api/queryKeys'

type LoginValues = { username: string; password: string }

export default function LoginPage() {
  const [mode, setMode] = useState<'member' | 'admin'>('member')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const { message } = AntApp.useApp()
  const next = new URLSearchParams(location.search).get('next')

  async function submit(values: LoginValues) {
    setError('')
    setLoading(true)
    try {
      await api.post(`/auth/${mode}/login`, values)
      await queryClient.invalidateQueries({ queryKey: queryKeys.me })
      message.success('登录成功，欢迎回来')
      navigate(next || (mode === 'admin' ? '/admin' : '/member/home'), { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '暂时无法登录，请稍后再试')
    } finally { setLoading(false) }
  }

  return (
    <div className="auth-page">
      <div className="auth-aside">
        <Link to="/login" className="brand auth-brand"><span className="brand-mark">拾</span><span>拾光集</span></Link>
        <div className="auth-quote"><span className="eyebrow light">MEMBER SHOP</span><h1>让每一次选择，<br />都更接近喜欢的生活。</h1><p>为认真生活的人，挑选值得长期拥有的好物。</p></div>
        <div className="auth-aside-foot">SINCE 2026 · MEMBER SHOPPING</div>
      </div>
      <div className="auth-panel">
        <Card bordered={false} className="auth-card">
          <div className="eyebrow">WELCOME BACK</div>
          <Typography.Title level={2}>{mode === 'member' ? '登录拾光集' : '进入管理后台'}</Typography.Title>
          <Typography.Paragraph type="secondary">{mode === 'member' ? '登录后查看你的专属商品和订单' : '使用管理员账号处理每日业务'}</Typography.Paragraph>
          <Segmented block value={mode} onChange={(value) => { setMode(value as typeof mode); setError('') }} options={[{ label: '会员登录', value: 'member' }, { label: '管理员登录', value: 'admin' }]} className="login-segment" />
          {error && <Alert showIcon type="error" message={error} className="form-alert" />}
          <Form layout="vertical" size="large" onFinish={submit} requiredMark={false}>
            <Form.Item label="登录名" name="username" rules={[{ required: true, message: '请输入登录名' }]}><Input prefix={<UserRound size={17} />} placeholder={mode === 'member' ? '输入用户名' : '输入管理员账号'} autoComplete="username" /></Form.Item>
            <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}><Input.Password prefix={<LockKeyhole size={17} />} iconRender={(visible) => visible ? <Eye size={16} /> : <LockKeyhole size={16} />} placeholder="输入密码" autoComplete="current-password" /></Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading} icon={<ArrowRight size={17} />} iconPosition="end">登录</Button>
          </Form>
          {mode === 'member' && <div className="auth-links"><span>还没有账号？<Link to="/register">立即注册</Link></span><Link to="/login">忘记密码</Link></div>}
          {mode === 'admin' && <div className="auth-help">管理员密码由超级管理员维护，如需重置请联系系统负责人。</div>}
        </Card>
      </div>
    </div>
  )
}
