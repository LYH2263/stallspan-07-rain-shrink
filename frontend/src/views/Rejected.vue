<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

const rows = ref<any[]>([])
const data = ref<any>(null)

const isRain = computed(() => Boolean(data.value?.day?.rainy))
const coefficient = computed<number | null>(() => {
  const c = data.value?.day?.width_coefficient
  return c === null || c === undefined ? null : Number(c)
})
const registeredWidth = computed(() => data.value?.segment?.width_m ?? null)
// Same single effective width as the engine and map.
const effWidth = computed(() => {
  if (!data.value) return null
  return typeof data.value.effective_width_m === 'number'
    ? data.value.effective_width_m : Number(data.value.segment.width_m)
})

onMounted(async () => {
  // /latest is fingerprint-gated server-side: after a day change this
  // appends a run at the NEW effective width, never serving stale rejected.
  const d = await api('/allocate/latest?segment_id=1')
  data.value = d
  rows.value = d.rejected || []
})
</script>
<template>
  <h1>放不下</h1>
  <p class="sub">无法在连续空档内安置且不跨越挡柱的摊位</p>
  <p v-if="data">
    <span :class="['badge', isRain ? 'badge-warn' : 'badge-ok']">
      <template v-if="isRain">雨天 系数 {{ coefficient }} · 登记 {{ registeredWidth }} → 有效 {{ effWidth }} m</template>
      <template v-else>晴天 · 有效宽 {{ effWidth }} m</template>
    </span>
    <span class="muted ss-rejected-meta">放不下集合与主图、切空引擎使用同一有效宽度（运行 #{{ data.id }}）</span>
  </p>
  <div class="card">
    <table>
      <thead><tr><th>摊主</th><th>需求宽度</th><th>原因</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.vendor_id">
          <td>{{ r.vendor_name }}</td>
          <td>{{ r.width_m }}</td>
          <td>{{ r.reason }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">全部放下</p>
  </div>
</template>
