import React, { useEffect, useRef, useState } from 'react'
import { Card, Spin } from 'antd'
import { BulbOutlined } from '@ant-design/icons'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

const transformer = new Transformer()

// 分支颜色样式
const BRANCH_STYLES = `
.branch-green { color: #52c41a !important; }
.branch-green rect { fill: #f6ffed !important; stroke: #52c41a !important; }
.branch-blue { color: #1677ff !important; }
.branch-blue rect { fill: #e6f4ff !important; stroke: #1677ff !important; }
.branch-orange { color: #fa8c16 !important; }
.branch-orange rect { fill: #fff7e6 !important; stroke: #fa8c16 !important; }
.branch-purple { color: #722ed1 !important; }
.branch-purple rect { fill: #f9f0ff !important; stroke: #722ed1 !important; }
.branch-cyan { color: #13c2c2 !important; }
.branch-cyan rect { fill: #e6fffb !important; stroke: #13c2c2 !important; }
`

const COLOR_CLASS_MAP = {
  '前置知识': 'branch-green',
  '核心概念': 'branch-blue',
  '相关算法': 'branch-orange',
  '应用场景': 'branch-purple',
  '拓展延伸': 'branch-cyan',
}

function applyColors(root) {
  if (!root) return
  const label = root.content || ''
  // 匹配 H2 标题对应的分支名
  for (const [branch, className] of Object.entries(COLOR_CLASS_MAP)) {
    if (label.startsWith(branch)) {
      root.content = label.replace(branch, branch)
      root.payload = { ...root.payload, className }
      break
    }
  }
  if (root.children) {
    root.children.forEach(applyColors)
  }
}

export default function MindMap({ mermaidCode }) {
  const containerRef = useRef(null)
  const svgRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const render = async () => {
    if (!mermaidCode || !svgRef.current) return
    setLoading(true)
    setError(null)

    try {
      // 清除旧内容
      svgRef.current.innerHTML = ''

      const { root, features } = transformer.transform(mermaidCode)
      applyColors(root)

      // 注入样式
      const existing = document.getElementById('mindmap-branch-styles')
      if (!existing) {
        const style = document.createElement('style')
        style.id = 'mindmap-branch-styles'
        style.textContent = BRANCH_STYLES
        document.head.appendChild(style)
      }

      Markmap.create(svgRef.current, {}, root)
    } catch (err) {
      console.error('markmap render error:', err)
      setError('思维导图渲染失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    render()
  }, [mermaidCode])

  if (!mermaidCode) {
    return (
      <Card title={<><BulbOutlined /> 思维导图</>}>
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          暂无思维导图
        </div>
      </Card>
    )
  }

  return (
    <Card
      title={<><BulbOutlined /> 知识点思维导图</>}
      styles={{ body: { padding: 16 } }}
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="正在渲染思维导图..." />
        </div>
      )}
      {error && (
        <div style={{ textAlign: 'center', padding: 20, color: '#ff4d4f' }}>
          {error}
        </div>
      )}
      <div
        style={{ display: 'flex', justifyContent: 'center', overflow: 'auto' }}
      >
        <svg ref={svgRef} style={{ minHeight: 300, width: '100%', maxWidth: 800 }} />
      </div>
      {/* 图例 */}
      <div style={{ marginTop: 16, display: 'flex', justifyContent: 'center', gap: 16, flexWrap: 'wrap' }}>
        {Object.entries(COLOR_CLASS_MAP).map(([name, cls]) => {
          const colors = {
            'branch-green': '#52c41a',
            'branch-blue': '#1677ff',
            'branch-orange': '#fa8c16',
            'branch-purple': '#722ed1',
            'branch-cyan': '#13c2c2',
          }
          return (
            <span key={name}>
              <span style={{
                display: 'inline-block', width: 12, height: 12,
                background: colors[cls], borderRadius: 2, marginRight: 4,
              }} />
              {name}
            </span>
          )
        })}
      </div>
    </Card>
  )
}
