import React from 'react'
import { Button } from 'antd'
import { UserSwitchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'

// 未完成学习画像时的占位：提醒用户先完成画像，画像完成后展示真实内容
export default function ProfilePlaceholder() {
  const setCurrentStep = useStore((s) => s.setCurrentStep)
  const navigate = useNavigate()

  return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', padding: 48, maxWidth: 420 }}>
        <UserSwitchOutlined style={{ fontSize: 56, color: '#4A90F9', marginBottom: 16 }} />
        <div style={{ fontSize: 18, fontWeight: 700, color: '#1F2733' }}>请先完成评估问卷</div>
        <div style={{ fontSize: 13, color: '#6B7280', marginTop: 8, lineHeight: 1.6 }}>
          完成问卷生成学习画像后，本页将展示与你学习方向匹配的内容
        </div>
        <Button
          type="primary"
          style={{ marginTop: 20 }}
          onClick={() => { setCurrentStep(0); navigate('/main') }}
        >
          去完成问卷
        </Button>
      </div>
    </div>
  )
}
