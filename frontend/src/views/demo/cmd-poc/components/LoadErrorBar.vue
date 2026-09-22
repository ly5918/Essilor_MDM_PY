<template>
  <div v-if="message" class="load-error" role="alert">
    <span class="load-error-ic">!</span>
    <span class="load-error-msg">{{ message }}</span>
    <el-button link type="primary" class="load-error-retry" @click="emit('retry')">重新加载</el-button>
  </div>
</template>

<script setup lang="ts">
/**
 * 请求失败条（列表 / 指标通用）：「拿不到数据」≠「没有数据」。
 *
 * 网关 502、后端重启或断连时必须显性报错并给出重试入口，否则页面上的「暂无数据 / 0」
 * 会被读成业务事实（复测报告 BUG-01：「提交了但列表没有」的观感来源）。
 * 注：模板保持单根节点——项目 check-transition 插件禁止多根。
 */
defineProps<{
  /** 失败原因文案；为空时不渲染（成功态不留痕迹） */
  message?: string;
}>();

const emit = defineEmits<{ (e: 'retry'): void }>();
</script>
