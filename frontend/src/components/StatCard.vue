<template>
  <div class="stat-card">
    <div class="stat-icon" :style="{ background: iconBg }">{{ icon }}</div>
    <div class="stat-content">
      <p class="stat-value">{{ value }}</p>
      <p class="stat-label">{{ label }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: string
  iconBg?: string
  value: string | number
  label: string
}>()
</script>

<style scoped>
.stat-card {
  background: #F8F9FC;
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--app-primary-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 15px;
  font-weight: 700;
  color: #1E1E2D;
  line-height: 1.2;
}

.stat-label {
  font-size: 10px;
  color: #9CA3C4;
  line-height: 1.3;
}
</style>
