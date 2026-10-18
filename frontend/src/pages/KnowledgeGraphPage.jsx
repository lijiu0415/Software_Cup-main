import React, { useState, useEffect, useMemo } from 'react'
import { Card, Tag, Space, Typography, Progress, Spin } from 'antd'
import { AimOutlined, RadarChartOutlined, EnvironmentOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import ReactECharts from 'echarts-for-react'
import useStore from '../store/useStore'
import { getKgGraph, getLearningPath } from '../api'
import ProfilePlaceholder from '../components/ProfilePlaceholder'

const { Text } = Typography

const radarOption = {
  tooltip: {},
  radar: {
    indicator: [
      { name: '理论基础', max: 5 }, { name: '实践能力', max: 5 }, { name: '算法思维', max: 5 },
      { name: '工程应用', max: 5 }, { name: '知识迁移', max: 5 },
    ],
    radius: '62%',
    axisName: { color: '#6B7280', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(0,0,0,0.1)' } },
    splitArea: { areaStyle: { color: ['rgba(74,144,249,0.03)', 'rgba(14,165,233,0.03)'] } },
  },
  series: [{
    type: 'radar',
    data: [{
      value: [0, 0, 0, 0, 0], name: '能力画像',
      areaStyle: { color: 'rgba(14,165,233,0.25)' },
      lineStyle: { color: '#0EA5E9', width: 2 },
      itemStyle: { color: '#0EA5E9' },
    }],
  }],
}

export default function KnowledgeGraphPage() {
  const navigate = useNavigate()
  const { studentId, studentProfile, questionnaire_complete, setPendingKpId, setCurrentStep } = useStore()
  const [graphData, setGraphData] = useState({ nodes: [], links: [], nameMap: {} })
  const [pathStats, setPathStats] = useState({ total: 0, completed: 0 })
  const [loading, setLoading] = useState(true)

  const course = studentProfile?.course || studentProfile?.course_name || '人工智能导论'
  const baseLevel = studentProfile?.base_level || 0
  const style = studentProfile?.cognitive_style || ''
  const goal = studentProfile?.learn_goal || ''

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [graphRes, pathRes] = await Promise.all([
          getKgGraph(course),
          getLearningPath(studentId),
        ])
        const rawNodes = graphRes.data.nodes || []
        const edges = graphRes.data.edges || []
        const path = pathRes.data.path || []
        const completed = pathRes.data.completed || []

        const completedSet = new Set(completed.map((c) => c.kp_id))
        const masteryMap = {}
        path.forEach((p) => { masteryMap[p.kp_id] = p.mastery })

        const nameMap = {}
        rawNodes.forEach((n) => { nameMap[n.id] = n.name })

        // 节点用 kp_id 作为唯一标识（便于连线匹配），显示名走 label.formatter
        const nodes = rawNodes.map((n) => {
          const isCompleted = completedSet.has(n.id)
          const isLearning = masteryMap[n.id] > 0
          return {
            name: n.id,
            symbolSize: isCompleted ? 58 : isLearning ? 62 : 46,
            itemStyle: {
              color: isCompleted ? '#10B981' : isLearning ? '#0EA5E9' : 'rgba(0,0,0,0.28)',
            },
          }
        })
        const links = edges.map((e) => ({ source: e.from, target: e.to }))

        setGraphData({ nodes, links, nameMap })
        setPathStats({ total: path.length + completed.length, completed: completed.length })
      } catch (err) {
        // 拉取失败时保留空图
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [course, studentId])

  const graphOption = useMemo(() => ({
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: 'rgba(0,0,0,0.1)',
      textStyle: { color: '#1F2733' },
      formatter: (p) => (p.dataType === 'node' ? graphData.nameMap[p.name] || p.name : ''),
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      cursor: 'pointer',
      label: {
        show: true,
        color: '#1F2733',
        fontSize: 11,
        formatter: (p) => graphData.nameMap[p.name] || p.name,
      },
      force: { repulsion: 320, edgeLength: 90 },
      lineStyle: { color: 'rgba(0,0,0,0.25)', width: 1 },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: 5,
      data: graphData.nodes,
      links: graphData.links,
    }],
  }), [graphData])

  const progress = pathStats.total ? Math.round((pathStats.completed / pathStats.total) * 100) : 0

  if (!questionnaire_complete) return <ProfilePlaceholder />

  // 点击知识图谱节点 → 跳转到对应知识点学习
  const handleNodeClick = (params) => {
    if (params.dataType === 'node' && params.data && params.data.name) {
      setPendingKpId(params.data.name) // node.name 即 kp_id
      setCurrentStep(2)
      navigate('/main')
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', gap: 16, overflow: 'hidden' }}>
      {/* 左 25% 画像摘要 */}
      <div style={{ flex: '0 0 22%', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Card className="glass-card" title={<Space><EnvironmentOutlined style={{ color: '#4A90F9' }} /><span>学习画像摘要</span></Space>} size="small">
          {questionnaire_complete ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>当前课程</Text>
                <div><Tag color="blue" style={{ marginTop: 4 }}>{course}</Tag></div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>学习风格</Text>
                <div><Tag color="cyan" style={{ marginTop: 4 }}>{style}</Tag></div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>基础水平</Text>
                <div style={{ marginTop: 4 }}>
                  <Text strong className="mono" style={{ fontSize: 20, color: '#0EA5E9' }}>{baseLevel}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}> / 5</Text>
                </div>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>阶段目标</Text>
                <div style={{ marginTop: 4, fontSize: 13, color: '#1F2733' }}>{goal}</div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 20, color: '#F5222D', fontSize: 13, fontWeight: 600 }}>
              待画像确认
            </div>
          )}
        </Card>
      </div>

      {/* 中 55% 关系图 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <Card className="glass-card" title={<Space><AimOutlined style={{ color: '#0EA5E9' }} /><span>知识关系图</span></Space>} style={{ height: '100%' }}
          extra={<Space size={8}>
            <Tag color="success">已掌握</Tag><Tag color="cyan">学习中</Tag><Tag>未学习</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>点击节点进入学习</Text>
          </Space>}
          styles={{ body: { height: 'calc(100% - 56px)' } }}
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
          ) : (
            <ReactECharts option={graphOption} style={{ height: '100%', minHeight: 380 }} onEvents={{ click: handleNodeClick }} />
          )}
        </Card>
      </div>

      {/* 右 20% 路径详情 */}
      <div style={{ flex: '0 0 22%', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Card className="glass-card" title="路径详情" size="small">
          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            <div style={{ flex: 1, textAlign: 'center', padding: 10, borderRadius: 10, background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: 11, color: '#6B7280' }}>总知识点</div>
              <div className="mono" style={{ fontSize: 20, color: '#1F2733' }}>{pathStats.total}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center', padding: 10, borderRadius: 10, background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize: 11, color: '#6B7280' }}>已完成</div>
              <div className="mono" style={{ fontSize: 20, color: '#10B981' }}>{pathStats.completed}</div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#6B7280', marginBottom: 4 }}>
            <span>整体进度</span>
            <span className="mono" style={{ color: '#0EA5E9' }}>{progress}%</span>
          </div>
          <Progress percent={progress} strokeColor={{ '0%': '#4A90F9', '100%': '#0EA5E9' }} trailColor="rgba(0,0,0,0.1)" />
        </Card>
        <Card className="glass-card" title={<Space><RadarChartOutlined style={{ color: '#4A90F9' }} /><span>能力雷达</span></Space>} size="small">
          <ReactECharts option={radarOption} style={{ height: 220 }} />
        </Card>
      </div>
    </div>
  )
}
