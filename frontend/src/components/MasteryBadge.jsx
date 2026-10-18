import React from 'react'
import { Tag, Progress, Tooltip } from 'antd'
import { CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'

export default function MasteryBadge({ mastery, showProgress = false, size = 'small' }) {
  const percent = Math.round((mastery || 0) * 100)

  let color, icon, text
  if (mastery >= 0.6) {
    color = 'success'
    icon = <CheckCircleOutlined />
    text = '已掌握'
  } else if (mastery >= 0.3) {
    color = 'warning'
    icon = <ExclamationCircleOutlined />
    text = '部分掌握'
  } else {
    color = 'error'
    icon = <CloseCircleOutlined />
    text = '未掌握'
  }

  if (showProgress) {
    return (
      <Tooltip title={`${text} (${percent}%)`}>
        <Progress
          percent={percent}
          size={size === 'small' ? 'small' : 'default'}
          strokeColor={mastery >= 0.6 ? '#52c41a' : mastery >= 0.3 ? '#faad14' : '#ff4d4f'}
          format={() => `${percent}%`}
          style={{ width: 120 }}
        />
      </Tooltip>
    )
  }

  return (
    <Tag color={color} icon={icon}>
      {text} {percent}%
    </Tag>
  )
}
