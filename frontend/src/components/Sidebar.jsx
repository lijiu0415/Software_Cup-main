import React from 'react'
import { Menu, Progress, Badge } from 'antd'
import {
  DashboardOutlined,
  BookOutlined,
  ExperimentOutlined,
  ShareAltOutlined,
  ProfileOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import useStore from '../store/useStore'

const MENU_ITEMS = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '智育万象' },
  { key: '/main', icon: <BookOutlined />, label: '课程航行' },
  { key: '/exercise', icon: <ExperimentOutlined />, label: '题库操练' },
  { key: '/knowledge-graph', icon: <ShareAltOutlined />, label: '知识航图' },
  { key: '/report', icon: <ProfileOutlined />, label: '学习档案' },
  { key: '/profile', icon: <UserOutlined />, label: '个人资料' },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, questionnaire_complete, studentProfile, course, progress, dueReviewCount } = useStore()

  return (
    <div
      className="sidebar"
      style={{ height: '100vh', display: 'flex', flexDirection: 'column', padding: '16px 12px' }}
    >
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        onClick={({ key }) => navigate(key)}
        items={MENU_ITEMS.map((it) =>
          it.key === '/profile' && dueReviewCount > 0
            ? { ...it, label: <span>{it.label}<Badge count={dueReviewCount} size="small" style={{ marginLeft: 6, backgroundColor: '#6E2733' }} /></span> }
            : it
        )}
        style={{ background: 'transparent', border: 'none', flex: 1 }}
      />

      {/* 底部迷你学习画像卡片 */}
      <div
        style={{
          padding: 14,
          borderRadius: 12,
          background: 'rgba(0,0,0,0.04)',
          border: '1px solid rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div
            style={{
              width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
              background: 'linear-gradient(135deg,#4A90F9,#0EA5E9)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <UserOutlined style={{ color: '#fff' }} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 700, color: '#fff', fontSize: 14 }}>{user.name}</div>
            {questionnaire_complete ? (
              <div style={{ color: '#6B7280', fontSize: 12 }}>{studentProfile.course || course}</div>
            ) : (
              <div style={{ color: '#F5222D', fontSize: 12 }}>待画像确认</div>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#6B7280', marginBottom: 4 }}>
          <span>完成度</span>
          <span className="mono" style={{ color: '#0EA5E9' }}>{progress}%</span>
        </div>
        <Progress
          percent={progress}
          showInfo={false}
          strokeColor={{ '0%': '#4A90F9', '100%': '#0EA5E9' }}
          trailColor="rgba(0,0,0,0.1)"
          size="small"
        />
      </div>
    </div>
  )
}
