import { useState } from 'react'
import { ArrowLeft, ArrowRight, LockKeyhole, UserRound } from 'lucide-react'
import { Alert, Button, Card, Form, Input, Typography, App as AntApp } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'

type RegisterValues = { username: string; password: string; confirmPassword: string }

export default function RegisterPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { message } = AntApp.useApp()
  async function submit(values: RegisterValues) {
    setLoading(true); setError('')
    try {
      await api.post('/auth/member/register', { username: values.username, password: values.password, confirm_password: values.confirmPassword })
      message.success('注册成功，请登录')
      navigate('/login')
    } catch (err) { setError(err instanceof ApiError ? err.message : '暂时无法注册，请稍后再试') } finally { setLoading(false) }
  }
  return (
    <div className="auth-page auth-register-page">
      <div className="auth-aside"><Link to="/login" className="brand auth-brand"><span className="brand-mark">拾</span><span>拾光集</span></Link><div className="auth-quote"><span className="eyebrow light">A SMALL BEGINNING</span><h1>从今天开始，<br />把喜欢加入日常。</h1><p>注册会员，收藏你的每一份心动。</p></div><div className="auth-aside-foot">A QUIETLY GOOD LIFE</div></div>
      <div className="auth-panel"><Card bordered={false} className="auth-card"><Link to="/login" className="back-link"><ArrowLeft size={16} />返回登录</Link><div className="eyebrow">JOIN US</div><Typography.Title level={2}>创建会员账号</Typography.Title><Typography.Paragraph type="secondary">只需要一个用户名和密码即可开始。</Typography.Paragraph>{error && <Alert showIcon type="error" message={error} className="form-alert" />}<Form layout="vertical" size="large" onFinish={submit} requiredMark={false}>
        <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }, { min: 3, message: '用户名至少 3 个字符' }]}><Input prefix={<UserRound size={17} />} placeholder="3-50 个字符" autoComplete="username" /></Form.Item>
        <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }, { min: 8, message: '密码至少 8 个字符' }]}><Input.Password prefix={<LockKeyhole size={17} />} placeholder="至少 8 个字符" autoComplete="new-password" /></Form.Item>
        <Form.Item label="确认密码" name="confirmPassword" dependencies={['password']} rules={[{ required: true, message: '请再次输入密码' }, ({ getFieldValue }) => ({ validator(_, value) { return !value || getFieldValue('password') === value ? Promise.resolve() : Promise.reject(new Error('两次密码不一致')) } })]}><Input.Password prefix={<LockKeyhole size={17} />} placeholder="再次输入密码" autoComplete="new-password" /></Form.Item>
        <Button type="primary" htmlType="submit" block loading={loading} icon={<ArrowRight size={17} />} iconPosition="end">创建账号</Button>
      </Form><div className="auth-links"><span>已经有账号？<Link to="/login">返回登录</Link></span></div></Card></div>
    </div>
  )
}
