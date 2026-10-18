import React from 'react'
import { Card, Typography } from 'antd'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'

const { Text } = Typography

export default function ResourceCard({ title, icon, content, type = 'markdown' }) {
  if (!content) {
    return (
      <Card title={icon ? <>{icon} {title}</> : title}>
        <Text type="secondary">暂无内容</Text>
      </Card>
    )
  }

  return (
    <Card
      title={icon ? <>{icon} {title}</> : title}
      styles={{ body: { padding: '16px 24px' } }}
    >
      <div className="dark-md" style={{ fontSize: 14, lineHeight: 1.8 }}>
        <ReactMarkdown
          remarkPlugins={[remarkMath, remarkGfm]}
          rehypePlugins={[rehypeKatex]}
          components={{
            // 处理知识点跳转链接
            a: ({ href, children, ...props }) => {
              if (href && href.startsWith('/learn/')) {
                return (
                  <a
                    {...props}
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      const kpId = href.replace('/learn/', '')
                      window.dispatchEvent(new CustomEvent('navigateToKp', { detail: kpId }))
                    }}
                    style={{ color: '#0EA5E9', textDecoration: 'underline' }}
                  >
                    {children}
                  </a>
                )
              }
              return <a {...props} href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#0EA5E9' }}>{children}</a>
            },
            // 代码块样式
            code: ({ inline, children, ...props }) => {
              if (inline) {
                return <code {...props} style={{ background: 'rgba(14,165,233,0.12)', color: '#0284C7', padding: '2px 6px', borderRadius: 4 }}>{children}</code>
              }
              return (
                <pre style={{ background: 'rgba(0,0,0,0.05)', padding: 16, borderRadius: 10, overflow: 'auto', border: '1px solid rgba(0,0,0,0.08)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  <code {...props}>{children}</code>
                </pre>
              )
            },
            // 表格样式
            table: ({ children, ...props }) => (
              <div style={{ overflow: 'auto' }}>
                <table {...props} style={{ borderCollapse: 'collapse', width: '100%' }}>{children}</table>
              </div>
            ),
            th: ({ children, ...props }) => (
              <th {...props} style={{ border: '1px solid rgba(0,0,0,0.12)', padding: '8px 12px', background: 'rgba(0,0,0,0.04)', textAlign: 'left' }}>{children}</th>
            ),
            td: ({ children, ...props }) => (
              <td {...props} style={{ border: '1px solid rgba(0,0,0,0.12)', padding: '8px 12px' }}>{children}</td>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </Card>
  )
}
