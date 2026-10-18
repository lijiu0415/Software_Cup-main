import React, { useState, useEffect, useRef } from 'react'
import { Button, Input, Space, Tooltip, Popconfirm, message, Spin, Tag, Avatar } from 'antd'
import {
  MessageOutlined, DownOutlined, DeleteOutlined, SendOutlined, RobotOutlined, AuditOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import useStore from '../store/useStore'
import { qaChatStream, getQaHistory, deleteQaHistory, evaluateProfile } from '../api'
import { glassStyle } from '../styles/theme'

const { TextArea } = Input

function MarkdownBlock({ content }) {
  return (
    <div style={{ fontSize: 13, lineHeight: 1.7, wordBreak: 'break-word' }}>
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={{
          pre: ({ children }) => (
            <pre style={{ background: 'rgba(0,0,0,0.05)', padding: 12, borderRadius: 8, overflow: 'auto', fontSize: 12, margin: '8px 0' }}>
              {children}
            </pre>
          ),
          code: ({ children }) => (
            <code style={{ background: 'rgba(14,165,233,0.10)', color: '#0284C7', padding: '2px 6px', borderRadius: 4, fontFamily: 'inherit' }}>
              {children}
            </code>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

const FIELD_LABELS = {
  base_level: '基础', learn_speed: '速度', cognitive_style: '认知风格',
  learn_preference: '学习偏好', error_type: '易错类型',
}

export default function QaAssistant() {
  const { studentId, studentProfile, setStudentProfile } = useStore()
  const course = studentProfile?.course
  const [collapsed, setCollapsed] = useState(true)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState('') // 'retrieving' | 'generating'
  const [evaluating, setEvaluating] = useState(false)
  const listRef = useRef(null)
  const streamBufferRef = useRef('')
  const flushTimerRef = useRef(null)

  // 流式渲染节流：累积 chunk，定时刷入状态，形成平滑打字机效果
  const flushStream = () => {
    const text = streamBufferRef.current
    setMessages((prev) => {
      if (prev.length === 0) return prev
      const next = [...prev]
      next[next.length - 1] = { ...next[next.length - 1], content: text }
      return next
    })
  }

  const stopFlush = () => {
    if (flushTimerRef.current) {
      clearInterval(flushTimerRef.current)
      flushTimerRef.current = null
    }
  }

  // 卸载时清理流式定时器
  useEffect(() => () => stopFlush(), [])

  // 加载历史
  useEffect(() => {
    if (!studentId) return
    getQaHistory(studentId)
      .then((res) => {
        const list = res.data.messages || []
        setMessages(list.map((m) => ({ role: m.role, content: m.content, sources: m.sources || [] })))
      })
      .catch(() => {})
  }, [studentId])

  // 自动滚动到底部
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages, loading, stage, collapsed])

  const handleSend = async () => {
    const q = input.trim()
    if (!q || loading || !studentId) return
    setInput('')
    setLoading(true)
    setStage('retrieving')
    streamBufferRef.current = ''
    stopFlush()
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: q, sources: [] },
      { role: 'assistant', content: '', sources: [] },
    ])

    await qaChatStream(studentId, q, {
      onStart: () => {
        setStage('generating')
        if (!flushTimerRef.current) flushTimerRef.current = setInterval(flushStream, 50)
      },
      onChunk: (chunk) => {
        streamBufferRef.current += chunk
      },
      onDone: (event) => {
        stopFlush()
        const final = event.reply || streamBufferRef.current
        const sources = event.sources || []
        setMessages((prev) => {
          const next = [...prev]
          next[next.length - 1] = { ...next[next.length - 1], content: final, sources }
          return next
        })
        setLoading(false)
        setStage('')
      },
      onError: (msg) => {
        stopFlush()
        message.error(msg || '答疑请求失败，请检查后端服务是否启动')
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          next[next.length - 1] = { ...last, content: last.content || '抱歉，暂时无法回答，请稍后重试。' }
          return next
        })
        setLoading(false)
        setStage('')
      },
    })
  }

  const handleEvaluate = async () => {
    if (!studentId || evaluating) return
    setEvaluating(true)
    try {
      const res = await evaluateProfile(studentId)
      const d = res.data
      if (d.profile && Object.keys(d.profile).length > 0) setStudentProfile(d.profile)
      if (d.evaluated && d.record) {
        const changes = d.record.changes || []
        if (changes.length > 0) {
          const desc = changes.map((c) => `${FIELD_LABELS[c.field] || c.field}→${c.value}`).join('、')
          message.success(`画像已更新：${desc}`)
        } else {
          message.info('已评估，无需调整画像')
        }
      } else {
        message.info(d.reason || '近期提问不足，暂无法评估')
      }
    } catch {
      message.error('评估失败，请稍后重试')
    } finally {
      setEvaluating(false)
    }
  }

  const handleClear = async () => {
    try {
      await deleteQaHistory(studentId)
      setMessages([])
      message.success('对话已清空')
    } catch {
      message.error('清空失败，请稍后重试')
    }
  }

  // 收起态：右下角圆钮（叠在「学习画像」圆钮上方）
  if (collapsed) {
    return (
      <Tooltip title="答疑助手" placement="left">
        <Button
          type="primary"
          shape="circle"
          size="large"
          icon={<MessageOutlined />}
          onClick={() => setCollapsed(false)}
          style={{ position: 'fixed', right: 24, bottom: 88, zIndex: 1001, boxShadow: '0 0 20px rgba(14,165,233,0.5)' }}
        />
      </Tooltip>
    )
  }

  return (
    <div
      style={{
        position: 'fixed', right: 24, bottom: 88, zIndex: 1001,
        width: 'min(50vw, 460px)', height: 'min(65vh, 600px)',
        ...glassStyle, padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}
    >
      {/* 头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid rgba(0,0,0,0.08)' }}>
        <Space size={8}>
          <RobotOutlined style={{ color: '#0EA5E9', fontSize: 18 }} />
          <span style={{ fontSize: 15, fontWeight: 700 }}>答疑助手</span>
          {course && <Tag color="cyan" style={{ fontSize: 11 }}>{course}</Tag>}
        </Space>
        <Space size={4}>
          <Tooltip title="评估画像"><Button size="small" type="text" icon={<AuditOutlined />} onClick={handleEvaluate} loading={evaluating} /></Tooltip>
          <Popconfirm title="清空全部答疑记录？" okText="清空" cancelText="取消" onConfirm={handleClear}>
            <Tooltip title="清空对话"><Button size="small" type="text" icon={<DeleteOutlined />} /></Tooltip>
          </Popconfirm>
          <Tooltip title="收起"><Button size="small" type="text" icon={<DownOutlined />} onClick={() => setCollapsed(true)} /></Tooltip>
        </Space>
      </div>

      {/* 消息区 */}
      <div ref={listRef} style={{ flex: 1, overflow: 'auto', padding: '12px 16px', minHeight: 0 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '48px 16px', color: '#6B7280' }}>
            <RobotOutlined style={{ fontSize: 40, marginBottom: 12, color: '#0EA5E9' }} />
            <div style={{ fontSize: 13 }}>学习过程中有疑问？随时问我～</div>
            <div style={{ fontSize: 12, marginTop: 6 }}>我会结合课程讲义与你的学习画像解答</div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 12 }}>
            <div style={{
              maxWidth: '85%',
              padding: '10px 14px',
              borderRadius: 12,
              background: msg.role === 'user' ? 'linear-gradient(135deg,#4A90F9,#0EA5E9)' : 'rgba(0,0,0,0.04)',
              border: msg.role === 'user' ? 'none' : '1px solid rgba(0,0,0,0.08)',
              color: msg.role === 'user' ? '#fff' : '#1F2733',
            }}>
              {msg.role === 'assistant' && (
                <Space size={6} style={{ marginBottom: 4, display: 'flex', alignItems: 'center' }}>
                  <Avatar size="small" icon={<RobotOutlined />} style={{ background: '#0EA5E9' }} />
                  <span style={{ fontSize: 11, color: '#6B7280' }}>答疑导师</span>
                </Space>
              )}

              {msg.role === 'assistant' && !msg.content ? (
                <div style={{ color: '#6B7280', fontSize: 13 }}>
                  <Spin size="small" style={{ marginRight: 8 }} />
                  {stage === 'retrieving' ? '正在检索讲义…' : '正在回答…'}
                </div>
              ) : msg.role === 'assistant' ? (
                <MarkdownBlock content={msg.content} />
              ) : (
                <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
              )}

              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
                  <span style={{ fontSize: 11, color: '#6B7280' }}>出处：</span>
                  {msg.sources.slice(0, 3).map((s, j) => (
                    <Tag key={j} color="geekblue" style={{ fontSize: 10, marginRight: 0 }}>
                      {s.type === 'chapter' ? '讲义' : s.type === 'exercise' ? '习题' : s.type === 'code' ? '代码' : '资料'} · {s.source}
                    </Tag>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 输入区 */}
      <div style={{ display: 'flex', gap: 8, padding: '10px 12px', borderTop: '1px solid rgba(0,0,0,0.08)' }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder="输入课程相关问题…（Enter发送，Shift+Enter换行）"
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={loading}
          style={{ flex: 1 }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading}>发送</Button>
      </div>
    </div>
  )
}
