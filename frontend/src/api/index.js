import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 读取本地 token（登录成功后写入 localStorage）
const getToken = () => localStorage.getItem('token') || ''

// 请求拦截器：自动携带 Bearer token
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截器：401 时清除凭证并跳回登录页
api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('studentId')
      localStorage.removeItem('studentName')
      localStorage.removeItem('studentProfile')
      if (!window.location.hash.startsWith('#/')) {
        window.location.hash = '#/'
      }
    }
    return Promise.reject(err)
  },
)

// 用户认证
export const login = (username, password) =>
  api.post('/auth/login', { username, password })

export const register = (username, password) =>
  api.post('/auth/register', { username, password })

// 注销用户账号（删除用户及全部数据，不可撤回）
export const deleteAccount = (username) =>
  api.post('/auth/delete', { username })

// 资源生成（标准模式）
export const generateResources = (studentId, kpId) =>
  api.post('/resource/generate', { student_id: studentId, kp_id: kpId })

// 资源生成（流式 SSE + 进度条）
export const generateResourcesStream = async (studentId, kpId, { onProgress, onDone, onError }) => {
  try {
    const resp = await fetch('/api/resource/generate/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ student_id: studentId, kp_id: kpId }),
    })

    if (!resp.ok) {
      onError(`服务器错误: ${resp.status}`)
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'start') {
            onProgress({ phase: 'start', total: event.total, agents: event.agents })
          } else if (event.type === 'progress') {
            onProgress({
              phase: event.status,
              agent: event.agent,
              key: event.key,
              chars: event.chars,
              cached: event.cached,
              error: event.error,
            })
          } else if (event.type === 'done') {
            onDone(event.results)
          }
        } catch {
          // 跳过解析失败的行
        }
      }
    }
  } catch (err) {
    onError(`网络请求失败: ${err.message}`)
  }
}

// 学习路径
export const getLearningPath = (studentId) =>
  api.get('/path/get_path', { params: { student_id: studentId } })

// AI 个性化学习路径规划（规则算法兜底）
export const planLearningPath = (studentId) =>
  api.post('/path/plan', { student_id: studentId })

// 各科目学习完成度
export const getCourseProgress = (studentId) =>
  api.get('/path/course_progress', { params: { student_id: studentId } })

// 更新掌握度
export const updateMastery = (studentId, kpId, newMastery) =>
  api.put('/path/update_mastery', {
    student_id: studentId,
    kp_id: kpId,
    new_mastery: newMastery,
  })

// 标记知识点已完成学习
export const completeKp = (studentId, kpId) =>
  api.post('/path/complete_kp', { student_id: studentId, kp_id: kpId })

// 前置校验
export const checkPrerequisites = (kpId, studentId) =>
  api.get(`/kg/check_pre/${kpId}/${studentId}`)

// 知识点列表
export const getKnowledgePoints = (chapterId, course) =>
  api.get('/kg/knowledge_points', { params: { chapter_id: chapterId, course } })

// 知识点详情
export const getKpDetail = (kpId) =>
  api.get(`/kg/knowledge_point/${kpId}`)

// 知识图谱（按课程）
export const getKgGraph = (course) =>
  api.get('/kg/graph', { params: { course } })

// 重置学生数据
export const resetStudent = (studentId) =>
  api.post('/chat/reset', { student_id: studentId })

// 当前画像（页面刷新后恢复画像）
export const getProfile = (studentId) =>
  api.get(`/chat/profile/${studentId}`)

// 切换当前课程（快照/恢复画像，返回新课程画像与完成态）
export const switchCourse = (studentId, course) =>
  api.post('/profile/course/switch', { student_id: studentId, course })

// 提交评估问卷（分析生成画像，按课程隔离）
export const submitQuestionnaire = (studentId, answers, course = '人工智能导论') =>
  api.post('/questionnaire/submit', { student_id: studentId, answers, course })

// 问卷完成状态（页面刷新后恢复，按课程隔离）
export const getQuestionnaireStatus = (studentId, course = '人工智能导论') =>
  api.get(`/questionnaire/status/${studentId}`, { params: { course } })

// ============================================================
// 题库 / 答题 / 错题本
// ============================================================
export const getExerciseList = (course) =>
  api.get('/exercise/list', { params: { course } })

export const submitAnswer = (studentId, exId, studentAnswer) =>
  api.post('/exercise/submit', { student_id: studentId, ex_id: exId, student_answer: studentAnswer })

export const getWrongBook = (studentId, course) =>
  api.get('/exercise/wrong_book', { params: { student_id: studentId, course } })

export const getExerciseChapters = (studentId, course) =>
  api.get('/exercise/chapters', { params: { student_id: studentId, course } })

export const getChapterTest = (studentId, chapterId) =>
  api.get(`/exercise/test/${chapterId}`, { params: { student_id: studentId } })

export const submitChapterTest = (studentId, chapterId, answers) =>
  api.post('/exercise/submit_test', { student_id: studentId, chapter_id: chapterId, answers })

export const getChapterTestResult = (studentId, chapterId) =>
  api.get(`/exercise/result/${chapterId}`, { params: { student_id: studentId } })

// ============================================================
// 个人资料（学习设置 / 每日目标 / 番茄钟 / 遗忘曲线复习）
// ============================================================
export const getProfileSummary = (studentId, course) =>
  api.get(`/profile/summary/${studentId}`, { params: { course } })

export const getProfileSettings = (studentId, course) =>
  api.get(`/profile/settings/${studentId}`, { params: { course } })

export const updateProfileSettings = (studentId, settings, course) =>
  api.put('/profile/settings', { student_id: studentId, ...settings, course })

export const completePomodoro = (studentId, { focus_min, break_min }, course) =>
  api.post('/profile/pomodoro', { student_id: studentId, focus_min, break_min, course })

export const markKpReviewed = (studentId, kpId) =>
  api.post(`/profile/review/${kpId}`, { student_id: studentId })

// 书架：上传 / 列表 / 删除教材
export const uploadTextbook = (studentId, file) => {
  const form = new FormData()
  form.append('student_id', studentId)
  form.append('file', file)
  return api.post('/profile/textbooks', form)
}

export const getTextbooks = (studentId) =>
  api.get(`/profile/textbooks/${studentId}`)

export const deleteTextbook = (studentId, textbookId) =>
  api.delete(`/profile/textbooks/${textbookId}`, { params: { student_id: studentId } })

// 编程测试Agent：出题 + 实时批改（不计分，影响画像）
export const startProgramTest = (studentId, chapterId) =>
  api.post('/exercise/program/start', { student_id: studentId, chapter_id: chapterId })

export const gradeProgramTest = (studentId, chapterId, payload) =>
  api.post('/exercise/program/grade', { student_id: studentId, chapter_id: chapterId, ...payload })

// ============================================================
// 学习档案报告（GET /report/overview）
// ============================================================
export const getReportOverview = (studentId) =>
  api.get('/report/overview', { params: { student_id: studentId } })

// 章节分析
export const getChapterAnalysis = (studentId) =>
  api.get('/report/chapter_analysis', { params: { student_id: studentId } })

// 能力成长
export const getAbilityGrowth = (studentId) =>
  api.get('/report/ability_growth', { params: { student_id: studentId } })

// 错题分析
export const getWrongAnalysis = (studentId) =>
  api.get('/report/wrong_analysis', { params: { student_id: studentId } })

// ============================================================
// 答疑助手（独立于对话画像）
// ============================================================
// 流式答疑（SSE）
export const qaChatStream = async (studentId, content, { onStart, onChunk, onDone, onError }) => {
  try {
    const resp = await fetch('/api/qa/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ student_id: studentId, content }),
    })

    if (!resp.ok) {
      onError(`服务器错误: ${resp.status}`)
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'start') {
            onStart?.(event)
          } else if (event.type === 'chunk') {
            onChunk(event.content)
          } else if (event.type === 'done') {
            onDone(event)
          } else if (event.type === 'error') {
            onError(event.message)
          }
        } catch {
          // 跳过解析失败的行
        }
      }
    }
  } catch (err) {
    onError(`网络请求失败: ${err.message}`)
  }
}

// 答疑历史
export const getQaHistory = (studentId) =>
  api.get(`/qa/history/${studentId}`)

// 清空答疑历史
export const deleteQaHistory = (studentId) =>
  api.delete(`/qa/history/${studentId}`)

// 动态画像评估（评估Agent）
export const evaluateProfile = (studentId) =>
  api.post('/qa/evaluate', { student_id: studentId })

// 评估历史
export const getEvaluationHistory = (studentId) =>
  api.get(`/qa/evaluation/history/${studentId}`)

// 最近一次评估
export const getLatestEvaluation = (studentId) =>
  api.get(`/qa/evaluation/latest/${studentId}`)

export default api
