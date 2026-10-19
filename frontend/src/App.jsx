import React, { useState, useEffect, useRef } from 'react'
import { HashRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Tag, Space, notification } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import useStore from './store/useStore'
import { getCourseProgress, getProfile, getLearningPath, getProfileSummary } from './api'
import Sidebar from './components/Sidebar'
import QaAssistant from './components/QaAssistant'
import HomePage from './pages/HomePage'
import ProfileModePage from './pages/ProfileModePage'
import AccessiblePage from './pages/AccessiblePage'
import { Button } from 'antd'
import DashboardPage from './pages/DashboardPage'
import MainPage from './pages/MainPage'
import ExercisePage from './pages/ExercisePage'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'
import ReportPage from './pages/ReportPage'
import ProfilePage from './pages/ProfilePage'

const { Header, Content, Sider } = Layout

// 学习天数：注册日期为第 1 天，按现实日期每天 +1
function calcStudyDay(registerDate) {
  if (!registerDate) return 1
  const reg = new Date(`${registerDate}T00:00:00`)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diff = Math.floor((today - reg) / 86400000)
  return Math.max(1, diff + 1)
}

function RequireAuth({ children }) {
  const token = useStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return children
}

function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const {
    user, questionnaire_complete, studentProfile, course, registerDate, studentId,
    setRegisterDate, setStudentProfile, setStudentName, setQuestionnaireComplete,
    setProgress, setGapCount, setDueReviewCount,
  } = useStore()
  const isLogin = location.pathname === '/'
  const dueNotifiedRef = useRef(false)

  useEffect(() => {
    if (!studentId) return
    getProfile(studentId)
      .then((res) => {
        const d = res.data
        if (!d || d.error) return
        if (d.register_date) setRegisterDate(d.register_date)
        if (d.questionnaire_complete) setQuestionnaireComplete(true)
        if (d.profiled || d.questionnaire_complete) {
          setStudentProfile({
            base_level: d.base_level,
            cognitive_style: d.cognitive_style,
            learn_preference: d.learn_preference,
            error_type: d.error_type,
            learn_speed: d.learn_speed,
            learn_goal: d.learn_goal,
            course: d.course,
          })
        } else {
          setStudentProfile({})
        }
        if (d.student_name) setStudentName(d.student_name)
      })
      .catch(() => {})
  }, [studentId])

  // 实时拉取学习总览：完成度进度 + 开放缺口数（侧边栏 / 看板共享）
  useEffect(() => {
    if (!studentId) return
    Promise.all([getCourseProgress(studentId), getLearningPath(studentId)])
      .then(([progRes, pathRes]) => {
        const courses = progRes.data.courses || []
        const total = courses.reduce((s, c) => s + (c.total || 0), 0)
        const done = courses.reduce((s, c) => s + (c.completed || 0), 0)
        setProgress(total ? Math.round((done / total) * 100) : 0)
        const path = pathRes.data.path || []
        setGapCount(path.filter((kp) => kp.mastery < 0.6).length)
      })
      .catch(() => {})
  }, [studentId, location.pathname])

  // 遗忘曲线复习提醒：进入应用时刷新待复习数，若有到期知识点弹一次通知
  useEffect(() => {
    if (!studentId) return
    getProfileSummary(studentId, studentProfile.course)
      .then((res) => {
        const due = res.data.due_count || 0
        setDueReviewCount(due)
        if (due > 0 && !dueNotifiedRef.current) {
          dueNotifiedRef.current = true
          notification.warning({
            message: '遗忘曲线复习提醒',
            description: `有 ${due} 个知识点进入复习窗口，点击前往「个人资料」查看。`,
            duration: 6,
            onClick: () => navigate('/profile'),
          })
        }
      })
      .catch(() => {})
  }, [studentId])

  // 学习天数（注册日期为第 1 天，按现实日期每天递增）
  const studyDay = calcStudyDay(registerDate)

  return (
    <Layout style={{ minHeight: '100vh', background: '#F5F7FA' }}>
      {!isLogin && (
        <Sider width={220} style={{ background: 'rgba(255,255,255,0.85)', borderRight: '1px solid rgba(0,0,0,0.08)' }}>
          <Sidebar />
        </Sider>
      )}

      <Layout style={{ background: 'transparent' }}>
        {!isLogin && (
          <Header style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0 24px', height: 64,
            background: 'rgba(255,255,255,0.6)',
            backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
            borderBottom: '1px solid rgba(0,0,0,0.08)',
          }}>
            <Space size={12} style={{ cursor: 'pointer' }} onClick={() => navigate('/dashboard')}>
              <ThunderboltOutlined style={{ fontSize: 22, color: '#0EA5E9' }} />
              <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: 1 }}>智育万象</span>
            </Space>
            <Space size={12}>
              {questionnaire_complete ? (
                <Tag>「{studentProfile.course || course}」第<span className="mono">{studyDay}</span>天</Tag>
              ) : (
                <span style={{ color: '#F5222D', fontWeight: 600 }}>待画像确认</span>
              )}
              <span style={{ color: '#6B7280' }}>
                下午好，<span style={{ color: '#1F2733', fontWeight: 600 }}>{user.name}</span>
              </span>
            </Space>
          </Header>
        )}

        <Content style={{
          padding: isLogin ? 0 : '20px 24px',
          height: isLogin ? '100vh' : 'calc(100vh - 64px)',
          overflow: 'hidden',
          background: 'transparent',
        }}>
          <Routes>
            <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
            <Route path="/main" element={<RequireAuth><MainPage /></RequireAuth>} />
            <Route path="/exercise" element={<RequireAuth><ExercisePage /></RequireAuth>} />
            <Route path="/knowledge-graph" element={<RequireAuth><KnowledgeGraphPage /></RequireAuth>} />
            <Route path="/report" element={<RequireAuth><ReportPage /></RequireAuth>} />
            <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Content>
      </Layout>

      {!isLogin && <QaAssistant />}
    </Layout>
  )
}

function LoginEntry() {
  const navigate = useNavigate()
  return (
    <div>
      <Button style={{ position: 'fixed', top: 16, left: 16, zIndex: 1000 }} onClick={() => navigate('/')}>返回模式选择</Button>
      <HomePage />
    </div>
  )
}

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<ProfileModePage />} />
        <Route path="/login" element={<LoginEntry />} />
        <Route path="/accessibility" element={<AccessiblePage />} />
        <Route path="*" element={<AppLayout />} />
      </Routes>
    </HashRouter>
  )
}
