import React, { useState, useEffect } from 'react'
import { Card, Select, Tabs, Button, Space, Tag, Typography, Spin, message, List, Progress, Modal } from 'antd'
import {
  BookOutlined,
  FileTextOutlined,
  CodeOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  LoadingOutlined,
  ReadOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import { getKnowledgePoints, generateResourcesStream, checkPrerequisites, completeKp, getLearningPath } from '../api'
import ResourceCard from '../components/ResourceCard'
import MindMap from '../components/MindMap'
import KnowledgeVulnerabilityBoard from '../components/KnowledgeVulnerabilityBoard'

const { Title, Text } = Typography

const AGENT_LABELS = {
  '教案Agent': { label: '教案', icon: <FileTextOutlined /> },
  '习题Agent': { label: '习题', icon: <BookOutlined /> },
  '代码Agent': { label: '代码', icon: <CodeOutlined /> },
  '思维导图Agent': { label: '思维导图', icon: <BulbOutlined /> },
  '拓展阅读Agent': { label: '拓展阅读', icon: <ReadOutlined /> },
  '视频推荐Agent': { label: '视频推荐', icon: <PlayCircleOutlined /> },
}

export default function LearningPage() {
  const { studentId, studentProfile, pendingKpId, setPendingKpId, setPendingChapterId } = useStore()
  const navigate = useNavigate()
  const [kpList, setKpList] = useState([])
  const [chapters, setChapters] = useState([])
  const [selectedChapter, setSelectedChapter] = useState(null)
  const [selectedKp, setSelectedKp] = useState(null)
  const [resources, setResources] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [prereqCheck, setPrereqCheck] = useState(null)
  const [activeTab, setActiveTab] = useState('lesson')
  const [masteryVersion, setMasteryVersion] = useState(0)
  const [chapterCompleteModal, setChapterCompleteModal] = useState(false)
  const currentCourse = studentProfile?.course || studentProfile?.course_name || '人工智能导论'
  const [completedIds, setCompletedIds] = useState(new Set())

  // 进度条状态
  const [progressPct, setProgressPct] = useState(0)
  const [agentStatuses, setAgentStatuses] = useState({})

  useEffect(() => {
    fetchCompletedIds()
  }, [studentId])

  useEffect(() => {
    setSelectedChapter(null)
    setSelectedKp(null)
    setResources(null)
    fetchKps()
  }, [currentCourse])

  const fetchCompletedIds = async () => {
    try {
      const res = await getLearningPath(studentId)
      const ids = new Set((res.data.completed || []).map((k) => k.kp_id))
      setCompletedIds(ids)
    } catch {
      // 静默失败
    }
  }

  const fetchKps = async () => {
    setLoading(true)
    try {
      const res = await getKnowledgePoints(null, currentCourse || undefined)
      const items = res.data.items || []
      setKpList(items)

      const chMap = {}
      items.forEach((kp) => {
        if (!chMap[kp.chapter_id]) {
          chMap[kp.chapter_id] = { id: kp.chapter_id, name: kp.chapter_id }
        }
      })
      setChapters(Object.values(chMap))

      if (!selectedChapter && Object.keys(chMap).length > 0) {
        setSelectedChapter(Object.keys(chMap)[0])
      }
    } catch (err) {
      message.error('获取知识点列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectKp = async (kp) => {
    setSelectedKp(kp)
    setResources(null)
    setGenerating(true)
    setProgressPct(0)
    setAgentStatuses({})

    // 前置校验
    try {
      const preRes = await checkPrerequisites(kp.kp_id, studentId)
      setPrereqCheck(preRes.data)
    } catch (err) {
      setPrereqCheck({ is_ok: true, lack_kp: [] })
    }

    // 流式生成资源
    generateResourcesStream(studentId, kp.kp_id, {
      onProgress: (evt) => {
        if (evt.phase === 'start') {
          const initial = {}
          evt.agents.forEach((a) => { initial[a] = 'waiting' })
          setAgentStatuses(initial)
        } else if (evt.phase === 'running') {
          setAgentStatuses((prev) => ({ ...prev, [evt.agent]: 'running' }))
        } else if (evt.phase === 'done') {
          setAgentStatuses((prev) => ({ ...prev, [evt.agent]: evt.cached ? 'cached' : 'done' }))
          setProgressPct((p) => Math.min(p + 17, 100))
        } else if (evt.phase === 'fail') {
          setAgentStatuses((prev) => ({ ...prev, [evt.agent]: 'fail' }))
          setProgressPct((p) => Math.min(p + 17, 100))
        }
      },
      onDone: (results) => {
        setResources(results)
        setGenerating(false)
        setProgressPct(100)
      },
      onError: (errMsg) => {
        message.error(`资源生成失败: ${errMsg}`)
        setGenerating(false)
      },
    })
  }

  // 监听 markdown 链接内的知识点跳转（同页跳转）
  useEffect(() => {
    const handler = (e) => {
      const targetKp = kpList.find((k) => k.kp_id === e.detail)
      if (targetKp) {
        setSelectedChapter(targetKp.chapter_id)
        handleSelectKp(targetKp)
      }
    }
    window.addEventListener('navigateToKp', handler)
    return () => window.removeEventListener('navigateToKp', handler)
  }, [kpList])

  // 跨页跳转：从学习路径/漏洞看板带过来的 pendingKpId
  useEffect(() => {
    if (pendingKpId && kpList.length > 0) {
      const targetKp = kpList.find((k) => k.kp_id === pendingKpId)
      if (targetKp) {
        setSelectedChapter(targetKp.chapter_id)
        handleSelectKp(targetKp)
      }
      setPendingKpId(null)
    }
  }, [pendingKpId, kpList])

  const filteredKps = selectedChapter
    ? kpList.filter((kp) => kp.chapter_id === selectedChapter)
    : kpList

  const handleCompleteLearning = async () => {
    if (!selectedKp || !resources) return
    try {
      await completeKp(studentId, selectedKp.kp_id)
      const newIds = new Set([...completedIds, selectedKp.kp_id])
      setCompletedIds(newIds)
      setMasteryVersion((v) => v + 1)
      message.success(`已完成学习：${selectedKp.name}`)

      // 检测本章是否已学完全部知识点，学完则提示可进行章节测试
      const chapterKps = kpList.filter((kp) => kp.chapter_id === selectedKp.chapter_id)
      const allDone = chapterKps.length > 0 && chapterKps.every((kp) => newIds.has(kp.kp_id))
      if (allDone) {
        setChapterCompleteModal(true)
      }
    } catch {
      message.error('掌握度更新失败')
    }
  }

  const goToTest = () => {
    setChapterCompleteModal(false)
    setPendingChapterId(selectedKp?.chapter_id)
    navigate('/exercise')
  }

  // 渲染进度条区域
  const renderProgress = () => {
    const total = Object.keys(agentStatuses).length
    const done = Object.values(agentStatuses).filter((s) => s === 'done' || s === 'cached').length
    const statusColor = (status) => {
      switch (status) {
        case 'running': return '#4A90F9'
        case 'done': return '#10B981'
        case 'cached': return '#10B981'
        case 'fail': return '#EF4444'
        default: return 'rgba(0,0,0,0.2)'
      }
    }
    const statusText = (status) => {
      switch (status) {
        case 'waiting': return '等待中'
        case 'running': return '生成中...'
        case 'done': return '✓ 完成'
        case 'cached': return '✓ 缓存命中'
        case 'fail': return '✗ 失败'
        default: return '等待中'
      }
    }

    return (
      <div style={{ textAlign: 'center', padding: '40px 20px' }}>
        <Title level={5} style={{ marginBottom: 16 }}>
          <LoadingOutlined spin style={{ marginRight: 8, color: '#4A90F9' }} />
          多智能体并行生成资源
        </Title>

        <Progress
          percent={progressPct}
          status={progressPct === 100 ? 'success' : 'active'}
          strokeColor={{ '0%': '#4A90F9', '100%': '#0EA5E9' }}
          trailColor="rgba(0,0,0,0.1)"
          style={{ maxWidth: 400, marginBottom: 24 }}
        />
        <Text type="secondary">
          已完成 {done}/{total} 个Agent
        </Text>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 24, flexWrap: 'wrap' }}>
          {Object.entries(AGENT_LABELS).map(([name, info]) => {
            const status = agentStatuses[name] || 'waiting'
            const isRunning = status === 'running'
            return (
              <Card
                key={name}
                size="small"
                style={{
                  width: 140, textAlign: 'center',
                  borderColor: statusColor(status),
                  background: isRunning ? 'rgba(74,144,249,0.08)' : 'rgba(0,0,0,0.03)',
                }}
              >
                <div style={{ fontSize: 24, marginBottom: 4 }}>
                  {isRunning ? <LoadingOutlined spin style={{ color: '#4A90F9' }} /> : info.icon}
                </div>
                <Text strong style={{ display: 'block' }}>{info.label}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {statusText(status)}
                </Text>
              </Card>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'stretch', height: '100%', overflow: 'hidden' }}>
      {/* 左侧知识点列表 */}
      <Card
        className="glass-card"
        title="知识点列表"
        style={{ width: 280, minWidth: 280, flexShrink: 0, overflow: 'auto' }}
        extra={
          <Select
            placeholder="选择章节"
            value={selectedChapter}
            onChange={setSelectedChapter}
            style={{ width: 150 }}
            options={chapters.map((ch) => ({ value: ch.id, label: ch.name }))}
            allowClear
          />
        }
      >
        <List
          loading={loading}
          dataSource={filteredKps}
          renderItem={(kp) => (
            <List.Item
              style={{
                cursor: 'pointer',
                padding: '8px 12px',
                borderRadius: 6,
                background: selectedKp?.kp_id === kp.kp_id ? 'rgba(14,165,233,0.08)' : 'transparent',
                border: selectedKp?.kp_id === kp.kp_id ? '1px solid rgba(14,165,233,0.4)' : '1px solid transparent',
              }}
              onClick={() => handleSelectKp(kp)}
            >
              <Space>
                <Tag color={kp.difficulty <= 2 ? 'green' : kp.difficulty <= 3 ? 'orange' : 'red'}>
                  L{kp.difficulty}
                </Tag>
                <Text>{kp.name}</Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>

      {/* 中间内容区 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {selectedKp ? (
          <>
            <Card className="glass-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                  <BookOutlined style={{ fontSize: 20, color: '#4A90F9' }} />
                  <Title level={4} style={{ margin: 0 }}>{selectedKp.name}</Title>
                  <Tag>难度 {selectedKp.difficulty}/5</Tag>
                  {resources && (
                    completedIds.has(selectedKp.kp_id) ? (
                      <Tag color="success" icon={<CheckCircleOutlined />}>已完成</Tag>
                    ) : (
                      <Button type="primary" size="small" onClick={handleCompleteLearning}>
                        完成学习 ✓
                      </Button>
                    )
                  )}
                </Space>
                {prereqCheck && !prereqCheck.is_ok && (
                  <Tag color="warning" icon={<WarningOutlined />}>
                    前置知识点不足
                  </Tag>
                )}
              </div>
              <Text type="secondary">{selectedKp.description}</Text>

              {prereqCheck && !prereqCheck.is_ok && (
                <Card size="small" style={{ marginTop: 12, background: 'rgba(255,179,71,0.08)', borderColor: 'rgba(255,179,71,0.3)' }}>
                  <Text type="warning">
                    <WarningOutlined /> 需要先学习以下前置知识点：
                  </Text>
                  <div style={{ marginTop: 8 }}>
                    {prereqCheck.lack_kp.map((k) => (
                      <Tag key={k.kp_id} color="orange" style={{ cursor: 'pointer' }}>
                        {k.name} (掌握度: {(k.mastery * 100).toFixed(0)}%)
                      </Tag>
                    ))}
                  </div>
                </Card>
              )}
            </Card>

            {/* 资源标签页 */}
            <Card className="glass-card" style={{ flex: 1, overflow: 'auto' }}>
              {generating ? (
                renderProgress()
              ) : resources ? (
                <Tabs
                  activeKey={activeTab}
                  onChange={setActiveTab}
                  items={[
                    {
                      key: 'lesson',
                      label: <span><FileTextOutlined /> 教案</span>,
                      children: <ResourceCard title="个性化教案" icon={<FileTextOutlined />} content={resources.lesson} type="markdown" />,
                    },
                    {
                      key: 'exercise',
                      label: <span><BookOutlined /> 习题</span>,
                      children: <ResourceCard title="针对性练习" icon={<BookOutlined />} content={resources.exercise} type="markdown" />,
                    },
                    {
                      key: 'code',
                      label: <span><CodeOutlined /> 代码</span>,
                      children: <ResourceCard title="Python代码案例" icon={<CodeOutlined />} content={resources.code} type="markdown" />,
                    },
                    {
                      key: 'mindmap',
                      label: <span><BulbOutlined /> 思维导图</span>,
                      children: <MindMap mermaidCode={resources.mindmap} />,
                    },
                    {
                      key: 'reading',
                      label: <span><ReadOutlined /> 拓展阅读</span>,
                      children: <ResourceCard title="拓展阅读" icon={<ReadOutlined />} content={resources.reading} type="markdown" />,
                    },
                    {
                      key: 'video',
                      label: <span><PlayCircleOutlined /> 视频推荐</span>,
                      children: <ResourceCard title="视频学习推荐" icon={<PlayCircleOutlined />} content={resources.video} type="markdown" />,
                    },
                  ]}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: 60, color: '#6B7280' }}>
                  <BookOutlined style={{ fontSize: 48 }} />
                  <p>选择左侧知识点开始学习</p>
                </div>
              )}
            </Card>
          </>
        ) : (
          <Card className="glass-card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: '#6B7280' }}>
              <BookOutlined style={{ fontSize: 48 }} />
              <p>请从左侧选择一个知识点</p>
            </div>
          </Card>
        )}
      </div>

      {/* 右侧画像面板 */}
      <div style={{ width: 240 }}>
        <KnowledgeVulnerabilityBoard
          key={masteryVersion}
          studentId={studentId}
          studentProfile={studentProfile}
        />
      </div>

      {/* 章节学完 → 提示可进行章节测试 */}
      <Modal
        title="章节测试已解锁"
        open={chapterCompleteModal}
        onCancel={() => setChapterCompleteModal(false)}
        footer={[
          <Button key="later" onClick={() => setChapterCompleteModal(false)}>稍后测试</Button>,
          <Button key="go" type="primary" onClick={goToTest}>去测试</Button>,
        ]}
      >
        <p>你已完成「{selectedKp?.chapter_id || ''}」全部知识点的学习，现在可以进行章节测试了。</p>
      </Modal>
    </div>
  )
}
