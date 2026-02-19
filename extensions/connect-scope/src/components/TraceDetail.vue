<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";
import { useTracesStore } from "../stores/traces";
import type { ContentItem, Job, OtlpRecord, OtlpSpan, OtlpAnyValue, FlatSpan } from "../types";

const props = defineProps<{
  content: ContentItem;
  job: Job;
  traceId: string;
}>();

const tracesStore = useTracesStore();

onMounted(() => {
  if (!tracesStore.traceData) {
    tracesStore.fetchTraces(props.content.guid, props.job.key);
  }
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

function otlpValue(v: OtlpAnyValue): string {
  if (v.stringValue != null) return v.stringValue;
  if (v.intValue    != null) return v.intValue;
  if (v.floatValue  != null) return String(v.floatValue);
  if (v.boolValue   != null) return String(v.boolValue);
  if (v.arrayValue  != null) return JSON.stringify(v.arrayValue.values ?? []);
  if (v.kvlistValue != null) return JSON.stringify(v.kvlistValue.values ?? []);
  return "";
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

const group = computed((): TraceGroup | null => {
  const records = tracesStore.traceData as OtlpRecord[] | null;
  if (!records) return null;

  const rawSpans: OtlpSpan[] = records
    .flatMap(r => r.resourceSpans ?? [])
    .flatMap(rs => rs.scopeSpans ?? [])
    .flatMap(ss => ss.spans ?? [])
    .filter(s => s.traceId === props.traceId);

  if (rawSpans.length === 0) return null;
  return buildTraceGroup(props.traceId, rawSpans);
});

function formatDuration(ms: number): string {
  if (ms >= 1000) return (ms / 1000).toFixed(2) + " s";
  return ms.toFixed(1) + " ms";
}

function maxDepth(g: TraceGroup): number {
  return g.spans.reduce((max, s) => Math.max(max, s.depth), 0);
}

const viewMode = ref<'waterfall' | 'flamegraph'>('waterfall');

const expandedSpans = reactive(new Set<string>());

function toggleSpan(spanId: string) {
  if (expandedSpans.has(spanId)) expandedSpans.delete(spanId);
  else expandedSpans.add(spanId);
}
</script>

<template>
  <div>
    <LoadingSpinner v-if="tracesStore.isLoading && !group" message="Loading..." class="mt-16" />

    <div v-else-if="tracesStore.error" class="text-red-600 text-sm">{{ tracesStore.error }}</div>

    <div v-else-if="!group" class="text-gray-500 text-sm">Trace not found.</div>

    <div v-else>
      <!-- Heading -->
      <div class="flex items-start justify-between mb-4">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-lg font-semibold text-gray-800 truncate">{{ group.label }}</h2>
            <span v-if="group.hasError" class="text-red-500 text-xs" title="One or more spans errored">●</span>
          </div>
          <p class="text-xs text-gray-400 mt-0.5 font-mono">{{ group.spanCount }} spans · {{ formatDuration(group.totalDurationMs) }}</p>
        </div>
        <!-- View toggle -->
        <div class="flex items-center gap-0.5 border border-gray-200 rounded p-0.5 shrink-0">
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
        </div>
      </div>

      <!-- Waterfall -->
      <ul v-if="viewMode === 'waterfall'" class="space-y-0.5">
        <li v-for="span in group.spans" :key="span.spanId"
            class="py-0.5 cursor-pointer"
            @click="toggleSpan(span.spanId)">
          <div class="flex items-center gap-2">
            <div class="w-64 shrink-0 flex items-center min-w-0"
                 :style="{ paddingLeft: `${span.depth * 16 + 4}px` }">
              <span class="text-gray-300 mr-1 shrink-0 text-xs leading-none">└</span>
              <span class="text-sm text-gray-600 truncate" :title="span.name">{{ span.name }}</span>
              <span v-if="span.hasError" class="shrink-0 ml-1 text-xs text-gray-500" title="Error">⚠</span>
            </div>
            <div class="relative flex-1 h-5 bg-gray-100 rounded overflow-hidden">
              <div class="absolute inset-y-0 rounded bg-blue-300"
                   :style="{ left: `${span.offsetPct}%`, width: `${Math.max(span.widthPct, 0.5)}%` }">
              </div>
            </div>
            <div class="w-16 text-right text-xs text-gray-500 shrink-0 font-mono whitespace-nowrap">
              {{ span.durationMs != null ? span.durationMs.toFixed(1) + ' ms' : '—' }}
            </div>
          </div>

          <div v-if="expandedSpans.has(span.spanId)"
               class="mt-1.5 px-2 py-2 bg-gray-50 border border-gray-100 rounded text-xs">
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
        </li>
      </ul>

      <!-- Flamegraph -->
      <div v-else-if="viewMode === 'flamegraph'">
        <div class="relative w-full" :style="{ height: `${(maxDepth(group) + 1) * 22}px` }">
          <div
            v-for="span in group.spans"
            :key="span.spanId"
            class="absolute overflow-hidden cursor-pointer rounded-sm border px-1 flex items-center"
            :class="span.hasError
              ? (expandedSpans.has(span.spanId) ? 'bg-red-300 border-red-400' : 'bg-red-200 border-red-300 hover:bg-red-300')
              : (expandedSpans.has(span.spanId) ? 'bg-blue-400 border-blue-500' : 'bg-blue-200 border-blue-300 hover:bg-blue-300')"
            :style="{
              left: `${span.offsetPct}%`,
              width: `${Math.max(span.widthPct, 0.3)}%`,
              top: `${span.depth * 22}px`,
              height: '20px',
            }"
            :title="`${span.name}${span.durationMs != null ? ' — ' + span.durationMs.toFixed(1) + ' ms' : ''}`"
            @click="toggleSpan(span.spanId)"
          >
            <span v-if="span.widthPct > 2"
                  class="text-xs font-mono truncate leading-none text-gray-800 select-none">{{ span.name }}</span>
          </div>
        </div>

        <template v-for="span in group.spans" :key="`detail-${span.spanId}`">
          <div v-if="expandedSpans.has(span.spanId)"
               class="mt-1.5 px-2 py-2 bg-gray-50 border border-gray-100 rounded text-xs">
            <p class="font-mono font-medium text-gray-700 mb-1.5 truncate">{{ span.name }}</p>
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
  </div>
</template>
