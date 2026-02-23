import { computed, ref } from "vue";
import type { SpanAggregate, AggSortKey, TraceGroup } from "../types";
import { percentile } from "../utils/trace-builder";

export function useAggregateView(filteredTraceGroups: () => TraceGroup[]) {
  const aggSortKey = ref<AggSortKey>('p95');
  const aggSortAsc = ref(false);

  function toggleAggSort(key: AggSortKey) {
    if (aggSortKey.value === key) {
      aggSortAsc.value = !aggSortAsc.value;
    } else {
      aggSortKey.value = key;
      aggSortAsc.value = key === 'name';
    }
  }

  const spanAggregates = computed((): SpanAggregate[] => {
    const groups = new Map<string, number[]>();
    for (const g of filteredTraceGroups()) {
      for (const span of g.spans) {
        if (span.durationMs == null) continue;
        let durations = groups.get(span.name);
        if (!durations) {
          durations = [];
          groups.set(span.name, durations);
        }
        durations.push(span.durationMs);
      }
    }

    // Compute grand total for pctOfTotal
    let grandTotal = 0;
    for (const durations of groups.values()) {
      for (const d of durations) grandTotal += d;
    }

    const result: SpanAggregate[] = [];
    for (const [name, durations] of groups) {
      durations.sort((a, b) => a - b);
      const total = durations.reduce((s, d) => s + d, 0);
      result.push({
        name,
        count: durations.length,
        min: durations[0],
        max: durations[durations.length - 1],
        p50: percentile(durations, 50),
        p95: percentile(durations, 95),
        total,
        avg: total / durations.length,
        pctOfTotal: grandTotal > 0 ? (total / grandTotal) * 100 : 0,
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

  const traceSummaryStats = computed(() => {
    const groups = filteredTraceGroups();
    const totalTraces = groups.length;
    const totalDuration = groups.reduce((s, g) => s + g.totalDurationMs, 0);
    const avgDuration = totalTraces > 0 ? totalDuration / totalTraces : 0;
    const errorCount = groups.filter(g => g.hasError).length;
    const errorRate = totalTraces > 0 ? (errorCount / totalTraces) * 100 : 0;
    return { totalTraces, avgDuration, errorRate };
  });

  return {
    aggSortKey,
    aggSortAsc,
    toggleAggSort,
    spanAggregates,
    traceSummaryStats,
  };
}
