import React, { useState } from 'react'
import { Card, Button, Typography, Input, message, Space, Tag, Alert } from 'antd'
import { ThunderboltOutlined, UserOutlined, LockOutlined, RocketOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import { login, register } from '../api'

const { Title, Paragraph, Link } = Typography

export default function HomePage() {
  const { switchStudent, setToken } = useStore()
  const navigate = useNavigate()

  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const switchMode = (m) => {
    setMode(m)
    setError('')
    setPassword('')
    setConfirm('')
  }

  const handleLogin = async () => {
    const u = username.trim()
    if (!u || !password) {
      setError('请输入用户名和密码')
      return
    }
    setError('')
    setLoading(true)
    try {
      const { data } = await login(u, password)
      if (data.success) {
        setToken(data.access_token || '')
        switchStudent(u)
        message.success(`欢迎回来，${u}！`)
        navigate('/main')
      } else {
        setError(data.message || '登录失败')
      }
    } catch {
      setError('登录请求失败，请检查服务是否已启动')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async () => {
    const u = username.trim()
    if (!u || !password) {
      setError('请填写完整的注册信息')
      return
    }
    if (password.length < 6) {
      setError('密码至少需要 6 位')
      return
    }
    if (password !== confirm) {
      setError('两次输入的密码不一致')
      return
    }
    setError('')
    setLoading(true)
    try {
      const { data } = await register(u, password)
      if (data.success) {
        message.success('注册成功，请登录')
        switchMode('login')
      } else {
        setError(data.message || '注册失败')
      }
    } catch {
      setError('注册请求失败，请检查服务是否已启动')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = () => {
    if (mode === 'login') handleLogin()
    else handleRegister()
  }

  return (
    <div style={{
      minHeight: 'calc(100vh - 64px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px 48px',
    }}>
      <Card
        className="glass-card"
        style={{ textAlign: 'center', maxWidth: 460, width: '100%' }}
      >
        <ThunderboltOutlined style={{ fontSize: 56, color: '#0EA5E9', marginBottom: 16 }} />

        <Title level={2} style={{ marginBottom: 4 }}>
          智育万象
        </Title>

        <Space size={6} style={{ marginBottom: 12 }}>
          <Tag color="blue">人工智能导论</Tag>
          <Tag color="cyan">AI 多智能体系统</Tag>
        </Space>

        <Paragraph type="secondary" style={{ fontSize: 14, marginBottom: 20 }}>
          基于大模型的个性化资源生成与学习多智能体系统
        </Paragraph>

        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Input
            size="large"
            placeholder="用户名"
            value={username}
            onChange={(e) => { setUsername(e.target.value); setError('') }}
            prefix={<UserOutlined />}
            autoComplete="username"
            name="username"
            style={{ fontSize: 16 }}
          />
          <Input.Password
            size="large"
            placeholder="密码"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError('') }}
            onPressEnter={handleSubmit}
            prefix={<LockOutlined />}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            name="password"
            style={{ fontSize: 16 }}
          />
          {mode === 'register' && (
            <Input.Password
              size="large"
              placeholder="确认密码"
              value={confirm}
              onChange={(e) => { setConfirm(e.target.value); setError('') }}
              onPressEnter={handleSubmit}
              prefix={<LockOutlined />}
              autoComplete="new-password"
              name="confirm"
              style={{ fontSize: 16 }}
            />
          )}

          {error && <Alert type="error" message={error} showIcon style={{ textAlign: 'left' }} />}

          <Button
            type="primary"
            size="large"
            block
            loading={loading}
            onClick={handleSubmit}
            icon={<RocketOutlined />}
            style={{ height: 48, fontSize: 16 }}
          >
            {mode === 'login' ? '登录' : '注册'}
          </Button>
        </Space>

        <div style={{ marginTop: 16, color: '#6B7280', fontSize: 13 }}>
          {mode === 'login' ? (
            <>还没有账号？<Link onClick={() => switchMode('register')}>立即注册</Link></>
          ) : (
            <>已有账号？<Link onClick={() => switchMode('login')}>直接登录</Link></>
          )}
        </div>
      </Card>
    </div>
  )
}
