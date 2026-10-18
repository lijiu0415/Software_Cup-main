import React, { useState, useRef, useEffect } from 'react'
import { Input, Button, List, Avatar, Spin } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons'

const { TextArea } = Input

export default function ChatBox({ messages = [], onSend, loading = false, placeholder = "输入消息..." }) {
  const [input, setInput] = useState('')
  const listRef = useRef(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || loading) return
    onSend(input.trim())
    setInput('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 消息列表 */}
      <div ref={listRef} style={{ flex: 1, overflow: 'auto', padding: '0 8px', minHeight: 220 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#6B7280' }}>
            <RobotOutlined style={{ fontSize: 32, color: '#4A90F9' }} />
            <p>开始对话吧</p>
          </div>
        )}
        <List
          dataSource={messages}
          renderItem={(msg) => (
            <List.Item style={{ border: 'none', padding: '4px 0' }}>
              <div style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                width: '100%',
              }}>
                <div style={{
                  maxWidth: '82%',
                  padding: '9px 14px',
                  borderRadius: 12,
                  background: msg.role === 'user'
                    ? 'linear-gradient(135deg,#4A90F9,#0EA5E9)'
                    : 'rgba(0,0,0,0.05)',
                  border: msg.role === 'user' ? 'none' : '1px solid rgba(0,0,0,0.1)',
                  color: msg.role === 'user' ? '#fff' : '#1F2733',
                }}>
                  {msg.role === 'agent' && <Avatar size="small" icon={<RobotOutlined />} style={{ marginRight: 6, background: '#0EA5E9' }} />}
                  <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                </div>
              </div>
            </List.Item>
          )}
        />
        {loading && (
          <div style={{ textAlign: 'center', padding: 8 }}>
            <Spin size="small" />
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div style={{ display: 'flex', gap: 8, padding: '10px 0 0', borderTop: '1px solid rgba(0,0,0,0.08)' }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder={placeholder}
          autoSize={{ minRows: 1, maxRows: 3 }}
          disabled={loading}
          style={{ background: 'rgba(0,0,0,0.04)' }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} />
      </div>
    </div>
  )
}
