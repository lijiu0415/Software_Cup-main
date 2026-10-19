// useSSVEPBridge.js —— 连接本地 Python 桥（ws://127.0.0.1:8765）
//
// 消息协议（与 app/bridge_server.py 约定）：
//   Python -> 网页：
//     {"type":"state",  "state":"<当前状态>", "ctx":{...}}      状态变化
//     {"type":"result", "state":"<状态>",     "result":0~5}     一次有效 SSVEP 结果
//   网页 -> Python：
//     {"action":"restart"}                                     重置流程回登录页
import { ref, onMounted, onUnmounted } from 'vue'

const WS_URL = 'ws://127.0.0.1:8765'

export function useSSVEPBridge() {
  const connected = ref(false)
  const state = ref(null)       // 当前状态名
  const ctx = ref(null)         // 上下文快照（subject / profile_answers / 各索引）
  const lastResult = ref(null)  // 最近一次结果 {state, result}
  let ws = null
  const handlers = new Set()

  function connect() {
    ws = new WebSocket(WS_URL)
    ws.onopen = () => { connected.value = true }
    ws.onclose = () => { connected.value = false }
    ws.onerror = () => { connected.value = false }
    ws.onmessage = (e) => {
      let msg
      try { msg = JSON.parse(e.data) } catch { return }
      if (msg.type === 'state') {
        state.value = msg.state
        ctx.value = msg.ctx
      } else if (msg.type === 'result') {
        lastResult.value = msg
        handlers.forEach((fn) => fn(msg))
      }
    }
  }

  function send(action, extra = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action, ...extra }))
    }
  }

  function onResult(fn) {
    handlers.add(fn)
    return () => handlers.delete(fn)
  }

  onMounted(connect)
  onUnmounted(() => { if (ws) ws.close() })

  return { connected, state, ctx, lastResult, send, onResult }
}

// 结果 -> 业务值 的映射（与 Python 端块文字保持一致）
export const RESULT_MAP = {
  login_ssvep: (r) => (r === 0 ? '游客登录' : '登录'),
  subject_ssvep: (r) => ['软件安全', '人工智能导论'][r],
  profile_ssvep: (r) => r + 1,          // 0~4 -> 1~5 分
  quiz_ssvep: (r) => 'ABCD'[r],         // 0~3 -> A/B/C/D
}
