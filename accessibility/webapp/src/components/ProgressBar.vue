<script setup>
defineProps(['ctx'])
</script>

<template>
  <div class="progressbar">
    <span>科目：{{ ctx?.subject || '—' }}</span>
    <span>画像：{{ ctx?.profile_answers?.length ?? 0 }}/6</span>
    <span>学习步骤：{{ (ctx?.learning_step_index ?? 0) + 1 }}/3</span>
    <span>当前题：{{ (ctx?.quiz_index ?? 0) + 1 }}/2</span>
  </div>
</template>
