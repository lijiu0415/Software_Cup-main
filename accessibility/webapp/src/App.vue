<script setup>
import { ref, computed } from 'vue'
import { useSSVEPBridge, RESULT_MAP } from './bridge/useSSVEPBridge'
import { dbGetProfileQuestions, dbGetQuizQuestion, dbSaveProfileAnswer, dbSubmitQuizAnswer } from './api/db'
import { agentGetLearningPath } from './api/agent'
import ConnectionStatus from './components/ConnectionStatus.vue'
import ProgressBar from './components/ProgressBar.vue'
import LoginPage from './pages/LoginPage.vue'
import SubjectPage from './pages/SubjectPage.vue'
import ProfilePage from './pages/ProfilePage.vue'
import LearningPage from './pages/LearningPage.vue'
import QuizPage from './pages/QuizPage.vue'
import DonePage from './pages/DonePage.vue'
import SupplementalProfile from './components/SupplementalProfile.vue'

const { connected, state, ctx, send, onResult } = useSSVEPBridge()

const feedback = ref(null)   // 最近一次结果的反馈文案

// 学习路径：画像 6 题完成后由网页（agent）生成
const learningPath = computed(() => {
  const pa = ctx.value?.profile_answers
  return pa && pa.length >= 6 ? agentGetLearningPath(pa) : []
})

// 收到结果：网页负责业务映射 + 记录（Mock）
onResult((msg) => {
  const r = msg.result
  const c = ctx.value || {}
  if (msg.state === 'profile_ssvep') {
    const score = RESULT_MAP.profile_ssvep(r)
    const q = dbGetProfileQuestions()[c.profile_index ?? 0]
    if (q && c.user_id) dbSaveProfileAnswer(c.user_id, q.id, score)
    feedback.value = `画像打分：${score} 分`
  } else if (msg.state === 'quiz_ssvep') {
    const answer = RESULT_MAP.quiz_ssvep(r)
    const qs = dbGetQuizQuestion(c.subject, learningPath.value, c.learning_step_index ?? 0)
    const q = qs[c.quiz_index ?? 0]
    if (q && c.user_id) dbSubmitQuizAnswer(c.user_id, q.id, answer)
    feedback.value = `做题答案：${answer}`
  } else if (msg.state === 'subject_ssvep') {
    feedback.value = `选择科目：${RESULT_MAP.subject_ssvep(r)}`
  } else if (msg.state === 'login_ssvep') {
    feedback.value = RESULT_MAP.login_ssvep(r)
  }
})

const page = computed(() => {
  const s = state.value
  if (!s) return 'connecting'
  if (s.startsWith('login')) return 'login'
  if (s.startsWith('subject')) return 'subject'
  if (s.startsWith('profile')) return 'profile'
  if (s.startsWith('learning')) return 'learning'
  if (s.startsWith('quiz')) return 'quiz'
  if (s === 'done') return 'done'
  return 'connecting'
})

function restart() { send('restart') }
</script>

<template>
  <div class="app">
    <header>
      <h1>SSVEP 学习系统</h1>
      <ConnectionStatus :connected="connected" />
      <button @click="restart">重新开始</button>
    </header>

    <ProgressBar v-if="ctx" :ctx="ctx" />
    <div v-if="feedback" class="feedback">{{ feedback }}</div>

    <main>
      <LoginPage v-if="page === 'login'" :state="state" :ctx="ctx" />
      <SubjectPage v-else-if="page === 'subject'" :state="state" :ctx="ctx" />
      <ProfilePage v-else-if="page === 'profile'" :state="state" :ctx="ctx" />
      <LearningPage v-else-if="page === 'learning'" :state="state" :ctx="ctx" :learningPath="learningPath" />
      <QuizPage v-else-if="page === 'quiz'" :state="state" :ctx="ctx" :learningPath="learningPath" />
      <DonePage v-else-if="page === 'done'" />
      <div v-else class="connecting">
        <p v-if="connected">已连接，等待开始…</p>
        <p v-else>未连接：请先运行 python run.py（ws://127.0.0.1:8765）</p>
      </div>
      <SupplementalProfile
        v-if="ctx?.user_id && !['login', 'connecting'].includes(page)"
        :key="ctx.user_id"
        :user-id="ctx.user_id"
      />
    </main>
  </div>
</template>
