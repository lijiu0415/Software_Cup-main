import React, { useState, useEffect } from 'react'
import { Card, Select, Button, Radio, Checkbox, Input, Tag, Space, Typography, Statistic, List, message, Empty, Spin, Progress, Divider, Menu } from 'antd'
import {
  CheckCircleFilled,
  CloseCircleFilled,
  LockOutlined,
  StarOutlined,
  WarningOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  getExerciseChapters, getChapterTest, submitChapterTest, getChapterTestResult,
  getWrongBook, getWrongAnalysis,
} from '../api'
import useStore from '../store/useStore'
import ProfilePlaceholder from '../components/ProfilePlaceholder'
import ProgramTestChat from '../components/ProgramTestChat'

const { Text, Title } = Typography

const TYPE_ORDER = ['单选题', '判断题', '多选题', '编程题']
const FIELD_LABELS = { base_level: '基础水平', error_type: '易错类型' }

export default function ExercisePage() {
  const studentId = useStore((s) => s.studentId)
  const questionnaire_complete = useStore((s) => s.questionnaire_complete)
  const studentProfile = useStore((s) => s.studentProfile)
  const pendingChapterId = useStore((s) => s.pendingChapterId)
  const setPendingChapterId = useStore((s) => s.setPendingChapterId)
  const course = studentProfile?.course || '人工智能导论'

  const [chapters, setChapters] = useState([])
  const [chapterLoading, setChapterLoading] = useState(true)
  const [selectedChapterId, setSelectedChapterId] = useState(null)
  const [questions, setQuestions] = useState([])
  const [testLoading, setTestLoading] = useState(false)
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [viewWrongBook, setViewWrongBook] = useState(false)

  const [stats, setStats] = useState({ done: 0, correct: 0, wrong: 0 })
  const [wrongBook, setWrongBook] = useState([])
  const [weakPoints, setWeakPoints] = useState([])

  useEffect(() => {
    if (!studentId) return
    setChapterLoading(true)
    setSelectedChapterId(null)
    setQuestions([])
    setAnswers({})
    setResult(null)
    setSubmitted(false)
    setViewWrongBook(false)
    getExerciseChapters(studentId, course)
      .then((res) => setChapters(res.data.chapters || []))
      .catch(() => message.error('获取章节列表失败'))
      .finally(() => setChapterLoading(false))
  }, [studentId, course])

  const refreshWrong = async () => {
    if (!studentId) return
    try {
      const [book, analysis] = await Promise.all([
        getWrongBook(studentId, course),
        getWrongAnalysis(studentId),
      ])
      setStats(book.data.stats || { done: 0, correct: 0, wrong: 0 })
      setWrongBook(book.data.items || [])
      setWeakPoints((analysis.data.by_kp || []).slice(0, 5))
    } catch {
      // 首屏加载失败不阻塞测试
    }
  }

  useEffect(() => {
    refreshWrong()
  }, [studentId, course])

  const loadLatestResult = async (cid) => {
    try {
      const r = await getChapterTestResult(studentId, cid)
      if (r.data.latest) {
        setResult(r.data.latest)
        setSubmitted(true)
      }
      setHistory(r.data.history || [])
    } catch {
      // 无历史结果时忽略
    }
  }

  const handleSelectChapter = async (cid) => {
    setSelectedChapterId(cid)
    setViewWrongBook(false)
    setAnswers({})
    setResult(null)
    setSubmitted(false)
    setHistory([])
    if (!cid) {
      setQuestions([])
      return
    }
    setTestLoading(true)
    try {
      const res = await getChapterTest(studentId, cid)
      setQuestions(res.data.questions || [])
      loadLatestResult(cid)
    } catch (e) {
      setQuestions([])
      message.error(e?.response?.data?.detail || '获取题目失败')
    } finally {
      setTestLoading(false)
    }
  }

  // 跨页跳转：从知识点学习「去测试」带来的 pendingChapterId，自动选中该章
  useEffect(() => {
    if (pendingChapterId && chapters.length > 0) {
      const target = chapters.find((c) => c.chapter_id === pendingChapterId)
      if (target && target.unlocked) {
        handleSelectChapter(pendingChapterId)
      }
      setPendingChapterId(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingChapterId, chapters])

  const isAnswered = (q) => {
    const a = answers[q.ex_id]
    if (q.type === '多选题') return Array.isArray(a) && a.length > 0
    return a != null && a !== ''
  }

  const setAnswer = (q, v) => setAnswers((prev) => ({ ...prev, [q.ex_id]: v }))

  const judged = questions.filter((q) => q.type !== '编程题')
  const allAnswered = judged.length > 0 && judged.every(isAnswered)

  const handleSubmitTest = async () => {
    if (!studentId || !selectedChapterId || submitted || submitting) return
    if (!allAnswered) {
      message.warning('请完成全部判分题目后再提交（编程题不判分）')
      return
    }
    setSubmitting(true)
    try {
      const payload = judged.map((q) => ({ ex_id: q.ex_id, student_answer: answers[q.ex_id] }))
      const res = await submitChapterTest(studentId, selectedChapterId, payload)
      setResult(res.data)
      setSubmitted(true)
      refreshWrong()
      loadLatestResult(selectedChapterId)
    } catch (e) {
      message.error(e?.response?.data?.detail || '提交失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRetry = () => {
    setAnswers({})
    setResult(null)
    setSubmitted(false)
    setHistory([])
  }

  const grouped = TYPE_ORDER
    .map((t) => ({ type: t, items: questions.filter((q) => q.type === t) }))
    .filter((g) => g.items.length > 0)

  const renderOptions = (q) => {
    const val = answers[q.ex_id]
    if (q.type === '多选题') {
      return (
        <Checkbox.Group
          value={val || []}
          onChange={(v) => setAnswer(q, v)}
          disabled={submitted}
          style={{ display: 'flex', flexDirection: 'column', gap: 10 }}
        >
          {q.options.map((op) => (
            <Checkbox key={op} value={q.options.indexOf(op)} style={{ color: '#1F2733' }}>{op}</Checkbox>
          ))}
        </Checkbox.Group>
      )
    }
    if (q.type === '编程题') {
      return (
        <div>
          <Input.TextArea
            rows={6}
            placeholder="在此编写代码…（自评，不判分）"
            value={val || ''}
            onChange={(e) => setAnswer(q, e.target.value)}
            disabled={submitted}
            style={{ fontFamily: 'Consolas, monospace' }}
          />
          {q.reference_answer && (
            <div style={{ marginTop: 10, fontSize: 13 }}>
              <Text type="secondary">参考解答：</Text>
              <pre style={{ background: 'rgba(0,0,0,0.04)', padding: 10, borderRadius: 8, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 12, margin: '4px 0 0' }}>{q.reference_answer}</pre>
            </div>
          )}
        </div>
      )
    }
    return (
      <Radio.Group value={val} onChange={(e) => setAnswer(q, e.target.value)} disabled={submitted} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {q.options.map((op, i) => (
          <Radio key={op} value={i} style={{ color: '#1F2733' }}>{op}</Radio>
        ))}
      </Radio.Group>
    )
  }

  const shortChapterName = (name) => {
    const m = /^(第\d+章)/.exec(name || '')
    return m ? m[1] : name
  }

  const chapterOptions = chapters.map((c) => ({
    value: c.chapter_id,
    label: (
      <span style={{ color: c.unlocked ? 'inherit' : '#9CA3AF' }}>
        {!c.unlocked && <LockOutlined style={{ marginRight: 4, fontSize: 12 }} />}
        {shortChapterName(c.name)}
      </span>
    ),
    disabled: !c.unlocked,
  }))

  const scrollToType = (t) => {
    const el = document.getElementById(`type-group-${t}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (!questionnaire_complete) return <ProfilePlaceholder />

  const correctRate = stats.done ? Math.round((stats.correct / stats.done) * 100) : 0

  return (
    <div style={{ height: '100%', display: 'flex', gap: 16, overflow: 'hidden' }}>
      {/* 左侧 章节导航 + 题型导航 */}
      <div style={{ flex: '0 0 22%', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Card
          className="glass-card"
          size="small"
          title={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
              <span>章节导航</span>
              <Select
                placeholder={chapterLoading ? '加载中…' : '选择章节'}
                loading={chapterLoading}
                size="small"
                style={{ width: 118, flexShrink: 0 }}
                value={viewWrongBook ? undefined : selectedChapterId}
                onChange={handleSelectChapter}
                options={chapterOptions}
                allowClear
                popupMatchSelectWidth={false}
              />
            </div>
          }
        >
          <Menu
            mode="inline"
            style={{ background: 'transparent', border: 'none' }}
            selectedKeys={[]}
            onClick={({ key }) => scrollToType(key)}
            items={TYPE_ORDER.map((t) => ({ key: t, label: t }))}
          />
          <Divider style={{ margin: '8px 0' }} />
          <Button
            type={viewWrongBook ? 'primary' : 'default'}
            icon={<WarningOutlined />}
            block
            onClick={() => { setViewWrongBook(true); setSelectedChapterId(null); setQuestions([]); setResult(null); setSubmitted(false) }}
          >
            错题本
          </Button>
        </Card>
        {selectedChapterId && !viewWrongBook && history.length > 0 && (
          <Card className="glass-card" size="small" title="往期正确率">
            {history.map((h, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '4px 0' }}>
                <Text type="secondary">{h.create_time || '—'}</Text>
                <Text strong style={{ color: h.accuracy >= 80 ? '#10B981' : h.accuracy >= 60 ? '#F59E0B' : '#EF4444' }}>{h.accuracy}%</Text>
              </div>
            ))}
          </Card>
        )}
      </div>

      {/* 中部 答题区 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <Card
          className="glass-card"
          style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
          title={
            <Space>
              <StarOutlined style={{ color: '#0EA5E9' }} />
              <span>
                {viewWrongBook ? '错题本 · 错题回顾' : selectedChapterId
                  ? (chapters.find((c) => c.chapter_id === selectedChapterId)?.name || '整章测试')
                  : '章节整章测试'}
              </span>
            </Space>
          }
          styles={{ body: { flex: 1, overflow: 'auto' } }}
        >
          {viewWrongBook ? (
            wrongBook.length === 0 ? (
              <Empty description="暂无错题，答错的题目会自动收录" style={{ marginTop: 60 }} />
            ) : (
              <List
                dataSource={wrongBook}
                renderItem={(q) => (
                  <div style={{ padding: '14px', marginBottom: 12, borderRadius: 10, background: 'rgba(255,92,122,0.06)', border: '1px solid rgba(255,92,122,0.2)' }}>
                    <Space size={6} style={{ marginBottom: 6 }}>
                      <Tag color="red">{q.type}</Tag>
                      {q.kp_id && <Tag>{q.kp_id}</Tag>}
                      <Text type="secondary" style={{ fontSize: 12 }}>{q.create_time}</Text>
                    </Space>
                    <Text strong style={{ fontSize: 14 }}>{q.question}</Text>
                    <div style={{ marginTop: 8, fontSize: 13 }}>
                      <div>你的答案：<Text type="danger">{q.student_answer || '未作答'}</Text></div>
                      <div>正确答案：<Text type="success">{q.correct_answer}</Text></div>
                      <div style={{ color: '#6B7280' }}>解析：{q.analysis}</div>
                    </div>
                  </div>
                )}
              />
            )
          ) : !selectedChapterId ? (
            <Empty description="请选择已解锁的章节开始整章测试" style={{ marginTop: 60 }} />
          ) : testLoading ? (
            <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
          ) : submitted && result ? (
            <div>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16, padding: 16, borderRadius: 12, background: 'rgba(14,165,233,0.06)', border: '1px solid rgba(14,165,233,0.2)' }}>
                <Progress type="circle" percent={Math.round(result.accuracy)} size={72} strokeColor={{ '0%': '#4A90F9', '100%': '#0EA5E9' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 15, fontWeight: 700 }}>
                    正确率 {result.accuracy}% · 对 {result.correct} / 错 {result.wrong} / 共 {result.total}
                  </div>
                  {result.profile_changes && result.profile_changes.length > 0 && (
                    <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>画像已更新：</Text>
                      {result.profile_changes.map((c, i) => (
                        <Tag key={i} color="cyan" style={{ fontSize: 12 }}>
                          {FIELD_LABELS[c.field] || c.field} {c.old} → {c.new}
                        </Tag>
                      ))}
                    </div>
                  )}
                </div>
                <Button icon={<ReloadOutlined />} onClick={handleRetry}>重新测试</Button>
              </div>

              {result.detail && result.detail.map((d) => (
                <div key={d.ex_id} style={{ padding: '12px 14px', marginBottom: 10, borderRadius: 10, background: d.is_correct ? 'rgba(43,217,163,0.06)' : 'rgba(255,92,122,0.06)', border: `1px solid ${d.is_correct ? 'rgba(43,217,163,0.25)' : 'rgba(255,92,122,0.25)'}` }}>
                  <Space size={6} style={{ marginBottom: 4 }}>
                    {d.is_correct ? <CheckCircleFilled style={{ color: '#10B981' }} /> : <CloseCircleFilled style={{ color: '#EF4444' }} />}
                    <Tag color={d.is_correct ? 'green' : 'red'}>{d.type}</Tag>
                  </Space>
                  <div style={{ fontSize: 13, marginTop: 4 }}>
                    <div>你的答案：<Text type={d.is_correct ? 'success' : 'danger'}>{d.student_answer || '未作答'}</Text></div>
                    <div>正确答案：<Text type="success">{d.correct_answer}</Text></div>
                    {d.analysis && <div style={{ color: '#6B7280', marginTop: 4 }}>解析：{d.analysis}</div>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div>
              {grouped.map((g) => (
                <div key={g.type} id={`type-group-${g.type}`} style={{ marginBottom: 20 }}>
                  <Title level={5} style={{ margin: '0 0 10px' }}>
                    <Tag color="blue" style={{ marginRight: 8 }}>{g.type}</Tag>
                    {g.type === '编程题' && <Text type="secondary" style={{ fontSize: 12 }}>（Agent出题 · 对话式作答 · 不计入分值）</Text>}
                  </Title>
                  {g.type === '编程题' ? (
                    <ProgramTestChat chapterId={selectedChapterId} studentId={studentId} />
                  ) : (
                    g.items.map((q) => (
                      <div key={q.ex_id} style={{ marginBottom: 16, padding: '14px', borderRadius: 10, background: 'rgba(0,0,0,0.02)', border: '1px solid rgba(0,0,0,0.06)' }}>
                        <div style={{ marginBottom: 8 }}>
                          <Text strong>{q.question}</Text>
                        </div>
                        {renderOptions(q)}
                      </div>
                    ))
                  )}
                </div>
              ))}
              <div style={{ marginTop: 8 }}>
                <Button type="primary" size="large" block onClick={handleSubmitTest} loading={submitting} disabled={!allAnswered}>
                  {allAnswered ? '提交测试' : `提交测试（${judged.filter(isAnswered).length}/${judged.length} 已作答）`}
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* 右侧 数据栏 */}
      <div style={{ flex: '0 0 22%', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Card className="glass-card" size="small" title="练习数据">
          <Statistic title="已做题数" value={stats.done} suffix="题" />
          <Statistic title="正确率" value={correctRate} suffix="%" style={{ marginTop: 12 }} />
          <Statistic title="错题数" value={stats.wrong} suffix="题" style={{ marginTop: 12 }} />
        </Card>
        <Card className="glass-card" size="small" title="易错知识点排行">
          {weakPoints.length === 0 ? (
            <Empty description="暂无错题数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              size="small"
              dataSource={weakPoints}
              renderItem={(p, i) => (
                <List.Item style={{ border: 'none', padding: '6px 0' }}>
                  <Space>
                    <Tag color={i === 0 ? 'red' : i === 1 ? 'orange' : 'blue'}>{i + 1}</Tag>
                    <Text style={{ fontSize: 13 }}>{p.name}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>错 {p.wrong_count} 次</Text>
                  </Space>
                </List.Item>
              )}
            />
          )}
        </Card>
      </div>
    </div>
  )
}
