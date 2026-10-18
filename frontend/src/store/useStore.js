import { create } from 'zustand'

const INITIAL_AGENT_STATUS = {
  '教案': 'idle',
  '习题': 'idle',
  '代码示例': 'idle',
  '思维导图': 'idle',
  '拓展阅读': 'idle',
  '视频推荐': 'idle',
}

// 全局状态管理
const useStore = create((set, get) => ({
  // ============ AI 智育万象（新） ============
  user: { name: '' },
  course: '人工智能导论',
  progress: 0,          // 完成度百分比
  gapCount: 0,          // 开放缺口数
  dueReviewCount: 0,    // 待复习知识点数（遗忘曲线，侧栏角标用）
  currentStep: 0,        // 0: 问卷  1: 规划  2: 学习
  agentStatus: { ...INITIAL_AGENT_STATUS },

  updateProgress: (delta) =>
    set((s) => ({ progress: Math.max(0, Math.min(100, s.progress + delta)) })),
  updateGapCount: (delta) =>
    set((s) => ({ gapCount: Math.max(0, s.gapCount + delta) })),
  setProgress: (p) => set({ progress: p }),
  setGapCount: (n) => set({ gapCount: n }),
  setDueReviewCount: (n) => set({ dueReviewCount: n }),
  setCurrentStep: (step) => set({ currentStep: step }),
  setAgentStatus: (id, status) =>
    set((s) => ({ agentStatus: { ...s.agentStatus, [id]: status } })),
  resetAgentStatus: () => set({ agentStatus: { ...INITIAL_AGENT_STATUS } }),

  // 跨页跳转目标知识点（学习路径/漏洞看板 → 知识点学习）
  pendingKpId: null,
  setPendingKpId: (id) => set({ pendingKpId: id }),

  // 跨页跳转目标章节（知识点学习 → 章节测试）
  pendingChapterId: null,
  setPendingChapterId: (id) => set({ pendingChapterId: id }),

  // 问卷完成状态（问卷为必经第0步，作为画像的主要来源）
  questionnaire_complete: JSON.parse(localStorage.getItem('questionnaire_complete') || 'false'),
  setQuestionnaireComplete: (v) => {
    localStorage.setItem('questionnaire_complete', JSON.stringify(v))
    set({ questionnaire_complete: v })
  },

  // ============ 原有字段（兼容登录 / 切换账号 / 旧逻辑） ============
  token: localStorage.getItem('token') || '',
  setToken: (t) => {
    localStorage.setItem('token', t)
    set({ token: t })
  },
  clearToken: () => {
    localStorage.removeItem('token')
    set({ token: '' })
  },
  studentId: localStorage.getItem('studentId') || '',
  studentName: localStorage.getItem('studentName') || '',
  studentProfile: JSON.parse(localStorage.getItem('studentProfile') || '{}'),
  registerDate: localStorage.getItem('registerDate') || '',  // 注册日期 YYYY-MM-DD

  setStudentId: (id) => {
    localStorage.setItem('studentId', id)
    set({ studentId: id })
  },
  setStudentName: (name) => {
    localStorage.setItem('studentName', name)
    set({ studentName: name })
  },
  setStudentProfile: (profile) => {
    localStorage.setItem('studentProfile', JSON.stringify(profile))
    set({ studentProfile: profile })
  },
  setRegisterDate: (date) => {
    localStorage.setItem('registerDate', date)
    set({ registerDate: date })
  },

  // 切换学生账号（同时更新总控面板用户名）
  switchStudent: (name) => {
    const studentId = 'student_' + name
    localStorage.setItem('studentId', studentId)
    localStorage.setItem('studentName', name)
    localStorage.setItem('studentProfile', '{}')
    localStorage.setItem('chatHistory', '[]')
    localStorage.setItem('questionnaire_complete', 'false')
    localStorage.removeItem('registerDate')
    set({
      studentId,
      studentName: name,
      studentProfile: {},
      chatHistory: [],
      registerDate: '',
      user: { name },
      questionnaire_complete: false,
    })
  },

  // 对话历史
  chatHistory: JSON.parse(localStorage.getItem('chatHistory') || '[]'),
  addChatMessage: (msg) => {
    set((s) => {
      const newHistory = [...s.chatHistory, msg]
      localStorage.setItem('chatHistory', JSON.stringify(newHistory))
      return { chatHistory: newHistory }
    })
  },
  clearChatHistory: () => {
    localStorage.setItem('chatHistory', '[]')
    set({ chatHistory: [] })
  },

  // 学习路径
  learningPath: [],
  setLearningPath: (path) => set({ learningPath: path }),

  // 当前知识点
  currentKp: null,
  setCurrentKp: (kp) => set({ currentKp: kp }),

  // 资源数据
  resources: {},
  setResources: (res) => set({ resources: res }),

  // Tab 状态（旧版，保留兼容）
  activeTab: 'chat',
  setActiveTab: (tab) => set({ activeTab: tab }),

  // 掌握度数据
  masteryData: {},
  setMasteryData: (data) => set({ masteryData: data }),
  updateMastery: (kpId, mastery) =>
    set((s) => ({ masteryData: { ...s.masteryData, [kpId]: mastery } })),
}))

export default useStore
