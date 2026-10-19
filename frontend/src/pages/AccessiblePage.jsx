import React from 'react'
import { Button } from 'antd'
import { useNavigate } from 'react-router-dom'

export default function AccessiblePage() {
  const navigate = useNavigate()
  return (
    <main style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: '#111820' }}>
      <nav aria-label="模式导航" style={{ padding: 12, flexShrink: 0 }}>
        <Button size="large" onClick={() => navigate('/')}>返回模式选择</Button>
      </nav>
      <iframe title="Project 脑机学习与补充画像" src={`${import.meta.env.BASE_URL}accessibility/index.html`}
        style={{ width: '100%', flex: 1, minHeight: 0, border: 0 }} />
    </main>
  )
}
