<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
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
  // Pre-parse all timestamps once — avoids repeated BigInt construction in sort comparators
  const spanStart = new Map<OtlpSpan, bigint>();
  const spanEnd = new Map<OtlpSpan, bigint | null>();
  for (const s of spans) {
    spanStart.set(s, BigInt(s.startTimeUnixNano ?? "0"));
    spanEnd.set(s, s.endTimeUnixNano != null ? BigInt(s.endTimeUnixNano) : null);
  }

  // Build id -> span map, then parent -> children map in O(N) instead of O(N²) per-span filter
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

  // Comparator uses pre-parsed BigInts — no per-comparison allocation
  const cmpByStart = (a: OtlpSpan, b: OtlpSpan) =>
    spanStart.get(a)! < spanStart.get(b)! ? -1 : 1;

  // Pre-sort every children list once
  for (const children of childrenByParent.values()) {
    children.sort(cmpByStart);
  }

  // Find trace time bounds using pre-parsed values
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
    const widthPct = eNs != null
      ? Number((eNs - sNs) * 10000n / durationNs) / 100
      : 0;

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
      selfTimeMs: null, // computed in second pass below
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

  // Second pass: compute self-time (duration minus direct children's durations)
  const flatById = new Map<string, FlatSpan>();
  for (const f of flat) flatById.set(f.spanId, f);
  const childDurationSum = new Map<string, number>();
  for (const f of flat) {
    if (f.parentSpanId && flatById.has(f.parentSpanId) && f.durationMs != null) {
      childDurationSum.set(f.parentSpanId, (childDurationSum.get(f.parentSpanId) ?? 0) + f.durationMs);
    }
  }
  for (const f of flat) {
    if (f.durationMs != null) {
      f.selfTimeMs = f.durationMs - (childDurationSum.get(f.spanId) ?? 0);
    }
  }

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

  const groups = Array.from(byTrace.entries()).map(([tid, spans]) =>
    buildTraceGroup(tid, spans)
  );

  return groups.sort((a, b) => (a.startNs > b.startNs ? -1 : 1));
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

const viewMode = ref<'waterfall' | 'flamegraph' | 'aggregate'>('waterfall');

function maxDepth(group: TraceGroup): number {
  return group.spans.reduce((max, s) => Math.max(max, s.depth), 0);
}

// All traces collapsed by default
const expanded = reactive(new Set<string>());

function toggle(traceId: string) {
  if (expanded.has(traceId)) expanded.delete(traceId);
  else expanded.add(traceId);
}

const allExpanded = computed(() =>
  sortedTraceGroups.value.length > 0 &&
  sortedTraceGroups.value.every(g => expanded.has(g.traceId))
);

function toggleAllTraces() {
  if (allExpanded.value) {
    for (const g of sortedTraceGroups.value) expanded.delete(g.traceId);
  } else {
    for (const g of sortedTraceGroups.value) expanded.add(g.traceId);
  }
}

const expandedSpans = reactive(new Set<string>());

function toggleSpan(spanId: string) {
  if (expandedSpans.has(spanId)) expandedSpans.delete(spanId);
  else expandedSpans.add(spanId);
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

// ── Sort & duration filter state ──────────────────────────────────────────────

const traceSortOrder = ref<'newest' | 'slowest'>('newest');
const minDurationMs = ref<number | null>(null);
const durationThresholds = [10, 50, 100, 500, 1000] as const;

// ── Facet filter state ────────────────────────────────────────────────────────

const activeFilters = ref<Array<{ key: string; value: string }>>([]);

const expandedFacets = reactive(new Set<string>());

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

// Precomputed once per filter change — not once per span
const activeFilterMap = computed((): Map<string, Set<string>> => {
  const m = new Map<string, Set<string>>();
  for (const f of activeFilters.value) {
    const s = m.get(f.key);
    if (s) s.add(f.value);
    else m.set(f.key, new Set([f.value]));
  }
  return m;
});

const hasAnyFilter = computed(() => activeFilters.value.length > 0 || minDurationMs.value != null);

const filteredTraceGroups = computed((): TraceGroup[] => {
  if (!hasAnyFilter.value) return traceGroups.value;
  const filterMap = activeFilterMap.value;
  return traceGroups.value
    .filter(g => g.spans.some(span => spanMatchesFilters(span, filterMap)));
});

const sortedTraceGroups = computed((): TraceGroup[] => {
  const list = [...filteredTraceGroups.value];
  if (traceSortOrder.value === 'slowest') {
    return list.sort((a, b) => b.totalDurationMs - a.totalDurationMs);
  }
  return list.sort((a, b) => (a.startNs > b.startNs ? -1 : 1));
});

const matchingSpanIds = computed((): Set<string> => {
  if (!hasAnyFilter.value) return new Set();
  const filterMap = activeFilterMap.value;
  const ids = new Set<string>();
  for (const g of filteredTraceGroups.value) {
    for (const span of g.spans) {
      if (spanMatchesFilters(span, filterMap)) ids.add(span.spanId);
    }
  }
  return ids;
});

function isSpanDimmed(spanId: string): boolean {
  return hasAnyFilter.value && !matchingSpanIds.value.has(spanId);
}

// ── Facet functions ───────────────────────────────────────────────────────────

function spanMatchesFilters(span: FlatSpan, filterMap: Map<string, Set<string>>): boolean {
  const minDur = minDurationMs.value;
  if (minDur != null && (span.durationMs === null || span.durationMs < minDur)) return false;
  for (const [key, allowed] of filterMap) {
    if (!span.attributes.some(a => a.key === key && allowed.has(otlpValue(a.value)))) return false;
  }
  return true;
}

function addFilter(key: string, value: string) {
  if (!activeFilters.value.some(f => f.key === key && f.value === value))
    activeFilters.value = [...activeFilters.value, { key, value }];
}

function removeFilter(key: string, value: string) {
  activeFilters.value = activeFilters.value.filter(f => !(f.key === key && f.value === value));
}

function toggleFacet(key: string) {
  if (expandedFacets.has(key)) expandedFacets.delete(key);
  else expandedFacets.add(key);
}

function facetValues(key: string): [string, number][] {
  const m = allFacets.value.get(key);
  return m ? [...m.entries()].sort((a, b) => b[1] - a[1]) : [];
}

function activeCountForKey(key: string): number {
  return activeFilters.value.filter(f => f.key === key).length;
}

function clearAllFilters() {
  activeFilters.value = [];
  minDurationMs.value = null;
}

// ── Aggregate view ────────────────────────────────────────────────────────────

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

interface SpanAggregate {
  name: string;
  count: number;
  min: number;
  max: number;
  p50: number;
  p95: number;
  total: number;
  avgSelfTime: number | null;
}

type AggSortKey = 'name' | 'count' | 'p50' | 'p95' | 'max' | 'avgSelfTime';
const aggSortKey = ref<AggSortKey>('p95');
const aggSortAsc = ref(false);

function toggleAggSort(key: AggSortKey) {
  if (aggSortKey.value === key) {
    aggSortAsc.value = !aggSortAsc.value;
  } else {
    aggSortKey.value = key;
    aggSortAsc.value = key === 'name'; // name defaults ascending, numbers descending
  }
}

const spanAggregates = computed((): SpanAggregate[] => {
  const groups = new Map<string, { durations: number[]; selfTimes: number[] }>();
  for (const g of filteredTraceGroups.value) {
    for (const span of g.spans) {
      if (span.durationMs == null) continue;
      let entry = groups.get(span.name);
      if (!entry) {
        entry = { durations: [], selfTimes: [] };
        groups.set(span.name, entry);
      }
      entry.durations.push(span.durationMs);
      if (span.selfTimeMs != null) entry.selfTimes.push(span.selfTimeMs);
    }
  }
  const result: SpanAggregate[] = [];
  for (const [name, { durations, selfTimes }] of groups) {
    durations.sort((a, b) => a - b);
    selfTimes.sort((a, b) => a - b);
    result.push({
      name,
      count: durations.length,
      min: durations[0],
      max: durations[durations.length - 1],
      p50: percentile(durations, 50),
      p95: percentile(durations, 95),
      total: durations.reduce((s, d) => s + d, 0),
      avgSelfTime: selfTimes.length > 0 ? selfTimes.reduce((s, d) => s + d, 0) / selfTimes.length : null,
    });
  }
  const key = aggSortKey.value;
  const dir = aggSortAsc.value ? 1 : -1;
  return result.sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === 'string') return dir * av.localeCompare(bv as string);
    return dir * ((av as number) - (bv as number));
  });
});
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
      <div class="flex gap-6">
        <!-- Sidebar filters -->
        <aside v-if="allFacets.size > 0" class="w-56 shrink-0">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filters</h3>
            <button
              v-if="hasAnyFilter"
              class="text-xs text-blue-600 hover:text-blue-800"
              @click="clearAllFilters"
            >Clear all</button>
          </div>
          <div class="mb-3">
            <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Duration</h4>
            <div class="flex flex-wrap gap-1">
              <button
                class="px-2 py-0.5 rounded-full text-xs transition-colors"
                :class="minDurationMs == null ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
                @click="minDurationMs = null"
              >Any</button>
              <button
                v-for="t in durationThresholds"
                :key="t"
                class="px-2 py-0.5 rounded-full text-xs transition-colors"
                :class="minDurationMs === t ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
                @click="minDurationMs = t"
              >&gt;{{ t >= 1000 ? `${t / 1000}s` : `${t}ms` }}</button>
            </div>
          </div>
          <div class="space-y-0.5">
            <div v-for="facet in sortedFacets" :key="facet.key">
              <button
                class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded text-left text-xs hover:bg-gray-50"
                @click="toggleFacet(facet.key)"
              >
                <svg class="w-3 h-3 shrink-0 text-gray-400 transition-transform duration-100"
                     :class="expandedFacets.has(facet.key) ? 'rotate-90' : ''"
                     viewBox="0 0 6 10" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="1,1 5,5 1,9" />
                </svg>
                <span class="font-mono text-gray-700 truncate flex-1">{{ facet.key }}</span>
                <span
                  v-if="activeCountForKey(facet.key) > 0"
                  class="ml-auto shrink-0 px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium leading-none"
                >{{ activeCountForKey(facet.key) }}</span>
              </button>
              <ul v-if="expandedFacets.has(facet.key)" class="max-h-48 overflow-y-auto pl-5 pr-1 pb-1">
                <li
                  v-for="[val, count] in facetValues(facet.key)"
                  :key="val"
                  class="flex items-center gap-1.5 py-0.5"
                >
                  <input
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5 shrink-0"
                    :checked="activeFilterMap.has(facet.key) && activeFilterMap.get(facet.key)!.has(val)"
                    @change="activeFilterMap.has(facet.key) && activeFilterMap.get(facet.key)!.has(val) ? removeFilter(facet.key, val) : addFilter(facet.key, val)"
                  />
                  <span class="font-mono text-xs text-gray-600 truncate flex-1" :title="val">{{ val }}</span>
                  <span class="shrink-0 text-xs text-gray-400 tabular-nums">{{ count }}</span>
                </li>
              </ul>
            </div>
          </div>
        </aside>

        <!-- Main trace content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <p class="text-xs text-gray-400">
                {{ sortedTraceGroups.length }}<template v-if="hasAnyFilter"> / {{ traceGroups.length }}</template> traces
              </p>
              <template v-if="viewMode !== 'aggregate'">
                <div class="flex items-center gap-0.5 border border-gray-200 rounded p-0.5">
                  <button
                    class="px-2 py-0.5 rounded text-xs transition-colors"
                    :class="traceSortOrder === 'newest' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
                    @click="traceSortOrder = 'newest'"
                  >Newest</button>
                  <button
                    class="px-2 py-0.5 rounded text-xs transition-colors"
                    :class="traceSortOrder === 'slowest' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
                    @click="traceSortOrder = 'slowest'"
                  >Slowest</button>
                </div>
                <button
                  class="text-xs text-gray-400 hover:text-gray-600"
                  @click="toggleAllTraces"
                >{{ allExpanded ? 'Collapse all' : 'Expand all' }}</button>
              </template>
            </div>
            <div class="flex items-center gap-0.5 border border-gray-200 rounded p-0.5">
              <button
                class="px-2 py-0.5 rounded text-xs transition-colors"
                :class="viewMode === 'waterfall' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
                @click="viewMode = 'waterfall'"
              >Waterfall</button>
              <button
                class="px-2 py-0.5 rounded text-xs transition-colors"
                :class="viewMode === 'flamegraph' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
                @click="viewMode = 'flamegraph'"
              >Flame</button>
              <button
                class="px-2 py-0.5 rounded text-xs transition-colors"
                :class="viewMode === 'aggregate' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
                @click="viewMode = 'aggregate'"
              >Aggregate</button>
            </div>
          </div>

      <!-- Aggregate table view -->
      <div v-if="viewMode === 'aggregate'" class="border border-gray-200 rounded-lg overflow-hidden">
        <table class="w-full text-xs">
          <thead>
            <tr class="bg-gray-50 text-gray-500 uppercase tracking-wide">
              <th class="text-left px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="toggleAggSort('name')">
                Operation<span v-if="aggSortKey === 'name'" class="ml-0.5">{{ aggSortAsc ? '↑' : '↓' }}</span>
              </th>
              <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="toggleAggSort('count')">
                Count<span v-if="aggSortKey === 'count'" class="ml-0.5">{{ aggSortAsc ? '↑' : '↓' }}</span>
              </th>
              <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="toggleAggSort('p50')">
                p50<span v-if="aggSortKey === 'p50'" class="ml-0.5">{{ aggSortAsc ? '↑' : '↓' }}</span>
              </th>
              <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="toggleAggSort('p95')">
                p95<span v-if="aggSortKey === 'p95'" class="ml-0.5">{{ aggSortAsc ? '↑' : '↓' }}</span>
              </th>
              <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="toggleAggSort('max')">
                Max<span v-if="aggSortKey === 'max'" class="ml-0.5">{{ aggSortAsc ? '↑' : '↓' }}</span>
              </th>
              <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="toggleAggSort('avgSelfTime')">
                Avg Self<span v-if="aggSortKey === 'avgSelfTime'" class="ml-0.5">{{ aggSortAsc ? '↑' : '↓' }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="agg in spanAggregates" :key="agg.name" class="border-t border-gray-100 hover:bg-gray-50">
              <td class="px-3 py-1.5 font-mono text-gray-800">{{ agg.name }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums text-gray-600">{{ agg.count }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ formatDuration(agg.p50) }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ formatDuration(agg.p95) }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ formatDuration(agg.max) }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ agg.avgSelfTime != null ? formatDuration(agg.avgSelfTime) : '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="spanAggregates.length === 0" class="px-3 py-4 text-gray-400 text-center text-sm">No matching spans</p>
      </div>

      <template v-else>
      <div
        v-for="group in sortedTraceGroups"
        :key="group.traceId"
        class="rounded-lg transition-all"
        :class="expanded.has(group.traceId)
          ? 'mb-2 border border-gray-200 bg-white px-3 py-2'
          : 'mb-0.5 px-1'"
      >

        <!-- Header row — same layout as span rows -->
        <div
          class="flex items-center gap-2 py-0.5 rounded cursor-pointer select-none hover:bg-gray-50"
          :class="expanded.has(group.traceId) ? 'border-b border-gray-100 pb-2 mb-2 hover:bg-transparent' : ''"
          @click="toggle(group.traceId)"
        >
          <!-- Chevron + name + timestamp -->
          <div class="w-64 shrink-0 flex items-center gap-1.5 min-w-0 pl-1">
            <svg class="w-3 h-3 shrink-0 text-gray-400 transition-transform duration-100"
                 :class="expanded.has(group.traceId) ? 'rotate-90' : ''"
                 viewBox="0 0 6 10" fill="none"
                 stroke="currentColor" stroke-width="1.5"
                 stroke-linecap="round" stroke-linejoin="round">
              <polyline points="1,1 5,5 1,9" />
            </svg>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="text-sm font-semibold text-gray-800 truncate" :title="group.label">{{ group.label }}</span>
                <span v-if="group.hasError" class="text-red-500 shrink-0 text-xs" title="One or more spans errored">●</span>
              </div>
              <div class="text-xs text-gray-400 leading-none mt-0.5">{{ formatTime(group.startMs) }} · {{ group.spanCount }} spans</div>
            </div>
          </div>
          <!-- Summary bar: width proportional across all traces -->
          <div class="relative flex-1 h-5 bg-gray-100 rounded overflow-hidden">
            <div class="absolute inset-y-0 left-0 bg-blue-400 rounded"
                 :style="{ width: `${(group.totalDurationMs / maxTraceDurationMs) * 100}%` }">
            </div>
          </div>
          <!-- Total duration -->
          <div class="w-16 text-right text-xs text-gray-600 shrink-0 font-mono whitespace-nowrap">
            {{ formatDuration(group.totalDurationMs) }}
          </div>
        </div>

        <!-- Span rows (collapsed by default) -->
        <ul v-if="expanded.has(group.traceId) && viewMode === 'waterfall'" class="space-y-0.5 mt-0.5">
          <li v-for="span in group.spans" :key="span.spanId"
              class="py-0.5 cursor-pointer transition-opacity"
              :class="isSpanDimmed(span.spanId) ? 'opacity-30' : ''"
              @click="toggleSpan(span.spanId)">
            <div class="flex items-center gap-2">
              <!-- Name, indented by depth -->
              <div class="w-64 shrink-0 flex items-center min-w-0"
                   :style="{ paddingLeft: `${span.depth * 16 + 4}px` }">
                <span class="text-gray-300 mr-1 shrink-0 text-xs leading-none">└</span>
                <span class="text-sm text-gray-600 truncate" :title="span.name">{{ span.name }}</span>
                <span v-if="span.hasError" class="shrink-0 ml-1 text-xs text-gray-500" title="Error">⚠</span>
              </div>
              <!-- Timeline bar: position + width relative to this trace's duration -->
              <div class="relative flex-1 h-5 bg-gray-100 rounded overflow-hidden">
                <div class="absolute inset-y-0 rounded bg-blue-300"
                     :style="{ left: `${span.offsetPct}%`, width: `${Math.max(span.widthPct, 0.5)}%` }">
                </div>
              </div>
              <!-- Duration -->
              <div class="text-right text-xs text-gray-500 shrink-0 font-mono whitespace-nowrap">
                <template v-if="span.durationMs != null">
                  {{ formatDuration(span.durationMs) }}<span v-if="span.selfTimeMs != null && span.selfTimeMs !== span.durationMs" class="text-gray-400"> (self: {{ formatDuration(span.selfTimeMs) }})</span>
                </template>
                <template v-else>—</template>
              </div>
            </div>

            <!-- Detail panel -->
            <div v-if="expandedSpans.has(span.spanId)"
                 class="mt-1.5 px-2 py-2 bg-gray-50 border border-gray-100 rounded text-xs">

              <!-- Timing -->
              <table class="w-full mb-2">
                <tbody>
                  <tr v-if="span.durationMs != null" class="align-top">
                    <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">duration</td>
                    <td class="pb-0.5 text-gray-700 font-mono break-all">{{ formatDuration(span.durationMs) }}</td>
                  </tr>
                  <tr v-if="span.selfTimeMs != null" class="align-top">
                    <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">self time</td>
                    <td class="pb-0.5 text-gray-700 font-mono break-all">{{ formatDuration(span.selfTimeMs) }}</td>
                  </tr>
                </tbody>
              </table>

              <!-- Attributes -->
              <table v-if="span.attributes.length" class="w-full mb-2">
                <tbody>
                  <tr v-for="attr in span.attributes" :key="attr.key" class="align-top">
                    <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">{{ attr.key }}</td>
                    <td class="pb-0.5 text-gray-700 font-mono break-all">{{ otlpValue(attr.value) }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-gray-400 mb-2">No attributes</p>

              <!-- Error details -->
              <template v-if="span.statusMessage || span.exception">
                <p class="text-gray-600 font-medium mb-1">
                  {{ span.exception?.type ?? 'Error' }}: {{ span.statusMessage ?? span.exception?.message }}
                </p>
                <pre v-if="span.exception?.stacktrace"
                     class="text-gray-500 whitespace-pre-wrap break-all bg-white border border-gray-100 rounded p-2 max-h-40 overflow-y-auto leading-relaxed">{{ span.exception.stacktrace }}</pre>
              </template>
            </div>
          </li>
        </ul>

        <!-- Flamegraph (collapsed by default, same toggle as waterfall) -->
        <div v-if="expanded.has(group.traceId) && viewMode === 'flamegraph'" class="mt-0.5">
          <!-- Flame chart canvas -->
          <div
            class="relative w-full"
            :style="{ height: `${(maxDepth(group) + 1) * 22}px` }"
          >
            <div
              v-for="span in group.spans"
              :key="span.spanId"
              class="absolute overflow-hidden cursor-pointer rounded-sm border px-1 flex items-center transition-opacity"
              :class="[
                span.hasError
                  ? (expandedSpans.has(span.spanId) ? 'bg-red-300 border-red-400' : 'bg-red-200 border-red-300 hover:bg-red-300')
                  : (expandedSpans.has(span.spanId) ? 'bg-blue-400 border-blue-500' : 'bg-blue-200 border-blue-300 hover:bg-blue-300'),
                isSpanDimmed(span.spanId) ? 'opacity-30' : '',
              ]"
              :style="{
                left: `${span.offsetPct}%`,
                width: `${Math.max(span.widthPct, 0.3)}%`,
                top: `${span.depth * 22}px`,
                height: '20px',
              }"
              :title="`${span.name}${span.durationMs != null ? ' — ' + span.durationMs.toFixed(1) + ' ms' : ''}`"
              @click="toggleSpan(span.spanId)"
            >
              <span
                v-if="span.widthPct > 2"
                class="text-xs font-mono truncate leading-none text-gray-800 select-none"
              >{{ span.name }}</span>
            </div>
          </div>

          <!-- Detail panels for selected spans (below the chart) -->
          <template v-for="span in group.spans" :key="`detail-${span.spanId}`">
            <div v-if="expandedSpans.has(span.spanId)"
                 class="mt-1.5 px-2 py-2 bg-gray-50 border border-gray-100 rounded text-xs">
              <p class="font-mono font-medium text-gray-700 mb-1.5 truncate">{{ span.name }}</p>
              <!-- Timing -->
              <table class="w-full mb-2">
                <tbody>
                  <tr v-if="span.durationMs != null" class="align-top">
                    <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">duration</td>
                    <td class="pb-0.5 text-gray-700 font-mono break-all">{{ formatDuration(span.durationMs) }}</td>
                  </tr>
                  <tr v-if="span.selfTimeMs != null" class="align-top">
                    <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">self time</td>
                    <td class="pb-0.5 text-gray-700 font-mono break-all">{{ formatDuration(span.selfTimeMs) }}</td>
                  </tr>
                </tbody>
              </table>
              <!-- Attributes -->
              <table v-if="span.attributes.length" class="w-full mb-2">
                <tbody>
                  <tr v-for="attr in span.attributes" :key="attr.key" class="align-top">
                    <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">{{ attr.key }}</td>
                    <td class="pb-0.5 text-gray-700 font-mono break-all">{{ otlpValue(attr.value) }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-gray-400 mb-2">No attributes</p>
              <template v-if="span.statusMessage || span.exception">
                <p class="text-gray-600 font-medium mb-1">
                  {{ span.exception?.type ?? 'Error' }}: {{ span.statusMessage ?? span.exception?.message }}
                </p>
                <pre v-if="span.exception?.stacktrace"
                     class="text-gray-500 whitespace-pre-wrap break-all bg-white border border-gray-100 rounded p-2 max-h-40 overflow-y-auto leading-relaxed">{{ span.exception.stacktrace }}</pre>
              </template>
            </div>
          </template>
        </div>

      </div>
      </template>
        </div><!-- /flex-1 -->
      </div><!-- /flex -->
    </div>

    <div v-else class="text-gray-500 text-sm">No trace data available.</div>
  </div>
</template>