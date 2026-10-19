// 数据库接口（Mock）。以后接真实后端时，只替换这里的实现，不改函数签名与调用方式。

export const SUBJECTS = ['软件安全', '人工智能导论']

export const PROFILE_QUESTIONS = [
  { id: 'p1', text: '第1题：你对动手实践类学习有多感兴趣？（1~5分）' },
  { id: 'p2', text: '第2题：你对抽象理论类内容有多感兴趣？（1~5分）' },
  { id: 'p3', text: '第3题：你更偏好项目制学习吗？（1~5分）' },
  { id: 'p4', text: '第4题：你对新技术的接受速度？（1~5分）' },
  { id: 'p5', text: '第5题：你偏好的学习节奏？（1~5分）' },
  { id: 'p6', text: '第6题：你希望的学习深度？（1~5分）' },
]

export function dbGetSubjects() {
  return [...SUBJECTS]
}

export function dbGetProfileQuestions() {
  return [...PROFILE_QUESTIONS]
}

export function dbSaveProfileAnswer(userId, questionId, score) {
  console.log(`[db] save_profile_answer user=${userId} q=${questionId} score=${score}`)
  // TODO: 换成真实后端 HTTP 调用
}

export function dbGetLearningContent(subject, learningPath, step) {
  const name = learningPath?.[step] ?? '未知步骤'
  return `【${subject}】学习内容：${name}（Mock 文字板，第 ${step + 1} 步）`
}

export function dbGetQuizQuestion(subject, learningPath, step) {
  const name = learningPath?.[step] ?? '未知步骤'
  return [
    { id: `${subject}_${name}_q1`, text: `【${subject}·${name}】第1题（Mock）：请选择 A/B/C/D`, answer: 'A' },
    { id: `${subject}_${name}_q2`, text: `【${subject}·${name}】第2题（Mock）：请选择 A/B/C/D`, answer: 'B' },
  ]
}

export function dbSubmitQuizAnswer(userId, questionId, answer) {
  console.log(`[db] submit_quiz_answer user=${userId} q=${questionId} answer=${answer}`)
  // TODO: 换成真实后端 HTTP 调用
}
