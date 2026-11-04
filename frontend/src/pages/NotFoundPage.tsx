import { Button, Result } from 'antd'
import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return <Result status="404" title="页面不存在" subTitle="你访问的页面可能已经离开拾光集。" extra={<Link to="/"><Button type="primary">回到首页</Button></Link>} />
}
