import { message } from 'antd'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'

const A4 = { w: 210, h: 297 } // mm
const MARGIN = 10 // mm

/**
 * 将报告内容导出为 PDF
 * - 捕获前临时展开滚动容器，确保完整内容（含图表）都被截取
 * - 按 A4 高度自动分页
 *
 * @param {HTMLElement} element 需要导出的 DOM 节点
 * @param {string} filename 导出文件名
 */
export async function exportPDF(element, filename = '学习报告.pdf') {
  if (!element) {
    message.warning('暂无可导出的报告内容')
    return
  }

  message.loading({ content: '正在生成 PDF…', key: 'pdf-export', duration: 0 })
  const restore = prepareForCapture(element)

  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#F5F7FA',
      scale: 2,
      useCORS: true,
      logging: false,
    })

    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pageW = A4.w - MARGIN * 2
    const pageH = A4.h - MARGIN * 2
    const imgW = pageW
    const imgH = (canvas.height * imgW) / canvas.width
    const imgData = canvas.toDataURL('image/png')

    let heightLeft = imgH
    let position = 0
    pdf.addImage(imgData, 'PNG', MARGIN, MARGIN, imgW, imgH)
    heightLeft -= pageH
    while (heightLeft > 0) {
      position += pageH
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', MARGIN, MARGIN - position, imgW, imgH)
      heightLeft -= pageH
    }

    pdf.save(filename)
    message.success({ content: '报告已导出', key: 'pdf-export', duration: 2 })
  } catch (err) {
    console.error('[exportPDF]', err)
    message.error({ content: '导出失败，请重试', key: 'pdf-export', duration: 2 })
  } finally {
    restore()
  }
}

// 临时展开可滚动 / 固定高度的容器，使 html2canvas 能截取完整内容
function prepareForCapture(el) {
  const fixes = []

  const expand = (node) => {
    if (!node || node.nodeType !== 1) return
    const cs = getComputedStyle(node)
    const clips = cs.overflowY === 'auto' || cs.overflowY === 'scroll' || cs.overflowY === 'hidden'
    const constrained = cs.height !== 'auto' || cs.maxHeight !== 'none'
    if (clips || constrained) {
      fixes.push({
        node,
        overflow: node.style.overflow,
        height: node.style.height,
        maxHeight: node.style.maxHeight,
      })
      node.style.overflow = 'visible'
      node.style.height = 'auto'
      node.style.maxHeight = 'none'
    }
  }

  // 目标元素自身 + 内部所有子节点
  expand(el)
  el.querySelectorAll('*').forEach(expand)

  // 祖先链（直到 body）：放开固定高度 / 裁剪
  let node = el.parentElement
  while (node && node !== document.body) {
    expand(node)
    node = node.parentElement
  }

  return () => {
    fixes.forEach(({ node, overflow, height, maxHeight }) => {
      node.style.overflow = overflow
      node.style.height = height
      node.style.maxHeight = maxHeight
    })
  }
}
