import React, { useState, useEffect, useRef } from 'react'
import { Card, Menu, Button, Space, Typography, List, Tag, Spin, Collapse, Progress, Statistic, Empty } from 'antd'
import {
  FileTextOutlined,
  BarChartOutlined,
  WarningOutlined,
  RiseOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import useStore from '../store/useStore'
import { getReportOverview, getChapterAnalysis, getAbilityGrowth, getWrongAnalysis } from '../api'
import ProfilePlaceholder from '../components/ProfilePlaceholder'
import { exportPDF } from '../utils/exportPDF'

const { Text } = Typography

const CATEGORY_ITEMS = [
  { key: 'overview', icon: <FileTextOutlined />, label: '总览报告' },
  { key: 'chapter', icon: <BarChartOutlined />, label: '章节分析' },
  { key: 'wrong', icon: <WarningOutlined />, label: '错题分析' },
  { key: 'growth', icon: <RiseOutlined />, label: '能力成长' },
]

function CenterSpin() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Spin size="large" />
    </div>
  )
}

function buildLineOption(data) {
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' } },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category', data: data.days,
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.2)' } },
      axisLabel: { color: '#6B7280' },
    },
    yAxis: {
      type: 'value', name: '个知识点',
      nameTextStyle: { color: '#6B7280' },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
      axisLabel: { color: '#6B7280' },
    },
    series: [{
      type: 'line', data: data.counts, smooth: true,
      lineStyle: { color: '#0EA5E9', width: 2 },
      itemStyle: { color: '#0EA5E9' },
      areaStyle: { color: 'rgba(14,165,233,0.15)' },
    }],
  }
}

function buildDonutOption(data) {
  return {
    tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' } },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: '#6B7280', fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['55%', '75%'], center: ['50%', '42%'],
      itemStyle: { borderColor: '#F5F7FA', borderWidth: 2 },
      label: {
        show: true, position: 'center',
        formatter: `{name|已掌握}\n{value|${data.mastered}}`,
        rich: {
          name: { color: '#6B7280', fontSize: 12, lineHeight: 20 },
          value: { color: '#10B981', fontSize: 26, fontWeight: 700, fontFamily: 'SF Mono, Consolas, monospace', lineHeight: 34 },
        },
      },
      data: [
        { value: data.mastered, name: '已掌握', itemStyle: { color: '#10B981' } },
        { value: data.unmastered, name: '未掌握', itemStyle: { color: 'rgba(0,0,0,0.15)' } },
      ],
    }],
  }
}

function buildBarOption(data) {
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' } },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category', data: data.map((c) => c.name),
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.2)' } },
      axisLabel: { color: '#6B7280' },
    },
    yAxis: { type: 'value', max: 100, splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }, axisLabel: { color: '#6B7280' } },
    series: [{
      type: 'bar', data: data.map((c) => c.progress), barWidth: 36,
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#4A90F9' }, { offset: 1, color: '#0EA5E9' }] },
      },
    }],
  }
}

function buildRadarOption(data) {
  return {
    tooltip: {},
    legend: { bottom: 0, icon: 'circle', textStyle: { color: '#6B7280', fontSize: 11 } },
    radar: {
      indicator: data.dimensions.map((d) => ({ name: d, max: 5 })),
      radius: '60%',
      axisName: { color: '#6B7280', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.1)' } },
      splitArea: { areaStyle: { color: ['rgba(74,144,249,0.03)', 'rgba(14,165,233,0.03)'] } },
    },
    series: [{
      type: 'radar',
      data: [
        { value: data.initial, name: '期初', lineStyle: { color: '#6B7280' }, itemStyle: { color: '#6B7280' }, areaStyle: { color: 'rgba(107,114,128,0.15)' } },
        { value: data.current, name: '当前', lineStyle: { color: '#0EA5E9' }, itemStyle: { color: '#0EA5E9' }, areaStyle: { color: 'rgba(14,165,233,0.25)' } },
      ],
    }],
  }
}

function buildTimelineOption(data) {
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' } },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category', data: data.days,
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.2)' } },
      axisLabel: { color: '#6B7280' },
    },
    yAxis: {
      type: 'value', name: '掌握知识点', minInterval: 1,
      nameTextStyle: { color: '#6B7280' },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
      axisLabel: { color: '#6B7280' },
    },
    series: [{
      type: 'line', data: data.mastered, smooth: true,
      lineStyle: { color: '#10B981', width: 2 },
      itemStyle: { color: '#10B981' },
      areaStyle: { color: 'rgba(16,185,129,0.15)' },
    }],
  }
}

function buildGrowthBarOption(dimensions, growth) {
  return {
    tooltip: {
      trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' },
      formatter: (p) => `${p[0].name}：${p[0].value >= 0 ? '+' : ''}${p[0].value}`,
    },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category', data: dimensions,
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.2)' } },
      axisLabel: { color: '#6B7280' },
    },
    yAxis: { type: 'value', name: '成长幅度', splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }, axisLabel: { color: '#6B7280' } },
    series: [{
      type: 'bar', data: growth, barWidth: 30,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: (p) => (p.value >= 0 ? '#10B981' : '#EF4444'),
      },
    }],
  }
}

function buildCountBarOption(data) {
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' } },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category', data: data.map((d) => d.name),
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.2)' } },
      axisLabel: { color: '#6B7280', interval: 0 },
    },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }, axisLabel: { color: '#6B7280' } },
    series: [{
      type: 'bar', data: data.map((d) => d.value), barWidth: 28,
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#F87171' }, { offset: 1, color: '#EF4444' }] },
      },
    }],
  }
}

function buildWrongTrendOption(data) {
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'rgba(0,0,0,0.1)', textStyle: { color: '#1F2733' } },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category', data: data.days,
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.2)' } },
      axisLabel: { color: '#6B7280' },
    },
    yAxis: { type: 'value', name: '错题数', minInterval: 1, nameTextStyle: { color: '#6B7280' }, splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }, axisLabel: { color: '#6B7280' } },
    series: [{
      type: 'line', data: data.wrong, smooth: true,
      lineStyle: { color: '#EF4444', width: 2 },
      itemStyle: { color: '#EF4444' },
      areaStyle: { color: 'rgba(239,68,68,0.12)' },
    }],
  }
}

export default function ReportPage() {
  const { studentId, questionnaire_complete } = useStore()
  const reportRef = useRef(null)
  const [active, setActive] = useState('overview')
  const [report, setReport] = useState(null)
  const [chapterData, setChapterData] = useState(null)
  const [growthData, setGrowthData] = useState(null)
  const [wrongData, setWrongData] = useState(null)
  const [loading, setLoading] = useState(true)

  // 总览报告
  useEffect(() => {
    if (!studentId) { setLoading(false); return }
    setLoading(true)
    getReportOverview(studentId)
      .then((res) => setReport(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [studentId])

  // 章节分析（切换到该 Tab 时拉取）
  useEffect(() => {
    if (!studentId || active !== 'chapter') return
    getChapterAnalysis(studentId)
      .then((res) => setChapterData(res.data))
      .catch(() => {})
  }, [studentId, active])

  // 能力成长（切换到该 Tab 时拉取）
  useEffect(() => {
    if (!studentId || active !== 'growth') return
    getAbilityGrowth(studentId)
      .then((res) => setGrowthData(res.data))
      .catch(() => {})
  }, [studentId, active])

  // 错题分析（切换到该 Tab 时拉取）
  useEffect(() => {
    if (!studentId || active !== 'wrong') return
    getWrongAnalysis(studentId)
      .then((res) => setWrongData(res.data))
      .catch(() => {})
  }, [studentId, active])

  if (!questionnaire_complete) return <ProfilePlaceholder />

  const renderOverview = () => (
    <>
      {/* 中 图表区 */}
      <div style={{ flex: 1, minWidth: 0, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Card className="glass-card" title="学习活跃趋势">
          <ReactECharts option={buildLineOption(report.study_trend)} style={{ height: 240 }} />
        </Card>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Card className="glass-card" title="知识点掌握度">
            <ReactECharts option={buildDonutOption(report.mastery)} style={{ height: 220 }} />
          </Card>
          <Card className="glass-card" title="章节完成度">
            <ReactECharts option={buildBarOption(report.chapters)} style={{ height: 220 }} />
          </Card>
        </div>
        <Card className="glass-card" title="能力成长对比">
          <ReactECharts option={buildRadarOption(report.ability_growth)} style={{ height: 260 }} />
        </Card>
      </div>

      {/* 右 总结区 */}
      <div style={{ flex: '0 0 24%', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Card className="glass-card" title="AI 学习总结" size="small">
          <Text style={{ fontSize: 13, lineHeight: 1.8 }}>{report.summary}</Text>
        </Card>
        <Card className="glass-card" title="提升建议" size="small">
          <List
            size="small"
            dataSource={report.suggestions}
            renderItem={(s, i) => (
              <List.Item style={{ border: 'none', padding: '6px 0' }}>
                <Space>
                  <Tag color="blue">{i + 1}</Tag>
                  <Text style={{ fontSize: 13 }}>{s}</Text>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      </div>
    </>
  )

  const renderChapter = () => {
    if (!chapterData) return <CenterSpin />
    const chapters = chapterData.chapters || []

    const collapseItems = chapters.map((c) => ({
      key: c.chapter_id,
      label: (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', paddingRight: 8 }}>
          <Space size={8}>
            <Text strong style={{ fontSize: 13 }}>{c.name}</Text>
            <Tag color={c.progress < 40 ? 'red' : c.progress < 80 ? 'orange' : 'green'}>{c.completed}/{c.total}</Tag>
          </Space>
          <span className="mono" style={{ fontSize: 12, color: c.progress < 40 ? '#EF4444' : '#10B981' }}>{c.progress}%</span>
        </div>
      ),
      children: (
        <List
          size="small"
          dataSource={c.kps}
          renderItem={(kp) => (
            <List.Item style={{ border: 'none', padding: '6px 0' }}>
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space size={6}>
                    <Tag color={kp.difficulty <= 2 ? 'green' : kp.difficulty <= 3 ? 'orange' : 'red'}>L{kp.difficulty}</Tag>
                    <Text style={{ fontSize: 13 }}>{kp.name}</Text>
                    {kp.completed && <Tag color="success">已掌握</Tag>}
                  </Space>
                  <span className="mono" style={{ fontSize: 12, color: '#6B7280' }}>{Math.round(kp.mastery * 100)}%</span>
                </div>
                <Progress
                  percent={Math.round(kp.mastery * 100)}
                  showInfo={false}
                  size="small"
                  strokeColor={kp.completed ? '#10B981' : '#0EA5E9'}
                  trailColor="rgba(0,0,0,0.1)"
                  style={{ marginTop: 4 }}
                />
              </div>
            </List.Item>
          )}
        />
      ),
    }))

    return (
      <>
        <div style={{ flex: 1, minWidth: 0, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card className="glass-card" title="章节完成度">
            <ReactECharts option={buildBarOption(chapters.map((c) => ({ name: c.name, progress: c.progress })))} style={{ height: 240 }} />
          </Card>
          <Card className="glass-card" title="章节平均掌握度">
            <ReactECharts option={buildBarOption(chapters.map((c) => ({ name: c.name, progress: Math.round(c.avg_mastery * 100) })))} style={{ height: 240 }} />
          </Card>
        </div>
        <div style={{ flex: '0 0 26%', overflow: 'auto' }}>
          <Card className="glass-card" title="章节明细" size="small">
            {chapters.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#6B7280', padding: 24 }}>暂无章节数据</div>
            ) : (
              <Collapse ghost defaultActiveKey={chapters[0]?.chapter_id} items={collapseItems} />
            )}
          </Card>
        </div>
      </>
    )
  }

  const renderGrowth = () => {
    if (!growthData) return <CenterSpin />
    const g = growthData
    const hasTimeline = g.timeline && g.timeline.days && g.timeline.days.length > 0

    return (
      <>
        <div style={{ flex: 1, minWidth: 0, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card className="glass-card" title="能力成长曲线">
            {hasTimeline ? (
              <ReactECharts option={buildTimelineOption(g.timeline)} style={{ height: 240 }} />
            ) : (
              <div style={{ textAlign: 'center', color: '#6B7280', padding: 48 }}>完成知识点后，这里会展示能力成长曲线</div>
            )}
          </Card>
          <Card className="glass-card" title="各维度成长幅度">
            <ReactECharts option={buildGrowthBarOption(g.dimensions, g.growth)} style={{ height: 240 }} />
          </Card>
        </div>
        <div style={{ flex: '0 0 26%', display: 'flex', flexDirection: 'column', gap: 16, overflow: 'auto' }}>
          <Card className="glass-card" title="能力雷达" size="small">
            <ReactECharts option={buildRadarOption({ dimensions: g.dimensions, initial: g.initial, current: g.current })} style={{ height: 220 }} />
          </Card>
          <Card className="glass-card" title="画像更新记录" size="small">
            {g.profile_rounds && g.profile_rounds.length > 0 ? (
              <List
                size="small"
                dataSource={g.profile_rounds}
                renderItem={(r) => (
                  <List.Item style={{ border: 'none', padding: '6px 0' }}>
                    <Space direction="vertical" size={2} style={{ width: '100%' }}>
                      <Space size={8}>
                        <Tag color="blue">第{r.round}轮</Tag>
                        <Text style={{ fontSize: 12 }}>{r.time}</Text>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        基础 {r.base_level} · 速度 {r.learn_speed} · {r.cognitive_style}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <div style={{ textAlign: 'center', color: '#6B7280', padding: 24 }}>暂无画像记录</div>
            )}
          </Card>
        </div>
      </>
    )
  }

  const renderWrong = () => {
    if (!wrongData) return <CenterSpin />
    const w = wrongData
    return (
      <>
        <div style={{ flex: 1, minWidth: 0, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
            <Card className="glass-card" size="small"><Statistic title="答题总数" value={w.total} suffix="题" /></Card>
            <Card className="glass-card" size="small"><Statistic title="答对" value={w.correct} suffix="题" valueStyle={{ color: '#10B981' }} /></Card>
            <Card className="glass-card" size="small"><Statistic title="答错" value={w.wrong} suffix="题" valueStyle={{ color: '#EF4444' }} /></Card>
            <Card className="glass-card" size="small"><Statistic title="正确率" value={w.accuracy} suffix="%" /></Card>
          </div>
          <Card className="glass-card" title="错题时间趋势">
            {w.trend && w.trend.days && w.trend.days.length > 0 ? (
              <ReactECharts option={buildWrongTrendOption(w.trend)} style={{ height: 220 }} />
            ) : (
              <div style={{ textAlign: 'center', color: '#6B7280', padding: 48 }}>暂无错题记录</div>
            )}
          </Card>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Card className="glass-card" title="题型分布">
              {w.by_type && w.by_type.length > 0 ? (
                <ReactECharts option={buildCountBarOption(w.by_type.map((t) => ({ name: t.type, value: t.wrong })))} style={{ height: 220 }} />
              ) : (
                <div style={{ textAlign: 'center', color: '#6B7280', padding: 48 }}>暂无数据</div>
              )}
            </Card>
            <Card className="glass-card" title="章节分布">
              {w.by_chapter && w.by_chapter.length > 0 ? (
                <ReactECharts option={buildCountBarOption(w.by_chapter.map((c) => ({ name: c.chapter, value: c.wrong })))} style={{ height: 220 }} />
              ) : (
                <div style={{ textAlign: 'center', color: '#6B7280', padding: 48 }}>暂无数据</div>
              )}
            </Card>
          </div>
        </div>
        <div style={{ flex: '0 0 26%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card className="glass-card" title="易错知识点排行" size="small">
            {w.by_kp && w.by_kp.length > 0 ? (
              <List
                size="small"
                dataSource={w.by_kp}
                renderItem={(k, i) => (
                  <List.Item style={{ border: 'none', padding: '6px 0' }}>
                    <Space>
                      <Tag color={i === 0 ? 'red' : i === 1 ? 'orange' : 'blue'}>{i + 1}</Tag>
                      <Text style={{ fontSize: 13 }}>{k.name}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>错 {k.wrong_count} 次</Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <div style={{ textAlign: 'center', color: '#6B7280', padding: 24 }}>暂无错题数据</div>
            )}
          </Card>
          <Card className="glass-card" title="错题明细" size="small">
            {w.wrong_list && w.wrong_list.length > 0 ? (
              <List
                size="small"
                dataSource={w.wrong_list}
                renderItem={(r) => (
                  <List.Item style={{ border: 'none', padding: '8px 0', alignItems: 'flex-start' }}>
                    <div style={{ width: '100%' }}>
                      <Space size={6} style={{ marginBottom: 4 }}>
                        <Tag color="red">{r.type}</Tag>
                        {r.chapter && <Tag>{r.chapter}</Tag>}
                        <Text type="secondary" style={{ fontSize: 11 }}>{r.time}</Text>
                      </Space>
                      <div style={{ fontSize: 13 }}><Text strong>{r.question}</Text></div>
                      <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>
                        你的答案：<Text type="danger" style={{ fontSize: 12 }}>{r.student_answer || '未作答'}</Text>
                        <span style={{ margin: '0 6px' }}>·</span>
                        正确答案：<Text type="success" style={{ fontSize: 12 }}>{r.correct_answer}</Text>
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            ) : (
              <div style={{ textAlign: 'center', color: '#6B7280', padding: 24 }}>暂无错题明细</div>
            )}
          </Card>
        </div>
      </>
    )
  }

  const renderBody = () => {
    if (active === 'chapter') return renderChapter()
    if (active === 'wrong') return renderWrong()
    if (active === 'growth') return renderGrowth()
    if (loading || !report) return <CenterSpin />
    return renderOverview()
  }

  return (
    <div style={{ height: '100%', display: 'flex', gap: 16, overflow: 'hidden' }}>
      {/* 左 报告分类 */}
      <div style={{ flex: '0 0 20%' }}>
        <Card
          className="glass-card"
          title="报告分类"
          size="small"
          style={{ height: '100%' }}
          extra={
            <Button size="small" type="primary" ghost icon={<DownloadOutlined />} onClick={() => exportPDF(reportRef.current)}>
              导出
            </Button>
          }
        >
          <Menu
            mode="inline"
            selectedKeys={[active]}
            onClick={({ key }) => setActive(key)}
            items={CATEGORY_ITEMS}
            style={{ background: 'transparent', border: 'none' }}
          />
        </Card>
      </div>

      <div ref={reportRef} style={{ flex: 1, minWidth: 0, display: 'flex', gap: 16, overflow: 'hidden' }}>
        {renderBody()}
      </div>
    </div>
  )
}
