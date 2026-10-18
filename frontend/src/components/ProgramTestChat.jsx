import React, { useState, useEffect, useRef } from 'react'
import { Button, Input, Space, Tag, Spin, Empty, Avatar, message } from 'antd'
import { SendOutlined, RobotOutlined, ReloadOutlined, CodeOutlined } from '@ant-design/icons'
import { startProgramTest, gradeProgramTest } from '../api'

const { TextArea } = Input

const CORRECTNESS_COLOR = { '正确': 'green', '部分正确': 'orange', '错误': 'red', '无法判定': 'default' }
const FIELD_LABELS = { base_level: '基础', learn_speed: '速度', cognitive_style: '认知风格', learn_preference: '学习偏好', error_type: '易错类型' }

export default function ProgramTestChat({ chapterId, studentId }) {
  const [messages, setMessages] = useState([])
  const [qInfo, setQInfo] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [phase, setPhase] = useState('') // 'generating' | 'grading'
  const listRef = useRef(null)

  const generate = async () => {
    if (!studentId || !chapterId) return
    setLoading(true)
    setPhase('generating')
    setQInfo(null)
    setInput('')
    try {
      const res = await startProgramTest(studentId, chapterId)
      const d = res.data
      setQInfo(d)
      setMessages([{ role: 'assistant', kind: 'question', content: d.question, kp_id: d.kp_id, kp_name: d.kp_name }])
    } catch (e) {
      message.error(e?.response?.data?.detail || '编程题生成失败，请重试')
    } finally {
      setLoading(false)
      setPhase('')
    }
  }

  // 章节切换 / 首次挂载：重置对话并出题
  useEffect(() => {
    setMessages([])
    setQInfo(null)
    setInput('')
    if (chapterId) generate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterId])

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages, loading])

  const handleGrade = async () => {
    const ans = input.trim()
    if (!ans || !qInfo || loading) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', kind: 'answer', content: ans }])
    setLoading(true)
    setPhase('grading')
    try {
      const res = await gradeProgramTest(studentId, chapterId, {
        question: qInfo.question,
        kp_id: qInfo.kp_id,
        kp_name: qInfo.kp_name,
        student_answer: ans,
      })
      setMessages((prev) => [...prev, { role: 'assistant', kind: 'grade', content: res.data.feedback, meta: res.data }])
    } catch (e) {
      message.error(e?.response?.data?.detail || '批改失败，请重试')
    } finally {
      setLoading(false)
      setPhase('')
    }
  }

  const renderBubble = (msg, i) => {
    if (msg.role === 'user') {
      return (
        <div key={i} style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
          <div style={{ maxWidth: '85%', padding: '10px 14px', borderRadius: 12, background: 'linear-gradient(135deg,#4A90F9,#0EA5E9)', color: '#fff', whiteSpace: 'pre-wrap', fontFamily: 'Consolas, monospace', fontSize: 13 }}>{msg.content}</div>
        </div>
      )
    }
    const meta = msg.meta || {}
    return (
      <div key={i} style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 12 }}>
        <div style={{ maxWidth: '92%', padding: '10px 14px', borderRadius: 12, background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.08)' }}>
          <Space size={6} style={{ marginBottom: 4, display: 'flex', alignItems: 'center' }}>
            <Avatar size="small" icon={<RobotOutlined />} style={{ background: '#0EA5E9' }} />
            <span style={{ fontSize: 11, color: '#6B7280' }}>编程测试Agent</span>
            {msg.kind === 'question' && msg.kp_id && <Tag color="blue" style={{ fontSize: 11, marginRight: 0 }}>{msg.kp_name || msg.kp_id}</Tag>}
          </Space>
          {msg.kind === 'question' ? (
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>{msg.content}</div>
          ) : (
            <div>
              <div style={{ marginBottom: 8 }}>
                <Tag color={CORRECTNESS_COLOR[meta.correctness] || 'default'}>{meta.correctness || '批改'}</Tag>
                {meta.kp_name && <Tag color="blue">{meta.kp_name}</Tag>}
              </div>
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>{msg.content}</div>
              {meta.standard_answer && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 12, color: '#6B7280' }}>标准答案：</div>
                  <pre style={{ background: 'rgba(0,0,0,0.05)', padding: 10, borderRadius: 8, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 12, margin: '4px 0 0', fontFamily: 'Consolas, monospace' }}>{meta.standard_answer}</pre>
                </div>
              )}
              {meta.profile_changes && meta.profile_changes.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
                  <span style={{ fontSize: 11, color: '#6B7280' }}>画像已更新：</span>
                  {meta.profile_changes.map((c, j) => (
                    <Tag key={j} color="cyan" style={{ fontSize: 11 }}>{FIELD_LABELS[c.field] || c.field} {c.old} → {c.new}</Tag>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div style={{ border: '1px solid rgba(14,165,233,0.25)', borderRadius: 12, padding: 12, background: 'rgba(14,165,233,0.02)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Space size={6}>
          <CodeOutlined style={{ color: '#0EA5E9' }} />
          <span style={{ fontWeight: 700, fontSize: 14 }}>编程实战</span>
          <span style={{ fontSize: 12, color: '#6B7280' }}>· Agent出题 · 对话式作答 · 不计入分值</span>
        </Space>
        <Button size="small" icon={<ReloadOutlined />} onClick={generate} loading={loading && phase === 'generating'} disabled={loading}>换一题</Button>
      </div>

      <div ref={listRef} style={{ maxHeight: 360, overflow: 'auto', padding: '4px 2px', minHeight: 120 }}>
        {messages.length === 0 && !loading && (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Agent 正在准备编程题…" />
        )}
        {messages.map(renderBubble)}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 12 }}>
            <div style={{ padding: '10px 14px', borderRadius: 12, background: 'rgba(0,0,0,0.04)', color: '#6B7280', fontSize: 13 }}>
              <Spin size="small" style={{ marginRight: 8 }} />
              {phase === 'grading' ? 'Agent 正在批改…' : 'Agent 正在出题…'}
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleGrade() } }}
          placeholder="在此编写/粘贴你的代码答案…（Enter发送，Shift+Enter换行）"
          autoSize={{ minRows: 2, maxRows: 6 }}
          disabled={loading || !qInfo}
          style={{ flex: 1, fontFamily: 'Consolas, monospace' }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={handleGrade} loading={loading && phase === 'grading'} disabled={loading || !qInfo}>提交</Button>
      </div>
    </div>
  )
}
