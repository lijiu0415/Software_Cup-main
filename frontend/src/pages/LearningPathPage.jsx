import React, { useState, useEffect } from 'react'
import { Card, Timeline, Tag, Typography, Button, Space, Progress, Spin, message } from 'antd'
import {
  FlagOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons'
import useStore from '../store/useStore'
import { getLearningPath, planLearningPath, completeKp } from '../api'

const { Title, Text } = Typography

const difficultyColors = { 1: 'green', 2: 'cyan', 3: 'blue', 4: 'orange', 5: 'red' }
const difficultyLabels = { 1: '入门', 2: '基础', 3: '中等', 4: '进阶', 5: '高级' }

export default function LearningPathPage() {
  const { studentId, learningPath, setLearningPath, updateMastery, setPendingKpId, setCurrentStep, currentStep } = useStore()
  const [loading, setLoading] = useState(false)
  const [completedKps, setCompletedKps] = useState([])
  const [aiSummary, setAiSummary] = useState('')
  const [planSource, setPlanSource] = useState('rule')
  const [planning, setPlanning] = useState(false)

  const fetchPath = async () => {
    setLoading(true)
    try {
      const res = await getLearningPath(studentId)
      setLearningPath(res.data.path || [])
      setCompletedKps(res.data.completed || [])
    } catch (err) {
      message.error('获取学习路径失败')
    } finally {
      setLoading(false)
    }
  }

  const planPath = async () => {
    if (!studentId) return
    setPlanning(true)
    try {
      const res = await planLearningPath(studentId)
      setLearningPath(res.data.path || [])
      setCompletedKps(res.data.completed || [])
      setAiSummary(res.data.summary || '')
      setPlanSource(res.data.source || 'rule')
    } catch (err) {
      // AI 规划失败：保持规则路径
    } finally {
      setPlanning(false)
    }
  }

  const refresh = () => {
    fetchPath()
    planPath()
  }

  useEffect(() => {
    fetchPath()
    planPath()
  }, [studentId])

  useEffect(() => {
    if (currentStep === 1) refresh()
  }, [currentStep])

  const handleLearn = (kp) => {
    // 跳到知识点学习页并选中该知识点
    setPendingKpId(kp.kp_id)
    setCurrentStep(2)
  }

  const handleSkip = async (kp) => {
    try {
      await completeKp(studentId, kp.kp_id)
      updateMastery(kp.kp_id, 1.0)
      message.success(`已掌握: ${kp.name}`)
      refresh()
    } catch (err) {
      message.error('操作失败')
    }
  }

  const totalCount = learningPath.length + completedKps.length
  const completedCount = completedKps.length
  const realProgress = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0
  const currentIdx = learningPath.findIndex((kp) => kp.mastery < 0.6)

  return (
    <div style={{ display: 'flex', gap: 20, alignItems: 'stretch', height: '100%', overflow: 'hidden' }}>
      {/* 左侧 60%：推荐学习顺序 */}
      <div style={{ flex: 3, minWidth: 0, height: '100%' }}>
        <Card
          className="glass-card"
          title={<Space><FlagOutlined style={{ color: '#0EA5E9' }} /><span>推荐学习顺序</span></Space>}
          extra={
            <Space>
              {planning && <Text type="secondary" style={{ fontSize: 12 }}><Spin size="small" /> AI 规划中…</Text>}
              <Button size="small" icon={<FlagOutlined />} onClick={refresh} loading={loading}>刷新路径</Button>
            </Space>
          }
          style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          styles={{ body: { flex: 1, overflow: 'auto', minHeight: 0 } }}
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <Spin size="large" />
            </div>
          ) : learningPath.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: '#6B7280' }}>
              <FlagOutlined style={{ fontSize: 48 }} />
              <p>暂无学习路径</p>
              <p><Text type="secondary">请先完成评估问卷，生成学习画像</Text></p>
            </div>
          ) : (
            <Timeline
              items={learningPath.map((kp, i) => {
                const isCurrent = i === currentIdx
                const isMastered = kp.mastery >= 0.6
                return {
                  color: isCurrent ? '#0EA5E9' : isMastered ? '#10B981' : 'rgba(0,0,0,0.2)',
                  dot: isCurrent ? <RocketOutlined style={{ color: '#0EA5E9' }} /> : undefined,
                  children: (
                    <div
                      style={{
                        padding: '14px 16px',
                        borderRadius: 12,
                        cursor: 'pointer',
                        background: isCurrent ? 'rgba(14,165,233,0.08)' : 'rgba(0,0,0,0.03)',
                        border: isCurrent ? '1px solid rgba(14,165,233,0.35)' : '1px solid rgba(0,0,0,0.08)',
                      }}
                      onClick={() => handleLearn(kp)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Space size={10}>
                          <Text strong={isCurrent} style={{ fontSize: 16, color: isCurrent ? '#0284C7' : undefined }}>
                            {i + 1}. {kp.name}
                          </Text>
                          <Tag color={difficultyColors[kp.difficulty]}>{difficultyLabels[kp.difficulty]}</Tag>
                          {isCurrent && <Tag color="cyan">当前推荐</Tag>}
                          {isMastered && <Tag color="success" icon={<CheckCircleOutlined />}>已掌握</Tag>}
                        </Space>
                      </div>
                      <div style={{ marginTop: 6, color: '#6B7280', fontSize: 13 }}>
                        <ClockCircleOutlined style={{ marginRight: 6 }} />
                        {kp.description || '无描述'}
                      </div>
                      {kp.reason && (
                        <div style={{ marginTop: 6, color: '#0284C7', fontSize: 12 }}>
                          💡 {kp.reason}
                        </div>
                      )}
                      <div style={{ marginTop: 8 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>掌握度：</Text>
                        <Progress
                          percent={Math.round(kp.mastery * 100)}
                          size="small"
                          strokeColor={isMastered ? '#10B981' : '#0EA5E9'}
                          trailColor="rgba(0,0,0,0.1)"
                          style={{ width: 200, display: 'inline-block', marginLeft: 8 }}
                        />
                        <Button
                          size="small"
                          type="primary"
                          ghost
                          icon={<ArrowRightOutlined />}
                          style={{ float: 'right' }}
                          onClick={(e) => { e.stopPropagation(); handleLearn(kp) }}
                        >
                          开始学习
                        </Button>
                        {!isMastered && (
                          <Button
                            size="small"
                            style={{ float: 'right', marginRight: 8 }}
                            onClick={(e) => { e.stopPropagation(); handleSkip(kp) }}
                          >
                            标记已掌握
                          </Button>
                        )}
                      </div>
                    </div>
                  ),
                }
              })}
            />
          )}
        </Card>
      </div>

      {/* 右侧 40%：路径详情 */}
      <div style={{ flex: 2, minWidth: 0 }}>
        <Card
          className="glass-card"
          title={<Space><RocketOutlined style={{ color: '#4A90F9' }} /><span>路径详情</span></Space>}
        >
          <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
            <div style={{ flex: 1, textAlign: 'center', padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: 12, color: '#6B7280' }}>总知识点</div>
              <div className="mono" style={{ fontSize: 22, color: '#1F2733' }}>{totalCount}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center', padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: 12, color: '#6B7280' }}>已完成</div>
              <div className="mono" style={{ fontSize: 22, color: '#10B981' }}>{completedCount}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center', padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: 12, color: '#6B7280' }}>进度</div>
              <div className="mono" style={{ fontSize: 22, color: '#0EA5E9' }}>{realProgress}%</div>
            </div>
          </div>

          {planSource === 'ai' && aiSummary && (
            <div style={{ marginTop: 8, padding: '12px 14px', borderRadius: 10, background: 'rgba(14,165,233,0.06)', border: '1px solid rgba(14,165,233,0.25)' }}>
              <Text strong style={{ fontSize: 13 }}>AI 规划说明</Text>
              <div style={{ color: '#1F2733', fontSize: 13, marginTop: 6, lineHeight: 1.8 }}>{aiSummary}</div>
            </div>
          )}

          <div style={{ marginTop: 8 }}>
            <Text strong style={{ fontSize: 13 }}>推荐理由</Text>
            <ul style={{ color: '#6B7280', fontSize: 13, paddingLeft: 20, marginTop: 8, lineHeight: 2 }}>
              {planSource === 'ai' ? (
                <>
                  <li>基于完整画像（目标 / 偏好 / 风格 / 易错 / 速度 / 基础）由 AI 个性化排序</li>
                  <li>知识图谱前置校验后，AI 为每一步给出推荐理由</li>
                  <li>优先补齐掌握度低于阈值的知识点缺口</li>
                </>
              ) : (
                <>
                  <li>基于知识图谱 DAG 拓扑排序，前置校验后推荐</li>
                  <li>结合学生画像能力加权，动态计算最优顺序</li>
                  <li>优先补齐掌握度低于阈值的知识点缺口</li>
                </>
              )}
            </ul>
          </div>

          <div style={{ marginTop: 8 }}>
            <Text strong style={{ fontSize: 13 }}>学习建议</Text>
            <ul style={{ color: '#6B7280', fontSize: 13, paddingLeft: 20, marginTop: 8, lineHeight: 2 }}>
              <li>点击左侧任意节点即可进入该知识点学习</li>
              <li>学完一个知识点后点击「完成学习」更新掌握度</li>
            </ul>
          </div>
        </Card>
      </div>
    </div>
  )
}
