<script setup>
defineProps(['connected'])
</script>

<template>
  <span class="status" :class="connected ? 'ok' : 'down'">
    {{ connected ? '已连接' : '未连接' }}
  </span>
</template>
