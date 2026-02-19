<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";
import { useTracesStore } from "../stores/traces";
import type { ContentItem, Job, OtlpRecord, OtlpSpan, OtlpAnyValue, FlatSpan } from "../types";

const props = defineProps<{
  content: ContentItem;
  job: Job;
}>();

const tracesStore = useTracesStore();

onMounted(() => {
  tracesStore.fetchTraces(props.content.guid, props.job.key);
});

interface TraceGroup {
  traceId: string;
  label: string;
  startNs: bigint;
  startMs: number;
  totalDurationMs: number;
  hasError: boolean;
  spanCount: number;
  spans: FlatSpan[];
}

function buildTraceGroup(traceId: string, spans: OtlpSpan[]): TraceGroup {
  const spanStart = new Map<OtlpSpan, bigint>();
  const spanEnd = new Map<OtlpSpan, bigint | null>();
  for (const s of spans) {
    spanStart.set(s, BigInt(s.startTimeUnixNano ?? "0"));
    spanEnd.set(s, s.endTimeUnixNano != null ? BigInt(s.endTimeUnixNano) : null);
  }

  const byId = new Map<string, OtlpSpan>();
  for (const s of spans) {
    if (s.spanId) byId.set(s.spanId, s);
  }
  const childrenByParent = new Map<string, OtlpSpan[]>();
  for (const s of spans) {
    const pid = s.parentSpanId;
    if (pid && byId.has(pid)) {
      const arr = childrenByParent.get(pid);
      if (arr) arr.push(s);
      else childrenByParent.set(pid, [s]);
    }
  }

  const cmpByStart = (a: OtlpSpan, b: OtlpSpan) =>
    spanStart.get(a)! < spanStart.get(b)! ? -1 : 1;

  for (const children of childrenByParent.values()) {
    children.sort(cmpByStart);
  }

  let traceStartNs = BigInt("9".repeat(20));
  let traceEndNs = 0n;
  for (const s of spans) {
    const t0 = spanStart.get(s)!;
    const t1 = spanEnd.get(s) ?? t0;
    if (t0 < traceStartNs) traceStartNs = t0;
    if (t1 > traceEndNs) traceEndNs = t1;
  }
  const durationNs = traceEndNs - traceStartNs || 1n;

  const flat: FlatSpan[] = [];

  const visit = (s: OtlpSpan, depth: number) => {
    const sNs = spanStart.get(s)!;
    const eNs = spanEnd.get(s) ?? null;
    const durationMs = eNs != null ? Number(eNs - sNs) / 1_000_000 : null;
    const offsetPct = Number((sNs - traceStartNs) * 10000n / durationNs) / 100;
    const widthPct = eNs != null ? Number((eNs - sNs) * 10000n / durationNs) / 100 : 0;

    const exceptionEvent = s.events?.find(e => e.name === "exception") ?? null;
    const exAttr = (key: string) => {
      const a = exceptionEvent?.attributes?.find(a => a.key === key);
      return a ? otlpValue(a.value) : undefined;
    };

    flat.push({
      name: s.name,
      spanId: s.spanId ?? `anon-${flat.length}`,
      parentSpanId: s.parentSpanId ?? null,
      startNs: sNs,
      durationMs,
      depth,
      offsetPct,
      widthPct,
      hasError: s.status?.code === 2,
      attributes: s.attributes ?? [],
      statusMessage: s.status?.message ?? null,
      exception: exceptionEvent
        ? { type: exAttr("exception.type"), message: exAttr("exception.message"), stacktrace: exAttr("exception.stacktrace") }
        : null,
    });

    for (const child of childrenByParent.get(s.spanId ?? "") ?? []) {
      visit(child, depth + 1);
    }
  };

  const roots = spans
    .filter(s => !s.parentSpanId || !byId.has(s.parentSpanId))
    .sort(cmpByStart);
  for (const root of roots) visit(root, 0);

  return {
    traceId,
    label: roots[0]?.name ?? "Trace",
    startNs: traceStartNs,
    startMs: Number(traceStartNs / 1_000_000n),
    totalDurationMs: Number(traceEndNs - traceStartNs) / 1_000_000,
    hasError: flat.some(s => s.hasError),
    spanCount: flat.length,
    spans: flat,
  };
}

const traceGroups = computed((): TraceGroup[] => {
  const records = tracesStore.traceData as OtlpRecord[] | null;
  if (!records) return [];

  const rawSpans: OtlpSpan[] = records
    .flatMap(r => r.resourceSpans ?? [])
    .flatMap(rs => rs.scopeSpans ?? [])
    .flatMap(ss => ss.spans ?? []);

  if (rawSpans.length === 0) return [];

  const byTrace = new Map<string, OtlpSpan[]>();
  for (const s of rawSpans) {
    const tid = s.traceId ?? "unknown";
    const group = byTrace.get(tid);
    if (group) group.push(s);
    else byTrace.set(tid, [s]);
  }

  return Array.from(byTrace.entries())
    .map(([tid, spans]) => buildTraceGroup(tid, spans))
    .sort((a, b) => (a.startNs > b.startNs ? -1 : 1));
});

const maxTraceDurationMs = computed(() =>
  Math.max(1, ...traceGroups.value.map(g => g.totalDurationMs))
);

function otlpValue(v: OtlpAnyValue): string {
  if (v.stringValue != null) return v.stringValue;
  if (v.intValue    != null) return v.intValue;
  if (v.floatValue  != null) return String(v.floatValue);
  if (v.boolValue   != null) return String(v.boolValue);
  if (v.arrayValue  != null) return JSON.stringify(v.arrayValue.values ?? []);
  if (v.kvlistValue != null) return JSON.stringify(v.kvlistValue.values ?? []);
  return "";
}

function formatTime(ms: number): string {
  return new Date(ms).toLocaleString();
}

function formatDuration(ms: number): string {
  if (ms >= 1000) return (ms / 1000).toFixed(2) + " s";
  return ms.toFixed(1) + " ms";
}

function timeAgo(isoString: string): string {
  const secs = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const STATUS_LABEL: Record<number, string> = { 0: "Active", 1: "Finished", 2: "Finalized" };
const STATUS_COLOR: Record<number, string> = {
  0: "text-green-600",
  1: "text-gray-400",
  2: "text-gray-400",
};

// ── Sort state ────────────────────────────────────────────────────────────────

type SortKey = 'startMs' | 'totalDurationMs' | 'spanCount' | 'label';
const sortKey = ref<SortKey>('startMs');
const sortDir = ref<'asc' | 'desc'>('desc');

function setSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortKey.value = key;
    sortDir.value = key === 'startMs' ? 'desc' : 'desc';
  }
}

// ── Facet filter state ────────────────────────────────────────────────────────

const activeFilters = ref<Array<{ key: string; value: string }>>([]);

type DropdownStep = 'closed' | 'pick-key' | 'pick-value';
const dropdownStep = ref<DropdownStep>('closed');
const pendingKey = ref<string | null>(null);

// ── Facet computed ────────────────────────────────────────────────────────────

const allFacets = computed((): Map<string, Map<string, number>> => {
  const facets = new Map<string, Map<string, number>>();
  for (const group of traceGroups.value) {
    for (const span of group.spans) {
      for (const attr of span.attributes) {
        const val = otlpValue(attr.value);
        if (!facets.has(attr.key)) facets.set(attr.key, new Map());
        const m = facets.get(attr.key)!;
        m.set(val, (m.get(val) ?? 0) + 1);
      }
    }
  }
  return facets;
});

const sortedFacets = computed(() =>
  [...allFacets.value.entries()]
    .map(([key, m]) => ({ key, total: [...m.values()].reduce((s, c) => s + c, 0) }))
    .sort((a, b) => b.total - a.total)
);

const sortedValues = computed(() => {
  if (!pendingKey.value) return [];
  const m = allFacets.value.get(pendingKey.value);
  return m ? [...m.entries()].sort((a, b) => b[1] - a[1]) : [];
});

const activeFilterMap = computed((): Map<string, Set<string>> => {
  const m = new Map<string, Set<string>>();
  for (const f of activeFilters.value) {
    const s = m.get(f.key);
    if (s) s.add(f.value);
    else m.set(f.key, new Set([f.value]));
  }
  return m;
});

const pendingKeyActiveValues = computed((): Set<string> => {
  if (!pendingKey.value) return new Set();
  const key = pendingKey.value;
  return new Set(activeFilters.value.filter(f => f.key === key).map(f => f.value));
});

function spanMatchesFilters(span: FlatSpan, filterMap: Map<string, Set<string>>): boolean {
  for (const [key, allowed] of filterMap) {
    if (!span.attributes.some(a => a.key === key && allowed.has(otlpValue(a.value)))) return false;
  }
  return true;
}

const filteredTraceGroups = computed((): TraceGroup[] => {
  if (activeFilters.value.length === 0) return traceGroups.value;
  const filterMap = activeFilterMap.value;
  return traceGroups.value
    .map(g => ({ ...g, spans: g.spans.filter(span => spanMatchesFilters(span, filterMap)) }))
    .filter(g => g.spans.length > 0);
});

const sortedFilteredTraceGroups = computed((): TraceGroup[] => {
  const groups = [...filteredTraceGroups.value];
  const dir = sortDir.value === 'asc' ? 1 : -1;
  groups.sort((a, b) => {
    const ak = a[sortKey.value];
    const bk = b[sortKey.value];
    if (typeof ak === 'string' && typeof bk === 'string')
      return ak.localeCompare(bk) * dir;
    return ((ak as number) - (bk as number)) * dir;
  });
  return groups;
});

// ── Facet functions ───────────────────────────────────────────────────────────

function addFilter(key: string, value: string) {
  if (!activeFilters.value.some(f => f.key === key && f.value === value))
    activeFilters.value = [...activeFilters.value, { key, value }];
}

function removeFilter(key: string, value: string) {
  activeFilters.value = activeFilters.value.filter(f => !(f.key === key && f.value === value));
}

function openKeyPicker() { dropdownStep.value = 'pick-key'; }
function selectKey(key: string) { pendingKey.value = key; dropdownStep.value = 'pick-value'; }
function selectValue(value: string) {
  if (pendingKey.value) addFilter(pendingKey.value, value);
  dropdownStep.value = 'closed'; pendingKey.value = null;
}
function closeDropdown() { dropdownStep.value = 'closed'; pendingKey.value = null; }
</script>

<template>
  <div>
    <div class="mb-4">
      <h2 class="text-lg font-semibold text-gray-800">{{ content.title || content.name }}</h2>
      <div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 text-sm text-gray-500">
        <span class="font-mono text-xs text-gray-400">{{ job.key }}</span>
        <span>started {{ timeAgo(job.start_time) }}</span>
        <span :class="STATUS_COLOR[job.status]">{{ STATUS_LABEL[job.status] }}</span>
      </div>
    </div>

    <LoadingSpinner v-if="tracesStore.isLoading" message="Loading..." class="mt-16" />

    <div v-else-if="tracesStore.error" class="text-red-600 text-sm">
      {{ tracesStore.error }}
    </div>

    <div v-else-if="traceGroups.length">
      <!-- Toolbar -->
      <div class="flex items-center justify-between mb-3">
        <p class="text-xs text-gray-400">
          {{ filteredTraceGroups.length }}<template v-if="activeFilters.length"> / {{ traceGroups.length }}</template> traces
        </p>
      </div>

      <!-- Filter bar -->
      <div v-if="allFacets.size > 0" class="mb-3">
        <div class="flex flex-wrap items-center gap-1.5">
          <span
            v-for="f in activeFilters"
            :key="`${f.key}:${f.value}`"
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 border border-blue-200 text-xs text-blue-800 font-mono"
          >
            {{ f.key }}: {{ f.value }}
            <button class="ml-0.5 text-blue-400 hover:text-blue-700 leading-none"
                    @click="removeFilter(f.key, f.value)" title="Remove filter">×</button>
          </span>

          <div class="relative z-10">
            <div v-if="dropdownStep !== 'closed'" class="fixed inset-0 z-0" @click="closeDropdown" />

            <button
              class="relative z-10 inline-flex items-center gap-1 px-2 py-0.5 rounded border border-gray-200 text-xs text-gray-600 hover:bg-gray-50"
              @click="openKeyPicker"
            >+ Add filter ▾</button>

            <div v-if="dropdownStep === 'pick-key'"
                 class="absolute z-10 left-0 mt-1 w-64 bg-white border border-gray-200 rounded shadow-lg overflow-hidden">
              <ul class="max-h-56 overflow-y-auto">
                <li v-for="facet in sortedFacets" :key="facet.key"
                    class="flex items-center justify-between px-3 py-1.5 text-xs cursor-pointer hover:bg-gray-50"
                    @click.stop="selectKey(facet.key)">
                  <span class="font-mono text-gray-700 truncate">{{ facet.key }}</span>
                  <span class="ml-2 shrink-0 text-gray-400">{{ facet.total }} spans</span>
                </li>
              </ul>
            </div>

            <div v-if="dropdownStep === 'pick-value'"
                 class="absolute z-10 left-0 mt-1 w-64 bg-white border border-gray-200 rounded shadow-lg overflow-hidden">
              <div class="flex items-center gap-1.5 px-3 py-1.5 border-b border-gray-100 text-xs text-gray-600 cursor-pointer hover:bg-gray-50"
                   @click.stop="dropdownStep = 'pick-key'">
                <span>←</span>
                <span class="font-mono font-medium truncate">{{ pendingKey }}</span>
              </div>
              <ul class="max-h-52 overflow-y-auto">
                <li v-for="[val, count] in sortedValues" :key="val"
                    class="flex items-center justify-between px-3 py-1.5 text-xs cursor-pointer hover:bg-gray-50"
                    :class="pendingKeyActiveValues.has(val) ? 'text-gray-400' : 'text-gray-700'"
                    @click.stop="selectValue(val)">
                  <span class="font-mono truncate">
                    <template v-if="pendingKeyActiveValues.has(val)">✓ </template>{{ val }}
                  </span>
                  <span class="ml-2 shrink-0 text-gray-400">{{ count }} spans</span>
                </li>
              </ul>
            </div>
          </div>

          <button v-if="activeFilters.length"
                  class="px-2 py-0.5 rounded text-xs text-gray-400 hover:text-gray-600"
                  @click="activeFilters = []">
            Clear all
          </button>
        </div>
      </div>

      <!-- Table -->
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="border-b border-gray-200">
            <th class="text-left pb-2 pr-4 text-xs font-medium text-gray-500 cursor-pointer select-none hover:text-gray-700 w-64"
                @click="setSort('label')">
              Name
              <span v-if="sortKey === 'label'" class="ml-0.5 text-gray-400">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="text-left pb-2 pr-4 text-xs font-medium text-gray-500 cursor-pointer select-none hover:text-gray-700 w-40"
                @click="setSort('startMs')">
              Time
              <span v-if="sortKey === 'startMs'" class="ml-0.5 text-gray-400">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="text-left pb-2 pr-4 text-xs font-medium text-gray-500 cursor-pointer select-none hover:text-gray-700"
                @click="setSort('totalDurationMs')">
              Duration
              <span v-if="sortKey === 'totalDurationMs'" class="ml-0.5 text-gray-400">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="text-right pb-2 text-xs font-medium text-gray-500 cursor-pointer select-none hover:text-gray-700 w-16"
                @click="setSort('spanCount')">
              Spans
              <span v-if="sortKey === 'spanCount'" class="ml-0.5 text-gray-400">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="group in sortedFilteredTraceGroups"
            :key="group.traceId"
            class="border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors"
            @click="tracesStore.selectedTraceId = group.traceId"
          >
            <!-- Name -->
            <td class="py-2 pr-4">
              <div class="flex items-center gap-1.5 min-w-0">
                <span v-if="group.hasError" class="shrink-0 text-red-500 text-xs" title="One or more spans errored">●</span>
                <span class="font-medium text-gray-800 truncate" :title="group.label">{{ group.label }}</span>
              </div>
            </td>
            <!-- Time -->
            <td class="py-2 pr-4 text-xs text-gray-500 whitespace-nowrap font-mono">
              {{ formatTime(group.startMs) }}
            </td>
            <!-- Duration bar + text -->
            <td class="py-2 pr-4">
              <div class="flex items-center gap-2">
                <div class="relative flex-1 h-3 bg-gray-100 rounded overflow-hidden">
                  <div class="absolute inset-y-0 left-0 bg-blue-300 rounded"
                       :style="{ width: `${(group.totalDurationMs / maxTraceDurationMs) * 100}%` }">
                  </div>
                </div>
                <span class="text-xs text-gray-600 font-mono whitespace-nowrap w-16 text-right">
                  {{ formatDuration(group.totalDurationMs) }}
                </span>
              </div>
            </td>
            <!-- Span count -->
            <td class="py-2 text-right text-xs text-gray-500 font-mono">
              {{ group.spanCount }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="text-gray-500 text-sm">No trace data available.</div>
  </div>
</template>
