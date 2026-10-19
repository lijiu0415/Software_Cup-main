<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({ userId: { type: String, required: true } })
const questions = [
  { id: 'goal', text: '你本次学习最主要的目标是什么？', options: ['建立基础认知', '完成课程或备考', '解决实际问题', '提升项目与实践能力', '探索个人兴趣'] },
  { id: 'foundation', text: '你对所选科目的基础掌握情况如何？', options: ['零基础', '了解少量概念', '学过基础课程', '能独立完成基础任务', '有相关项目经验'] },
  { id: 'format', text: '你更愿意使用哪些学习资料？', multiple: true, options: ['图文讲解', '视频演示', '具体案例', '交互练习', '项目实战'] },
  { id: 'duration', text: '你通常希望每次学习持续多久？', options: ['15 分钟以内', '15–30 分钟', '30–60 分钟', '60 分钟以上', '根据内容灵活安排'] },
  { id: 'difficulty', text: '学习时你最希望获得哪些方面的帮助？', multiple: true, options: ['理解抽象概念', '补充前置知识', '将知识应用到实践', '保持专注与学习动力', '梳理重点与复习'] },
  { id: 'feedback', text: '遇到难题时，你更希望获得怎样的引导？', options: ['先给少量提示，自己尝试', '分步骤讲解思路', '展示完整示例后再练习', '先复习相关基础', '通过小测发现薄弱点'] },
]
const answers = ref({})
const status = ref('')
const storageKey = computed(() => `ssvep:supplemental-profile:${props.userId}`)
const completed = computed(() => questions.filter(q => answers.value[q.id]?.length).length)

watch(storageKey, () => {
  answers.value = {}
  status.value = ''
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey.value) || '{}')
    for (const q of questions) {
      const values = Array.isArray(saved?.[q.id]) ? saved[q.id] : []
      answers.value[q.id] = values.filter(value => q.options.includes(value)).slice(0, q.multiple ? q.options.length : 1)
    }
  } catch {
    status.value = '暂时无法读取本机记录，仍可选择答案。'
  }
}, { immediate: true })

function select(q, option) {
  const selected = answers.value[q.id] || []
  answers.value[q.id] = q.multiple
    ? (selected.includes(option) ? selected.filter(value => value !== option) : [...selected, option])
    : (selected.includes(option) ? [] : [option])
  try {
    localStorage.setItem(storageKey.value, JSON.stringify(answers.value))
    status.value = '已自动保存到本机浏览器，可随时修改。'
  } catch {
    status.value = '浏览器暂时无法保存，当前选择仅在本次页面中保留。'
  }
}
</script>

<template>
  <details class="supplemental-profile" open>
    <summary>补充学习画像（选填，已答 {{ completed }}/{{ questions.length }}）</summary>
    <p class="intro">选择符合自己的选项，帮助补充学习偏好；所有问题均可跳过，再次点击可取消选择。答案仅保存在本机浏览器，暂不参与学习路径生成。</p>
    <fieldset v-for="(q, index) in questions" :key="q.id">
      <legend>{{ index + 1 }}. {{ q.text }}（{{ q.multiple ? '可多选' : '单选' }}）</legend>
      <div class="choices">
        <label v-for="option in q.options" :key="option" :class="{ selected: answers[q.id]?.includes(option) }">
          <input type="checkbox" :checked="answers[q.id]?.includes(option) || false" @change="select(q, option)">
          {{ option }}
        </label>
      </div>
    </fieldset>
    <p class="save-status" role="status">{{ status }}</p>
  </details>
</template>

<style scoped>
.supplemental-profile { margin-top: 20px; padding: 24px; background: #171c23; border: 1px solid #232b34; border-radius: 12px; }
summary { cursor: pointer; font-size: 18px; font-weight: 600; }
.intro { margin: 14px 0 20px; color: #9aa4ad; line-height: 1.7; font-size: 14px; }
fieldset { min-width: 0; border: 0; margin: 20px 0; }
legend { padding: 0; color: #cbd3da; line-height: 1.6; }
.choices { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
label { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: #1f2832; border: 1px solid #2f3a46; border-radius: 8px; cursor: pointer; }
label.selected { border-color: #7dd3fc; background: #1a3345; }
label:focus-within { outline: 2px solid #7dd3fc; outline-offset: 2px; }
input { accent-color: #38bdf8; }
.save-status { color: #7dd3fc; font-size: 14px; min-height: 20px; }
</style>
