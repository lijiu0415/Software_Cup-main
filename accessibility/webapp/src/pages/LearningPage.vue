<script setup>
import { computed } from 'vue'
import { dbGetLearningContent } from '../api/db'

const props = defineProps(['state', 'ctx', 'learningPath'])

const content = computed(() =>
  dbGetLearningContent(props.ctx?.subject, props.learningPath, props.ctx?.learning_step_index ?? 0)
)
</script>

<template>
  <div class="page">
    <h2>学习内容（第 {{ (ctx?.learning_step_index ?? 0) + 1 }} 步）</h2>
    <p class="content">{{ content }}</p>
  </div>
</template>
