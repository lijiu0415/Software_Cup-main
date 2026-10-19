<script setup>
import { computed } from 'vue'
import { dbGetQuizQuestion } from '../api/db'

const props = defineProps(['state', 'ctx', 'learningPath'])

const qs = computed(() =>
  dbGetQuizQuestion(props.ctx?.subject, props.learningPath, props.ctx?.learning_step_index ?? 0)
)
const q = computed(() => qs.value[props.ctx?.quiz_index ?? 0])
</script>

<template>
  <div class="page">
    <h2>做题提升问题</h2>
    <p v-if="q" class="question">{{ q.text }}</p>
    <p v-if="state === 'quiz_ssvep'">请注视频闪窗口（pygame）选择：</p>
    <div v-if="state === 'quiz_ssvep'" class="options">
      <div v-for="(opt, i) in ['A', 'B', 'C', 'D']" :key="i" class="option">
        <span class="tag">块{{ i }}</span> {{ opt }}
      </div>
    </div>
  </div>
</template>
