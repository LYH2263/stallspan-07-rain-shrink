<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

const SEGMENT_ID = 1

const data = ref<any>(null)
const vendors = ref<any[]>([])
const runs = ref<any[]>([])
const viewingRunId = ref<number | null>(null)
const drawerOpen = ref(false)

const colors = ['#e8a87c','#85dcb8','#e27d60','#c38d9e','#41b3a3','#f4a261','#e76f51']

const registeredWidth = computed(() => data.value?.segment?.width_m ?? 0)
// THE denominator shared with the engine: every cell, gap and the right end
// are scaled against this one effective width.
const effWidth = computed(() => {
  if (!data.value) return 0
  const e = data.value.effective_width_m
  return typeof e === 'number' ? e : Number(data.value.segment.width_m)
})
const isRain = computed(() => Boolean(data.value?.day?.rainy))
const coefficient = computed<number | null>(() => {
  const c = data.value?.day?.width_coefficient
  return c === null || c === undefined ? null : Number(c)
})
const currentRunId = computed(() => runs.value[0]?.id ?? null)
const isHistorical = computed(() =>
  viewingRunId.value !== null && currentRunId.value !== null && viewingRunId.value !== currentRunId.value)

interface BandCell {
  type: 'pillar' | 'stall'
  start: number
  end: number
  label: string
  color?: string
  leftPct: number
  widthPct: number
}

const cells = computed<BandCell[]>(() => {
  if (!data.value) return []
  const W = effWidth.value
  const out: any[] = []
  // Pillars come ONLY from the run payload — the same rectangles the engine
  // used. Voided pillars (mark past the right end) are simply absent.
  if (Array.isArray(data.value.pillar_rects)) {
    for (const p of data.value.pillar_rects) {
      out.push({ type: 'pillar', start: Number(p.start_m), end: Number(p.end_m), label: p.label || '挡柱' })
    }
  } else {
    // Legacy snapshots (built before pillar_rects existed).
    for (const p of data.value.pillars || []) {
      const half = (Number(p.thickness_m) || 0.4) / 2
      out.push({ type: 'pillar', start: Number(p.position_m) - half,
                 end: Number(p.position_m) + half, label: p.label || '挡柱' })
    }
  }
  for (const [i, p] of (data.value.placements || []).entries()) {
    out.push({ type: 'stall', start: Number(p.start_m), end: Number(p.end_m),
               label: p.vendor_name, color: colors[i % colors.length] })
  }
  return out
    .filter((c) => W > 0 && c.end > 0 && c.start < W)
    .map((c) => {
      const start = Math.max(0, c.start)
      const end = Math.min(W, c.end)
      return { ...c, leftPct: (start / W) * 100, widthPct: ((end - start) / W) * 100 }
    })
})

async function loadRuns() {
  runs.value = await api(`/allocate/runs?segment_id=${SEGMENT_ID}`)
}

async function showLatest() {
  data.value = await api(`/allocate/latest?segment_id=${SEGMENT_ID}`)
  viewingRunId.value = data.value.id
  await loadRuns()
}

async function run() {
  // Re-allocation always uses the CURRENT effective width; the server
  // fingerprint gate means /latest can never serve pre-change stale data.
  data.value = await api(`/allocate/run?segment_id=${SEGMENT_ID}`, { method: 'POST' })
  viewingRunId.value = data.value.id
  await loadRuns()
}

async function openRun(id: number) {
  data.value = await api(`/allocate/runs/${id}`)
  viewingRunId.value = id
}

function fmtTime(iso: string): string {
  const d = new Date(iso)
  return isNaN(d.getTime()) ? iso : d.toLocaleString()
}

onMounted(async () => {
  vendors.value = await api('/vendors')
  await showLatest()
})
</script>
<template>
  <div class="ss-street-wrap">
    <h1>街段分配带</h1>
    <p class="sub">沿街一维开间 · 挡柱为竖直阻断 · 底部为摊主排队</p>
    <div class="ss-map-actions">
      <button class="btn" @click="run">重新分配</button>
      <button class="btn btn-ghost" @click="drawerOpen = !drawerOpen">
        运行抽屉（{{ runs.length }}）
      </button>
      <span v-if="isRain" class="badge badge-warn ss-rain-badge">
        雨天 系数 {{ coefficient }} · 登记 {{ registeredWidth }} → 有效 {{ effWidth }} m
      </span>
      <span v-else class="badge badge-ok ss-rain-badge">晴天 · {{ effWidth }} m</span>
    </div>

    <div v-if="isHistorical" class="ss-history-banner">
      历史快照 #{{ data?.id }} · {{ fmtTime(runs.find(r => r.id === viewingRunId)?.created_at || '') }}
      ，按当时有效宽 {{ effWidth }} m 渲染，不会重新计算
      <button class="btn btn-small" @click="showLatest">回到当前</button>
    </div>

    <div class="ss-run-drawer card" v-show="drawerOpen">
      <table>
        <thead>
          <tr><th>运行</th><th>时间</th><th>天气</th><th>登记→有效</th><th>放不下</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="r in runs" :key="r.id"
              :class="{ 'ss-run-current': r.id === currentRunId, 'ss-run-viewing': r.id === viewingRunId }">
            <td>#{{ r.id }}</td>
            <td>{{ fmtTime(r.created_at) }}</td>
            <td>
              <span :class="['badge', r.rainy ? 'badge-warn' : 'badge-ok']">
                {{ r.rainy ? `雨 ${r.width_coefficient ?? ''}` : '晴' }}
              </span>
            </td>
            <td>{{ r.registered_width_m }} → {{ r.effective_width_m }} m</td>
            <td>{{ r.rejected_count }}</td>
            <td>
              <button class="btn btn-small"
                      :disabled="r.id === viewingRunId" @click="openRun(r.id)">查看</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="ss-band-ruler" v-if="data">
      <span>0 m</span>
      <span>{{ data.segment.name }} · 登记 {{ data.segment.width_m }} m</span>
      <span>{{ effWidth }} m</span>
    </div>
    <div class="ss-street-band" v-if="data">
      <div class="ss-street-inner">
        <div
          v-for="(c, i) in cells" :key="i"
          class="ss-band-cell"
          :class="{ 'ss-pillar': c.type === 'pillar' }"
          :style="{ left: c.leftPct + '%', width: c.widthPct + '%',
                    background: c.type === 'pillar' ? undefined : c.color }"
        >{{ c.label }}</div>
        <div v-if="effWidth === 0" class="ss-zero-width">雨天有效宽 0 m，街段不参与分配</div>
      </div>
    </div>
    <div class="ss-vendor-queue">
      <div v-for="v in vendors" :key="v.id" class="ss-vendor-chip">
        <strong>{{ v.name }}</strong>
        <span>需 {{ v.stall_width_m }} m · 优先 {{ v.priority }}</span>
      </div>
    </div>
    <div class="card" v-if="data">
      <table>
        <thead><tr><th>摊主</th><th>起点</th><th>终点</th><th>宽度</th></tr></thead>
        <tbody>
          <tr v-for="p in data.placements" :key="p.vendor_id">
            <td>{{ p.vendor_name }}</td>
            <td>{{ p.start_m }}</td>
            <td>{{ p.end_m }}</td>
            <td>{{ p.width_m }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
