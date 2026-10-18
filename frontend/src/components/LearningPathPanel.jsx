import React, { useEffect, useState } from 'react'
import { Card, List, Tag, Typography, Button, Space } from 'antd'
import { FlagOutlined, ArrowRightOutlined } from '@ant-design/icons'
import { getLearningPath } from '../api'

const { Text } = Typography

export default function LearningPathPanel({ studentId, onSelectKp }) {
  const [path, setPath] = useState([])

  useEffect(() => {
    fetchPath()
  }, [studentId])

  const fetchPath = async () => {
    if (!studentId) return
    try {
      const res = await getLearningPath(studentId)
      setPath(res.data.path || [])
    } catch (err) {
      // 静默失败
    }
  }

  const topPath = path.slice(0, 5)

  if (topPath.length === 0) {
    return (
      <Card title={<Space><FlagOutlined /> 学习路径</Space>} size="small">
        <div style={{ textAlign: 'center', padding: 16, color: '#999', fontSize: 12 }}>
          暂无推荐路径
        </div>
      </Card>
    )
  }

  return (
    <Card
      title={<Space><FlagOutlined style={{ color: '#1890ff' }} /> 推荐学习</Space>}
      size="small"
      style={{ marginTop: 16 }}
    >
      <List
        size="small"
        dataSource={topPath}
        renderItem={(kp, i) => (
          <List.Item
            style={{ padding: '6px 0', cursor: 'pointer' }}
            onClick={() => onSelectKp?.(kp)}
          >
            <Space>
              <Tag color="blue" style={{ fontSize: 10 }}>{i + 1}</Tag>
              <Text style={{ fontSize: 12 }} ellipsis>{kp.name}</Text>
            </Space>
          </List.Item>
        )}
      />
      {path.length > 5 && (
        <div style={{ textAlign: 'center', padding: '4px 0' }}>
          <Text type="secondary" style={{ fontSize: 11 }}>还有 {path.length - 5} 个知识点</Text>
        </div>
      )}
    </Card>
  )
}
