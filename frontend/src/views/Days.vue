<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

interface DayRow {
  id: number
  name: string
  day: string
  rainy: boolean
  width_coefficient: number | null
}
interface SegmentRow {
  id: number
  market_day_id: number
  name: string
  width_m: number
}

const rows = ref<DayRow[]>([])
const segments = ref<SegmentRow[]>([])
// Per-row editable draft; server state (`rows`) is only replaced after a 200.
const draft = ref<Record<number, { rainy: boolean; width_coefficient: string | null }>>({})
const saving = ref<Record<number, boolean>>({})
const errors = ref<Record<number, string>>({})

function syncDraft(r: DayRow) {
  draft.value[r.id] = {
    rainy: r.rainy,
    width_coefficient: r.width_coefficient === null || r.width_coefficient === undefined
      ? null : String(r.width_coefficient),
  }
}

function daySegments(dayId: number): SegmentRow[] {
  return segments.value.filter((s) => s.market_day_id === dayId)
}

function effHint(r: DayRow): string {
  const d = draft.value[r.id]
  if (!d?.rainy || d.width_coefficient === null || d.width_coefficient.trim() === '') return ''
  const c = Number(d.width_coefficient)
  if (!Number.isFinite(c)) return ''
  return daySegments(r.id).map((s) => `${s.name} ${s.width_m}→${(s.width_m * c).toFixed(2)}m`).join('，')
}

onMounted(async () => {
  const [dayRows, segRows] = await Promise.all([
    api<DayRow[]>('/days'),
    api<SegmentRow[]>('/segments'),
  ])
  rows.value = dayRows
  segments.value = segRows
  dayRows.forEach(syncDraft)
})

function coeffNumber(d: { rainy: boolean; width_coefficient: string | null }): number | null {
  if (!d.rainy) return null
  if (d.width_coefficient === null || d.width_coefficient.trim() === '') return null
  const n = Number(d.width_coefficient)
  return Number.isFinite(n) ? n : NaN
}

async function save(r: DayRow) {
  const d = draft.value[r.id]
  errors.value[r.id] = ''
  saving.value[r.id] = true
  try {
    const updated = await api<DayRow>(`/days/${r.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ rainy: d.rainy, width_coefficient: coeffNumber(d) }),
    })
    const idx = rows.value.findIndex((x) => x.id === r.id)
    if (idx >= 0) rows.value[idx] = updated
    syncDraft(updated)
  } catch (e: any) {
    // Rejected save: server row is unchanged — revert the form so the UI
    // cannot show a half-shortened state.
    errors.value[r.id] = e?.message || '保存失败'
    syncDraft(r)
  } finally {
    saving.value[r.id] = false
  }
}
</script>
<template>
  <h1>集日</h1>
  <p class="sub">开市日程 · 雨天按登记宽度 × 系数作为有效宽度，引擎、主图、放不下共用同一宽度</p>
  <div class="card">
    <table>
      <thead>
        <tr><th>名称</th><th>日期</th><th>雨天</th><th>宽度系数（0–1）</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.name }}</td>
          <td>{{ r.day }}</td>
          <td>
            <label class="ss-rain-toggle">
              <input
                type="checkbox"
                :checked="draft[r.id]?.rainy"
                @change="(e) => { draft[r.id].rainy = (e.target as HTMLInputElement).checked; errors[r.id] = '' }"
              />
              <span :class="['badge', draft[r.id]?.rainy ? 'badge-warn' : 'badge-ok']">
                {{ draft[r.id]?.rainy ? '雨天' : '晴天' }}
              </span>
            </label>
          </td>
          <td>
            <input
              class="ss-coeff-input"
              type="number"
              min="0"
              max="1"
              step="0.05"
              :disabled="!draft[r.id]?.rainy"
              :value="draft[r.id]?.rainy ? draft[r.id]?.width_coefficient ?? '' : ''"
              @input="(e) => { draft[r.id].width_coefficient = (e.target as HTMLInputElement).value; errors[r.id] = '' }"
            />
            <span class="muted ss-eff-hint" v-if="effHint(r)">{{ effHint(r) }}</span>
          </td>
          <td>
            <button class="btn" :disabled="saving[r.id]" @click="save(r)">
              {{ saving[r.id] ? '保存中…' : '保存' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p
      v-for="r in rows"
      v-show="errors[r.id]"
      :key="'err-' + r.id"
      class="ss-error-banner"
    >{{ r.name }}：{{ errors[r.id] }}</p>
  </div>
</template>
