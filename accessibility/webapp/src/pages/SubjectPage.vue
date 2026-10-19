<script setup>
defineProps(['state', 'ctx'])
</script>

<template>
  <div class="page">
    <h2 v-if="state === 'subject_prompt'">请进行想选择的科目</h2>
    <h2 v-else>选择科目</h2>
    <p v-if="state === 'subject_ssvep'">请注视频闪窗口（pygame），选择：</p>
    <div v-if="state === 'subject_ssvep'" class="options">
      <div class="option"><span class="tag">块0</span> 软件安全</div>
      <div class="option"><span class="tag">块1</span> 人工智能导论</div>
    </div>
    <p v-if="ctx?.subject" class="chosen">已选科目：{{ ctx.subject }}</p>
  </div>
</template>
