import React from 'react'
import { Button, Card, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph } = Typography

export default function ProfileModePage() {
  const navigate = useNavigate()
  return (
    <main style={{ minHeight: '100vh', background: '#F5F7FA', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, boxSizing: 'border-box' }}>
      <section style={{ width: '100%', maxWidth: 880 }}>
        <Title level={1}>欢迎使用智育万象</Title>
        <Paragraph>请选择适合自己的使用模式。</Paragraph>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 24 }}>
          <Card title="普通模式">
            <Paragraph>使用账号登录，填写学习画像问卷，获取个性化学习规划。</Paragraph>
            <Button type="primary" size="large" block onClick={() => navigate('/login')}>进入普通模式</Button>
          </Card>
          <Card title="残障模式">
            <Paragraph>直接进入 Project 脑机学习界面，使用脑机画像流程及补充画像问卷。</Paragraph>
            <Button type="primary" size="large" block onClick={() => navigate('/accessibility')}>进入残障模式</Button>
          </Card>
        </div>
      </section>
    </main>
  )
}
