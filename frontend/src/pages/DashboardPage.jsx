import React, { useState, useEffect } from 'react'
import { Card, Tag, Button, Space, Progress, Typography, List, message, Spin } from 'antd'
import {
  ThunderboltOutlined,
  ArrowRightOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  RadarChartOutlined,
  AimOutlined,
  FlagOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import ReactECharts from 'echarts-for-react'
import useStore from '../store/useStore'
import { getLearningPath, getCourseProgress } from '../api'
import ProfilePlaceholder from '../components/ProfilePlaceholder'

const { Title, Text } = Typography

const difficultyLabels = { 1: '入门', 2: '基础', 3: '中等', 4: '进阶', 5: '高级' }
const difficultyColors = { 1: 'green', 2: 'cyan', 3: 'blue', 4: 'orange', 5: 'red' }

// 由学生画像推导 5 维能力雷达（无画像数据时为 0）
function buildAbility(profile) {
  if (!profile || Object.keys(profile).length === 0) return [0, 0, 0, 0, 0]
  const base = profile.base_level || 0
  const speed = profile.learn_speed || 0
  const pref = `${profile.learn_preference || ''}${profile.cognitive_style || ''}`
  const goal = profile.learn_goal || ''
  const clamp = (n) => Math.max(0, Math.min(5, n))
  return [
    clamp(base),                                              // 理论基础：基础水平
    clamp(/实践|代码|习题/.test(pref) ? Math.max(base, 4) : base), // 实践能力：实践型/代码·习题偏好偏高
    clamp(/竞赛|算法/.test(goal) ? Math.max(speed, 4) : speed),    // 算法思维：竞赛目标偏高
    clamp(/就业|项目|工程/.test(goal) ? Math.max(base, 4) : base), // 工程应用：就业/项目目标偏高
    clamp(speed),                                             // 知识迁移：学习速度近似
  ]
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user, studentId, studentProfile, questionnaire_complete, setCurrentStep, setPendingKpId } = useStore()
  const [loading, setLoading] = useState(true)
  const [path, setPath] = useState([])
  const [totalKps, setTotalKps] = useState(0)
  const [doneKps, setDoneKps] = useState(0)

  useEffect(() => {
    if (!studentId) { setLoading(false); return }
    setLoading(true)
    Promise.all([getLearningPath(studentId), getCourseProgress(studentId)])
      .then(([pathRes, progRes]) => {
        setPath(pathRes.data.path || [])

        // 总知识点 / 已完成：优先取当前课程，找不到则聚合全部课程
        const courses = progRes.data.courses || []
        const course = studentProfile?.course || '人工智能导论'
        let cur = courses.find((c) => c.course === course)
        if (!cur) {
          cur = {
            total: courses.reduce((s, c) => s + (c.total || 0), 0),
            completed: courses.reduce((s, c) => s + (c.completed || 0), 0),
          }
        }
        setTotalKps(cur.total || 0)
        setDoneKps(cur.completed || 0)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [studentId, studentProfile?.course])

  if (!questionnaire_complete) return <ProfilePlaceholder />

  const weak = path.filter((kp) => kp.mastery < 0.6)
  const openGaps = weak.length
  const remediating = weak.filter((kp) => kp.mastery > 0).length
  const total = totalKps
  const done = doneKps
  const progress = total ? Math.round((done / total) * 100) : 0

  const recommendations = path.slice(0, 5).map((kp, i) => ({
    kp_id: kp.kp_id,
    name: kp.name,
    difficulty: difficultyLabels[kp.difficulty] || `L${kp.difficulty}`,
    color: difficultyColors[kp.difficulty] || 'default',
    mastery: Math.round(kp.mastery * 100),
    current: i === 0,
  }))

  const tasks = path.slice(0, 3).map((kp, i) => ({
    status: i === 0 ? 'doing' : 'pending',
    text: kp.name,
  }))

  const nextKp = path[0] || null
  const remaining = path.length
  const estMinutes = remaining * 20
  const estLabel = remaining === 0
    ? '0m'
    : (estMinutes >= 60 ? `${Math.floor(estMinutes / 60)}h ${estMinutes % 60}m` : `${estMinutes}m`)

  const ability = buildAbility(studentProfile)

  const jumpToKp = (kp) => {
    if (kp && kp.kp_id) setPendingKpId(kp.kp_id)
    setCurrentStep(2)
    navigate('/main')
  }

  const gapDonutOption = {
    tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' } },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: '#6B7280', fontSize: 11 } },
    series: [
      {
        type: 'pie', radius: ['58%', '78%'], center: ['50%', '42%'],
        avoidLabelOverlap: false,
        itemStyle: { borderColor: '#F5F7FA', borderWidth: 2 },
        label: {
          show: true, position: 'center',
          formatter: `{name|开放缺口}\n{value|${openGaps}}\n{unit|处}`,
          rich: {
            name: { color: '#6B7280', fontSize: 12, lineHeight: 20 },
            value: { color: '#F59E0B', fontSize: 28, fontWeight: 700, fontFamily: 'SF Mono, Consolas, monospace', lineHeight: 34 },
            unit: { color: '#6B7280', fontSize: 11, lineHeight: 18 },
          },
        },
        data: [
          { value: openGaps, name: '开放', itemStyle: { color: '#F59E0B' } },
          { value: done, name: '已闭合', itemStyle: { color: '#10B981' } },
          { value: 0, name: '已关闭', itemStyle: { color: '#4A90F9' } },
        ],
      },
    ],
  }

  const radarOption = {
    tooltip: {},
    radar: {
      indicator: [
        { name: '理论基础', max: 5 }, { name: '实践能力', max: 5 }, { name: '算法思维', max: 5 },
        { name: '工程应用', max: 5 }, { name: '知识迁移', max: 5 },
      ],
      radius: '62%',
      axisName: { color: '#6B7280', fontSize: 11 },
      splitArea: { areaStyle: { color: ['rgba(74,144,249,0.03)', 'rgba(14,165,233,0.03)'] } },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.1)' } },
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.1)' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: ability, name: '能力画像',
            areaStyle: { color: 'rgba(14,165,233,0.25)' },
            lineStyle: { color: '#0EA5E9', width: 2 },
            itemStyle: { color: '#0EA5E9' },
          },
        ],
      },
    ],
  }

  if (loading) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', display: 'flex', gap: 20, alignItems: 'flex-start' }}>
      {/* 左侧主区 65% */}
      <div style={{ flex: 6.5, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* 问候 + 今日下一步 */}
        <Card className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <Title level={3} style={{ margin: 0 }}>下午好，{user.name}</Title>
              <Text type="secondary">「人工智能导论」已完成 {done}/{total} 个知识点</Text>
            </div>
            <div style={{ padding: '12px 16px', borderRadius: 12, background: 'rgba(14,165,233,0.08)', border: '1px solid rgba(14,165,233,0.3)', maxWidth: 360 }}>
              <Text strong style={{ fontSize: 13, color: '#0284C7' }}>今日下一步</Text>
              <div style={{ color: '#1F2733', fontSize: 13, margin: '4px 0 10px' }}>
                {nextKp ? `建议先做：${nextKp.name}` : '暂无待学知识点，请先完成画像'}
              </div>
              <Button
                type="primary"
                size="small"
                icon={<ArrowRightOutlined />}
                onClick={() => {
                  if (nextKp) jumpToKp(nextKp)
                  else { setCurrentStep(1); navigate('/main') }
                }}
              >
                继续这一步
              </Button>
            </div>
          </div>
        </Card>

        {/* 缺口闭环面板 */}
        <Card className="glass-card" title={<Space><AimOutlined style={{ color: '#0EA5E9' }} /><span>缺口闭环</span></Space>}>
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1, minHeight: 200 }}>
              <ReactECharts option={gapDonutOption} style={{ height: 200 }} />
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 16 }}>
              <div>
                <Text type="secondary" style={{ fontSize: 13 }}>缺口态势</Text>
                <div style={{ fontSize: 20, color: '#F59E0B', fontWeight: 700, marginTop: 4 }}>
                  当前补救中：<span className="mono">{remediating}</span> 处
                </div>
              </div>
              <div style={{ fontSize: 13, color: '#6B7280', lineHeight: 2 }}>
                <div>开放 <span className="mono" style={{ color: '#F59E0B' }}>{openGaps}</span> 处</div>
                <div>已闭合 <span className="mono" style={{ color: '#10B981' }}>{done}</span> 处</div>
                <div>已关闭 <span className="mono" style={{ color: '#4A90F9' }}>0</span> 处</div>
              </div>
              <Button type="primary" ghost icon={<CheckCircleOutlined />} onClick={() => message.info('全缺口补救功能开发中')}>
                全缺口补救
              </Button>
            </div>
          </div>
        </Card>

        {/* 推荐学习顺序 */}
        <Card className="glass-card" title={<Space><ThunderboltOutlined style={{ color: '#F59E0B' }} /><span>推荐学习顺序</span></Space>}>
          {recommendations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 24, color: '#6B7280' }}>
              <FlagOutlined style={{ fontSize: 32, marginBottom: 8 }} />
              <div>暂无推荐，请先完成画像并生成个性化学习路径</div>
            </div>
          ) : (
            <List
              dataSource={recommendations}
              renderItem={(kp) => (
                <List.Item
                  style={{
                    padding: '12px 14px', marginBottom: 8, borderRadius: 10,
                    background: kp.current ? 'rgba(14,165,233,0.08)' : 'rgba(0,0,0,0.03)',
                    border: kp.current ? '1px solid rgba(14,165,233,0.35)' : '1px solid rgba(0,0,0,0.08)',
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space size={10}>
                        <Text strong={kp.current} style={{ fontSize: 15, color: kp.current ? '#0284C7' : undefined }}>
                          {kp.name}
                        </Text>
                        <Tag color={kp.color}>{kp.difficulty}</Tag>
                        {kp.current && <Tag color="cyan">当前推荐</Tag>}
                      </Space>
                      <Button size="small" type="primary" ghost icon={<ArrowRightOutlined />} onClick={() => jumpToKp(kp)}>
                        开始学习
                      </Button>
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>掌握度：</Text>
                      <Progress
                        percent={kp.mastery}
                        size="small"
                        strokeColor={kp.current ? '#0EA5E9' : '#4A90F9'}
                        trailColor="rgba(0,0,0,0.1)"
                        style={{ width: 220, display: 'inline-block', marginLeft: 8 }}
                      />
                    </div>
                  </div>
                </List.Item>
              )}
            />
          )}
        </Card>

        {/* 今日学习任务 */}
        <Card className="glass-card" title={<Space><ClockCircleOutlined style={{ color: '#4A90F9' }} /><span>今日学习任务</span></Space>}>
          {tasks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 24, color: '#6B7280' }}>暂无学习任务</div>
          ) : (
            <List
              dataSource={tasks}
              renderItem={(t) => (
                <List.Item style={{ border: 'none', padding: '8px 0' }}>
                  <Space>
                    {t.status === 'doing' ? <Tag color="processing">进行中</Tag> : <Tag>待完成</Tag>}
                    <Text style={{ fontSize: 14 }}>{t.text}</Text>
                  </Space>
                </List.Item>
              )}
            />
          )}
        </Card>
      </div>

      {/* 右侧辅助看板 35% */}
      <div style={{ flex: 3.5, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* 路径详情 */}
        <Card className="glass-card" title={<Space><ArrowRightOutlined style={{ color: '#4A90F9' }} /><span>路径详情</span></Space>}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            <div style={{ flex: 1, textAlign: 'center', padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: 12, color: '#6B7280' }}>总知识点</div>
              <div className="mono" style={{ fontSize: 22, color: '#1F2733' }}>{total}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center', padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: 12, color: '#6B7280' }}>已完成</div>
              <div className="mono" style={{ fontSize: 22, color: '#10B981' }}>{done}</div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#6B7280', marginBottom: 4 }}>
            <span>进度</span>
            <span className="mono" style={{ color: '#0EA5E9' }}>{progress}%</span>
          </div>
          <Progress percent={progress} strokeColor={{ '0%': '#4A90F9', '100%': '#0EA5E9' }} trailColor="rgba(0,0,0,0.1)" />
        </Card>

        {/* 学习画像雷达 */}
        <Card className="glass-card" title={<Space><RadarChartOutlined style={{ color: '#4A90F9' }} /><span>学习画像雷达</span></Space>}>
          <ReactECharts option={radarOption} style={{ height: 260 }} />
        </Card>

        {/* 预计学习时长 */}
        <Card className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Text type="secondary" style={{ fontSize: 13 }}>预计学习时长</Text>
              <div className="mono" style={{ fontSize: 28, color: '#0EA5E9' }}>{estLabel}</div>
            </div>
            <Button type="primary" ghost icon={<ArrowRightOutlined />} onClick={() => { setCurrentStep(1); navigate('/main') }}>
              查看路径
            </Button>
          </div>
        </Card>
      </div>
    </div>
  )
}
