import { computed, reactive } from "vue";
import type { TraceGroup } from "../types";

export function useTraceExpansion(sortedTraceGroups: () => TraceGroup[]) {
  const expanded = reactive(new Set<string>());
  const expandedSpans = reactive(new Set<string>());

  function toggle(traceId: string) {
    if (expanded.has(traceId)) expanded.delete(traceId);
    else expanded.add(traceId);
  }

  const allExpanded = computed(() =>
    sortedTraceGroups().length > 0 &&
    sortedTraceGroups().every(g => expanded.has(g.traceId))
  );

  function toggleAllTraces() {
    if (allExpanded.value) {
      for (const g of sortedTraceGroups()) expanded.delete(g.traceId);
    } else {
      for (const g of sortedTraceGroups()) expanded.add(g.traceId);
    }
  }

  function toggleSpan(spanId: string) {
    if (expandedSpans.has(spanId)) expandedSpans.delete(spanId);
    else expandedSpans.add(spanId);
  }

  function autoExpandFirst() {
    if (expanded.size === 0) {
      const first = sortedTraceGroups()[0];
      if (first) expanded.add(first.traceId);
    }
  }

  return {
    expanded,
    expandedSpans,
    toggle,
    allExpanded,
    toggleAllTraces,
    toggleSpan,
    autoExpandFirst,
  };
}
