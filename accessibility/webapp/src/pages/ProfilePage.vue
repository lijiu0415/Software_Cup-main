<script setup>
import { computed } from 'vue'
import { dbGetProfileQuestions } from '../api/db'

const props = defineProps(['state', 'ctx'])

const q = computed(() => dbGetProfileQuestions()[props.ctx?.profile_index ?? 0])
</script>

<template>
  <div class="page">
    <h2>人物画像问题</h2>
    <p v-if="q" class="question">{{ q.text }}</p>
    <p v-if="state === 'profile_ssvep'">请注视频闪窗口（pygame）打分：</p>
    <div v-if="state === 'profile_ssvep'" class="options">
      <div v-for="i in 5" :key="i" class="option">
        <span class="tag">块{{ i - 1 }}</span> {{ i }}分
      </div>
    </div>
    <p v-if="ctx" class="progress">已答 {{ ctx.profile_answers.length }} / 6</p>
  </div>
</template>
