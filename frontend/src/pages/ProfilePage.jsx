import React, { useState, useEffect, useRef } from 'react'
import {
  Card, Row, Col, Avatar, Tag, Progress, Button, InputNumber, Space, Typography,
  message, Modal, Timeline, Spin, Empty, Badge, Divider, Tooltip, Upload,
} from 'antd'
import {
  UserOutlined,
  LogoutOutlined,
  UserDeleteOutlined,
  HistoryOutlined,
  ReloadOutlined,
  PlayCircleFilled,
  PauseCircleFilled,
  ClockCircleOutlined,
  AimOutlined,
  BellOutlined,
  CheckOutlined,
  ReadOutlined,
  BookOutlined,
  UploadOutlined,
  EyeOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import {
  getProfileSummary, updateProfileSettings, completePomodoro, markKpReviewed,
  getCourseProgress, getEvaluationHistory, deleteAccount, resetStudent,
  uploadTextbook, getTextbooks, deleteTextbook, switchCourse,
} from '../api'

const { Text, Title } = Typography

const FIELD_LABELS = {
  base_level: '基础水平',
  learn_speed: '学习速度',
  cognitive_style: '认知风格',
  learn_preference: '学习偏好',
  error_type: '易错类型',
  learn_goal: '学习目标',
}

// 内置课程教材（书架始终展示）；「正在学习」由当前课程动态决定
const BUILTIN_TEXTBOOKS = [
  { id: 'builtin-ai', title: '人工智能导论' },
  { id: 'builtin-sc', title: '软件安全技术' },
]

// 学习天数：注册日期为第 1 天，按现实日期每天 +1
function calcStudyDay(registerDate) {
  if (!registerDate) return 1
  const reg = new Date(`${registerDate}T00:00:00`)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diff = Math.floor((today - reg) / 86400000)
  return Math.max(1, diff + 1)
}

function fmt(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, '0')
  const s = String(sec % 60).padStart(2, '0')
  return `${m}:${s}`
}

export default function ProfilePage() {
  const navigate = useNavigate()
  const {
    user, studentId, studentName, studentProfile, course, registerDate, questionnaire_complete,
    clearChatHistory, clearToken, setStudentId, setStudentName, setStudentProfile,
    setQuestionnaireComplete, setCurrentStep, setDueReviewCount,
  } = useStore()

  const [courses, setCourses] = useState([])
  const [todayCompleted, setTodayCompleted] = useState(0)
  const [dueReviews, setDueReviews] = useState([])
  const [pomodoroToday, setPomodoroToday] = useState({ count: 0, focus_minutes: 0 })
  const [textbooks, setTextbooks] = useState([])
  const [loading, setLoading] = useState(true)

  // 设置
  const [dailyGoal, setDailyGoal] = useState(3)
  const [focusMin, setFocusMin] = useState(25)
  const [breakMin, setBreakMin] = useState(5)

  // 番茄钟
  const [mode, setMode] = useState('focus') // focus | break
  const [secondsLeft, setSecondsLeft] = useState(25 * 60)
  const [running, setRunning] = useState(false)
  const timerInitRef = useRef(false)

  // 评估历史
  const [evalHistory, setEvalHistory] = useState([])
  const [evalLoading, setEvalLoading] = useState(false)
  const [evalModalOpen, setEvalModalOpen] = useState(false)

  const loadSummary = async () => {
    try {
      const currentCourse = studentProfile?.course || '人工智能导论'
      const [sum, prog] = await Promise.all([
        getProfileSummary(studentId, currentCourse),
        getCourseProgress(studentId),
      ])
      const s = sum.data.settings || {}
      setDailyGoal(s.daily_goal ?? 3)
      setFocusMin(s.focus_min ?? 25)
      setBreakMin(s.break_min ?? 5)
      setTodayCompleted(sum.data.today_completed || 0)
      setDueReviews(sum.data.due_reviews || [])
      setPomodoroToday(sum.data.pomodoro_today || { count: 0, focus_minutes: 0 })
      setCourses(prog.data.courses || [])
      setDueReviewCount(sum.data.due_count || 0)

      if (!timerInitRef.current) {
        timerInitRef.current = true
        setMode('focus')
        setSecondsLeft((s.focus_min ?? 25) * 60)
      }
    } catch {
      message.error('加载个人资料失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (studentId) {
      loadSummary()
      loadTextbooks()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId])

  const loadTextbooks = async () => {
    try {
      const res = await getTextbooks(studentId)
      setTextbooks(res.data.items || [])
    } catch {
      // 书架加载失败不阻塞整页
    }
  }

  // 番茄钟倒计时
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000)
    return () => clearInterval(id)
  }, [running])

  // 计时结束处理
  useEffect(() => {
    if (!running || secondsLeft > 0) return
    setRunning(false)
    if (mode === 'focus') {
      completePomodoro(studentId, { focus_min: focusMin, break_min: breakMin }, studentProfile?.course)
        .then((res) => setPomodoroToday(res.data))
        .catch(() => {})
      message.success(`专注完成！休息 ${breakMin} 分钟吧`)
      setMode('break')
      setSecondsLeft(breakMin * 60)
    } else {
      message.success('休息结束，开始新一轮专注！')
      setMode('focus')
      setSecondsLeft(focusMin * 60)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [secondsLeft, running, mode])

  const switchMode = (m) => {
    setRunning(false)
    setMode(m)
    setSecondsLeft((m === 'focus' ? focusMin : breakMin) * 60)
  }

  const saveSettings = async () => {
    try {
      await updateProfileSettings(studentId, {
        daily_goal: dailyGoal, focus_min: focusMin, break_min: breakMin,
      }, studentProfile?.course)
      message.success('设置已保存')
      if (!running) {
        setMode('focus')
        setSecondsLeft(focusMin * 60)
      }
    } catch {
      message.error('保存失败')
    }
  }

  const handleReviewed = async (kpId) => {
    try {
      await markKpReviewed(studentId, kpId)
      message.success('已记录复习')
      const sum = await getProfileSummary(studentId, studentProfile?.course)
      setDueReviews(sum.data.due_reviews || [])
      setTodayCompleted(sum.data.today_completed || 0)
      setDueReviewCount(sum.data.due_count || 0)
    } catch {
      message.error('操作失败')
    }
  }

  const handleUploadTextbook = async ({ file, onSuccess, onError }) => {
    try {
      const res = await uploadTextbook(studentId, file)
      onSuccess(res.data)
      message.success('上传成功')
      loadTextbooks()
    } catch (e) {
      onError(e)
      message.error(e?.response?.data?.detail || '上传失败')
    }
  }

  const handleDeleteTextbook = (id) => {
    Modal.confirm({
      title: '删除教材',
      content: '确定从书架删除该教材？',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteTextbook(studentId, id)
          message.success('已删除')
          loadTextbooks()
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const formatSize = (bytes) => {
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`
    return `${Math.max(1, Math.round(bytes / 1024))} KB`
  }

  const typeColor = (t) =>
    ({ pdf: '#EF4444', doc: '#0284C7', docx: '#0284C7', ppt: '#E19B5A', pptx: '#E19B5A',
       txt: '#6B7280', md: '#6B7280', markdown: '#6B7280', xls: '#10B981', xlsx: '#10B981',
       png: '#10B981', jpg: '#10B981', jpeg: '#10B981', gif: '#10B981' }[t] || '#0284C7')

  // 书籍封面配色：正在学习→蓝，内置课程教材→栗，上传教材→按文件类型
  const coverColor = (book) => {
    if (book.learning) return '#0284C7'
    if (book.builtin) return '#6E2733'
    return typeColor(book.file_type)
  }

  const loadEvaluations = async () => {
    setEvalLoading(true)
    try {
      const res = await getEvaluationHistory(studentId)
      setEvalHistory(res.data.history || [])
    } catch {
      setEvalHistory([])
    } finally {
      setEvalLoading(false)
    }
  }

  const handleLogout = () => {
    clearChatHistory()
    clearToken()
    setStudentId('')
    setStudentName('')
    setStudentProfile({})
    setDueReviewCount(0)
    navigate('/')
  }

  const handleDeleteAccount = () => {
    Modal.confirm({
      title: '用户注销',
      content: '注销后不可撤回，请问是否继续？',
      okText: '确认注销',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const { data } = await deleteAccount(studentName || user.name)
          if (data.success) {
            message.success('用户已注销')
            clearChatHistory()
            clearToken()
            setStudentId('')
            setStudentName('')
            setStudentProfile({})
            setQuestionnaireComplete(false)
            setDueReviewCount(0)
            navigate('/')
          } else {
            message.error(data.message || '注销失败')
          }
        } catch {
          message.error('注销请求失败，请检查服务是否已启动')
        }
      },
    })
  }

  const handleReset = () => {
    Modal.confirm({
      title: '确认重置',
      content: '你的学习画像、答疑记录和知识点掌握度将全部清空，确定继续？',
      okText: '确认重置',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await resetStudent(studentId)
          clearChatHistory()
          setStudentProfile({})
          setQuestionnaireComplete(false)
          setCurrentStep(0)
          setDueReviewCount(0)
          navigate('/main')
          message.success('数据已重置')
        } catch {
          message.error('重置失败，请稍后重试')
        }
      },
    })
  }

  const handleSwitchCourse = async (title) => {
    const currentCourse = studentProfile?.course || '人工智能导论'
    if (title === currentCourse) return
    try {
      const res = await switchCourse(studentId, title)
      const { profile: p, questionnaire_complete: complete, settings } = res.data
      setStudentProfile(p || {})
      setQuestionnaireComplete(!!complete)
      if (settings) {
        setDailyGoal(settings.daily_goal ?? 3)
        setFocusMin(settings.focus_min ?? 25)
        setBreakMin(settings.break_min ?? 5)
      }
      if (!complete) {
        // 新课程未完成问卷：门禁到该课程问卷（回到课程航行第 0 步）
        setCurrentStep(0)
        navigate('/main')
        message.info(`请先完成《${title}》的调研问卷`)
        return
      }
      message.success(`已切换到《${title}》`)
      loadSummary()
    } catch (e) {
      message.error(e?.response?.data?.detail || '切换课程失败')
    }
  }

  const profile = studentProfile || {}
  const currentCourse = profile.course || '人工智能导论'
  const profileFields = [
    { key: 'base_level', value: profile.base_level, numeric: true },
    { key: 'learn_speed', value: profile.learn_speed, numeric: true },
    { key: 'cognitive_style', value: profile.cognitive_style },
    { key: 'learn_preference', value: profile.learn_preference },
    { key: 'error_type', value: profile.error_type },
    { key: 'learn_goal', value: profile.learn_goal },
  ]

  const goalProgress = dailyGoal ? Math.min(100, Math.round((todayCompleted / dailyGoal) * 100)) : 0
  const timerTotal = (mode === 'focus' ? focusMin : breakMin) * 60
  const timerPercent = timerTotal ? Math.round((1 - secondsLeft / timerTotal) * 100) : 0

  // 书架统一列表：内置课程教材 + 用户上传教材（「正在学习」由当前课程决定）
  const books = [
    ...BUILTIN_TEXTBOOKS.map((b) => ({ ...b, builtin: true, learning: b.title === currentCourse })),
    ...textbooks.map((t) => ({ ...t, builtin: false, learning: false })),
  ]

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 120 }}><Spin size="large" /></div>
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', paddingRight: 4 }}>
      {/* 头部：个人资料（紧凑单行 + 六维画像横条） */}
      <Card style={{ marginBottom: 16, borderRadius: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
          <Avatar size={56} icon={<UserOutlined />} style={{ background: 'linear-gradient(135deg,#4A90F9,#0EA5E9)', flexShrink: 0 }} />
          <div style={{ minWidth: 200 }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#1F2733' }}>{user.name}</div>
            <div style={{ marginTop: 2, fontSize: 13, color: '#6B7280' }}>
              {questionnaire_complete ? (
                <span>
                  当前课程 · <Text strong style={{ color: '#0284C7' }}>{profile.course || course}</Text>
                  <span style={{ marginLeft: 12 }}>已学习第 <span className="mono" style={{ color: '#1F2733' }}>{calcStudyDay(registerDate)}</span> 天</span>
                </span>
              ) : (
                <span style={{ color: '#F5222D', fontWeight: 600 }}>待画像确认</span>
              )}
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 300, display: 'flex', flexWrap: 'wrap', gap: '8px 20px', justifyContent: 'flex-end' }}>
            {profileFields.map((f) => (
              <div key={f.key} style={{ minWidth: 88 }}>
                <div style={{ fontSize: 11, color: '#6B7280' }}>{FIELD_LABELS[f.key] || f.key}</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#1F2733', marginTop: 2 }}>
                  {questionnaire_complete && f.value != null ? (
                    f.numeric ? `${f.value} / 5` : f.value
                  ) : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <Row gutter={[16, 16]} align="stretch">
        {/* 左列：学习进度 + 遗忘曲线复习（复习卡自适应撑满，避免底部留白） */}
        <Col xs={24} lg={12}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%' }}>
            <Card title={<span><ReadOutlined style={{ color: '#0284C7', marginRight: 6 }} />学习进度</span>} style={{ borderRadius: 14 }}>
              {courses.length === 0 ? (
                <Empty description="暂无课程进度数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                courses.map((c) => (
                  <div key={c.course} style={{ marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                      <span style={{ color: '#1F2733' }}>{c.course}</span>
                      <span className="mono" style={{ color: '#0284C7' }}>{c.completed}/{c.total} · {c.progress}%</span>
                    </div>
                    <Progress percent={c.progress} showInfo={false} strokeColor={{ '0%': '#6EBDFE', '100%': '#0284C7' }} trailColor="rgba(0,0,0,0.08)" size="small" />
                  </div>
                ))
              )}
            </Card>

            <Card
              title={
                <span>
                  <BellOutlined style={{ color: '#6E2733', marginRight: 6 }} />遗忘曲线复习
                  <Badge count={dueReviews.length} size="small" style={{ marginLeft: 8, backgroundColor: '#6E2733' }} />
                </span>
              }
              style={{ borderRadius: 14, flex: 1, display: 'flex', flexDirection: 'column' }}
              styles={{ body: { flex: 1, overflow: 'auto' } }}
            >
              {dueReviews.length === 0 ? (
                <Empty description="暂无到期复习的知识点" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <div>
                  <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 10 }}>
                    根据艾宾浩斯遗忘曲线，以下知识点已进入复习窗口：
                  </div>
                  {dueReviews.map((d) => (
                    <div key={d.kp_id} style={{ padding: '10px 12px', marginBottom: 10, borderRadius: 10, background: 'rgba(110,39,51,0.05)', border: '1px solid rgba(110,39,51,0.15)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                        <div style={{ minWidth: 0 }}>
                          <Text strong style={{ fontSize: 13, color: '#1F2733' }}>{d.name}</Text>
                          <div style={{ fontSize: 12, color: '#6B7280', marginTop: 2 }}>
                            {d.chapter} · 已过 <span className="mono">{d.days_since}</span> 天 · 第 {d.review_count + 1} 次复习窗口
                          </div>
                        </div>
                        <Button size="small" type="primary" ghost icon={<CheckOutlined />} onClick={() => handleReviewed(d.kp_id)}>
                          已复习
                        </Button>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                        <Progress percent={d.retention} size="small" showInfo={false} strokeColor="#6E2733" trailColor="rgba(0,0,0,0.08)" style={{ flex: 1, margin: 0 }} />
                        <span className="mono" style={{ fontSize: 12, color: '#6E2733' }}>记忆保持 {d.retention}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </Col>

        {/* 右列：番茄钟 + 每日学习目标（目标卡自适应撑满，避免底部留白） */}
        <Col xs={24} lg={12}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%' }}>
            <Card
              title={<span><ClockCircleOutlined style={{ color: '#1F277B', marginRight: 6 }} />番茄钟</span>}
              style={{ borderRadius: 14 }}
              extra={
                <Space size={4}>
                  <InputNumber size="small" min={1} max={180} value={focusMin} onChange={(v) => setFocusMin(v || 25)} onBlur={saveSettings} style={{ width: 64 }} /> 专注
                  <InputNumber size="small" min={0} max={60} value={breakMin} onChange={(v) => setBreakMin(v || 0)} onBlur={saveSettings} style={{ width: 64 }} /> 休息
                </Space>
              }
            >
              <div style={{ textAlign: 'center' }}>
                <Space style={{ marginBottom: 8 }}>
                  <Button type={mode === 'focus' ? 'primary' : 'default'} size="small" onClick={() => switchMode('focus')}>专注</Button>
                  <Button type={mode === 'break' ? 'primary' : 'default'} size="small" onClick={() => switchMode('break')}>休息</Button>
                </Space>
                <div style={{ fontSize: 50, fontWeight: 800, fontFamily: 'Consolas, monospace', color: mode === 'focus' ? '#1F277B' : '#E19B5A', lineHeight: 1.1 }}>
                  {fmt(secondsLeft)}
                </div>
                <Progress
                  type="circle"
                  percent={timerPercent}
                  width={110}
                  showInfo={false}
                  strokeColor={mode === 'focus' ? { '0%': '#6EBDFE', '100%': '#1F277B' } : { '0%': '#FEB97B', '100%': '#E19B5A' }}
                  trailColor="rgba(0,0,0,0.08)"
                />
                <div style={{ marginTop: 10 }}>
                  <Button
                    type="primary"
                    size="large"
                    icon={running ? <PauseCircleFilled /> : <PlayCircleFilled />}
                    onClick={() => setRunning((r) => !r)}
                    style={{ background: mode === 'focus' ? '#1F277B' : '#E19B5A', borderColor: 'transparent' }}
                  >
                    {running ? '暂停' : '开始'}
                  </Button>
                </div>
                <div style={{ marginTop: 10, fontSize: 12, color: '#6B7280' }}>
                  今日已专注 <span className="mono" style={{ color: '#1F2733' }}>{pomodoroToday.count}</span> 次 ·{' '}
                  <span className="mono" style={{ color: '#1F2733' }}>{pomodoroToday.focus_minutes}</span> 分钟
                </div>
              </div>
            </Card>

            <Card
              title={<span><AimOutlined style={{ color: '#E19B5A', marginRight: 6 }} />每日学习目标</span>}
              style={{ borderRadius: 14, flex: 1 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <span style={{ fontSize: 13, color: '#6B7280' }}>每天学习</span>
                <InputNumber
                  min={1}
                  max={50}
                  value={dailyGoal}
                  onChange={(v) => setDailyGoal(v || 1)}
                  onBlur={saveSettings}
                  style={{ width: 80 }}
                />
                <span style={{ fontSize: 13, color: '#6B7280' }}>个知识点</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                <span style={{ color: '#1F2733' }}>今日新完成</span>
                <span className="mono" style={{ color: goalProgress >= 100 ? '#10B981' : '#E19B5A' }}>
                  {todayCompleted} / {dailyGoal}
                </span>
              </div>
              <Progress
                percent={goalProgress}
                status={goalProgress >= 100 ? 'success' : 'active'}
                strokeColor={{ '0%': '#FEB97B', '100%': '#E19B5A' }}
                trailColor="rgba(0,0,0,0.08)"
              />
              <div style={{ marginTop: 8, fontSize: 12, color: '#6B7280' }}>
                {todayCompleted >= dailyGoal
                  ? '今日目标已达成，继续保持！'
                  : `还差 ${Math.max(0, dailyGoal - todayCompleted)} 个知识点达成今日目标`}
              </div>
            </Card>
          </div>
        </Col>
      </Row>

      {/* 书架 */}
      <Card
        title={<span><BookOutlined style={{ color: '#0284C7', marginRight: 6 }} />书架</span>}
        extra={<span style={{ fontSize: 12, color: '#6B7280' }}>支持 PDF / Word / PPT / TXT / 图片，单文件 ≤ 50MB</span>}
        style={{ borderRadius: 14, marginTop: 16 }}
      >
        <Upload customRequest={handleUploadTextbook} showUploadList={false} multiple>
          <Button icon={<UploadOutlined />}>上传教材</Button>
        </Upload>

        {/* 教材书架：内置课程教材与用户上传教材统一以书籍外形展示 */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, marginTop: 20 }}>
          {books.map((book) => {
            const color = coverColor(book)
            return (
              <div key={book.id} style={{ width: 150 }}>
                {/* 书籍封面 */}
                <div
                  onClick={book.builtin ? () => handleSwitchCourse(book.title) : undefined}
                  title={book.builtin ? (book.learning ? '当前课程' : `切换到《${book.title}》`) : book.title}
                  style={{
                    position: 'relative', width: 150, height: 200, borderRadius: '4px 10px 10px 4px',
                    background: `linear-gradient(160deg, ${color} 0%, ${color} 52%, #111827 165%)`,
                    boxShadow: '0 10px 18px rgba(0,0,0,0.18)',
                    cursor: book.builtin ? 'pointer' : 'default',
                    transition: 'transform 0.2s ease, boxShadow 0.2s ease',
                  }}
                  onMouseEnter={(e) => { if (book.builtin) e.currentTarget.style.transform = 'translateY(-4px)' }}
                  onMouseLeave={(e) => { if (book.builtin) e.currentTarget.style.transform = 'translateY(0)' }}
                >
                  {/* 书脊 */}
                  <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 12, background: 'rgba(0,0,0,0.22)', borderTopLeftRadius: 4, borderBottomLeftRadius: 4 }} />
                  <div style={{ position: 'absolute', left: 4, top: 8, bottom: 8, width: 2, background: 'rgba(255,255,255,0.28)', borderRadius: 2 }} />
                  {/* 书名 */}
                  <div style={{
                    position: 'absolute', left: 24, right: 12, top: 18,
                    color: '#fff', fontSize: 15, fontWeight: 700, lineHeight: 1.4,
                    display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                  }}>
                    {book.title}
                  </div>
                  {/* 底部标签 */}
                  <div style={{ position: 'absolute', left: 24, right: 12, bottom: 14 }}>
                    {book.learning ? (
                      <Tag color="green" style={{ margin: 0, border: 'none', background: 'rgba(16,185,129,0.95)' }}>正在学习</Tag>
                    ) : (
                      <span style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.92)', letterSpacing: 1.5, textTransform: 'uppercase' }}>
                        {book.builtin ? '教材' : book.file_type}
                      </span>
                    )}
                  </div>
                </div>

                {/* 封面下方：书名 / 元信息 / 操作 */}
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#1F2733', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={book.title}>
                    {book.title}
                  </div>
                  <div style={{ fontSize: 11, color: '#6B7280', textAlign: 'center', marginTop: 2, minHeight: 16 }}>
                    {book.builtin ? (book.learning ? '当前学习课程' : '课程教材') : `${formatSize(book.file_size)} · ${book.create_time}`}
                  </div>
                  {!book.builtin && (
                    <div style={{ textAlign: 'center', marginTop: 4 }}>
                      <Space size={4}>
                        <Tooltip title="打开">
                          <Button type="text" size="small" icon={<EyeOutlined />} onClick={() => window.open(`/api/profile/textbooks/${book.id}/download`, '_blank')} />
                        </Tooltip>
                        <Tooltip title="删除">
                          <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteTextbook(book.id)} />
                        </Tooltip>
                      </Space>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* 账号管理 */}
      <Card title="账号管理" style={{ borderRadius: 14, marginTop: 16 }}>
        <Space wrap>
          <Button danger ghost icon={<LogoutOutlined />} onClick={handleLogout}>退出登录</Button>
          <Button danger icon={<UserDeleteOutlined />} onClick={handleDeleteAccount}>用户注销</Button>
          <Button icon={<HistoryOutlined />} onClick={() => { setEvalModalOpen(true); loadEvaluations() }}>评估历史</Button>
          <Button danger ghost icon={<ReloadOutlined />} onClick={handleReset}>重置数据</Button>
        </Space>
      </Card>

      <Modal title="动态画像评估历史" open={evalModalOpen} onCancel={() => setEvalModalOpen(false)} footer={null} width={460}>
        {evalLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
        ) : evalHistory.length === 0 ? (
          <Empty description="暂无评估记录，可在答疑助手多提问后触发评估" />
        ) : (
          <Timeline
            items={evalHistory.map((rec) => ({
              color: rec.applied ? 'blue' : 'gray',
              children: (
                <div>
                  <div style={{ fontSize: 12, color: '#6B7280' }}>{rec.create_time}</div>
                  {rec.summary && <div style={{ fontSize: 13, color: '#1F2733', margin: '4px 0' }}>{rec.summary}</div>}
                  {rec.applied && (rec.changes || []).length > 0 ? (
                    <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {(rec.changes || []).map((c, i) => (
                        <Tag key={i} color="cyan" style={{ fontSize: 11 }} title={c.reason}>
                          {FIELD_LABELS[c.field] || c.field}：{rec.before_profile?.[c.field]} → {c.value}
                        </Tag>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 12, color: '#6B7280' }}>已评估，无需调整</div>
                  )}
                </div>
              ),
            }))}
          />
        )}
      </Modal>
    </div>
  )
}
