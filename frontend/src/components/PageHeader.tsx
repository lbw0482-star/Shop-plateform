import { Breadcrumb, Typography } from 'antd'
import type { ReactNode } from 'react'

export default function PageHeader({ eyebrow, title, description, extra }: { eyebrow?: string; title: string; description?: string; extra?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <Typography.Title level={2}>{title}</Typography.Title>
        {description && <Typography.Paragraph type="secondary">{description}</Typography.Paragraph>}
      </div>
      {extra && <div className="page-header-extra">{extra}</div>}
    </div>
  )
}
