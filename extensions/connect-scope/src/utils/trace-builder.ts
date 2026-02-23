import type { OtlpAnyValue, OtlpSpan, FlatSpan, TraceGroup } from "../types";

export function otlpValue(v: OtlpAnyValue): string {
  if (v.stringValue != null) return v.stringValue;
  if (v.intValue    != null) return v.intValue;
  if (v.floatValue  != null) return String(v.floatValue);
  if (v.boolValue   != null) return String(v.boolValue);
  if (v.arrayValue  != null) return JSON.stringify(v.arrayValue.values ?? []);
  if (v.kvlistValue != null) return JSON.stringify(v.kvlistValue.values ?? []);
  return "";
}

export function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

export function buildTraceGroup(traceId: string, spans: OtlpSpan[]): TraceGroup {
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

  const maxDepth = flat.reduce((max, s) => Math.max(max, s.depth), 0);

  return {
    traceId,
    label: roots[0]?.name ?? "Trace",
    startNs: traceStartNs,
    startMs: Number(traceStartNs / 1_000_000n),
    totalDurationMs: Number(traceEndNs - traceStartNs) / 1_000_000,
    hasError: flat.some(s => s.hasError),
    spanCount: flat.length,
    maxDepth,
    spans: flat,
  };
}
