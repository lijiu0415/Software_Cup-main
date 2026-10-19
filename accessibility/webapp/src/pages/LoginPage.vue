<script setup>
defineProps(['state', 'ctx'])
</script>

<template>
  <div class="page">
    <h2>登录</h2>
    <p v-if="state === 'login_unavailable'" class="warn">登录暂未开放，请使用游客登录</p>
    <p v-if="state === 'login_ssvep'">请注视频闪窗口（pygame），选择：</p>
    <div class="options">
      <div class="option"><span class="tag">块0</span> 游客登录</div>
      <div class="option"><span class="tag">块1</span> 登录</div>
    </div>
  </div>
</template>
