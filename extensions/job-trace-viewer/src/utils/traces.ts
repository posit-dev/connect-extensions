import {
  flattenSpans,
  openTelemetrySpanAdapter,
} from "@evilmartians/agent-prism-data";
import type { OpenTelemetryDocument } from "@evilmartians/agent-prism-types";

import type { TraceViewerData } from "../components/agent-prism/TraceViewer/TraceViewer";

// Raw OTel span structure for extracting traceId before adapter conversion
interface RawSpan {
  traceId: string;
  status?: { code: string };
  [key: string]: unknown;
}

interface RawScopeSpan {
  spans: RawSpan[];
  [key: string]: unknown;
}

interface RawResourceSpan {
  scopeSpans: RawScopeSpan[];
  [key: string]: unknown;
}

interface RawDocument {
  resourceSpans: RawResourceSpan[];
}

/**
 * Groups raw OpenTelemetry documents by traceId, converts each group to
 * TraceViewerData for the agent-prism TraceViewer component.
 */
export function groupTracesByTraceId(
  rawDocuments: unknown[],
): TraceViewerData[] {
  if (!rawDocuments.length) return [];

  const documents = rawDocuments as OpenTelemetryDocument[];
  const traceDocMap = new Map<string, OpenTelemetryDocument[]>();

  for (const doc of documents) {
    const rawDoc = doc as unknown as RawDocument;
    const traceIds = new Set<string>();

    for (const rs of rawDoc.resourceSpans ?? []) {
      for (const ss of rs.scopeSpans ?? []) {
        for (const span of ss.spans ?? []) {
          if (span.traceId) traceIds.add(span.traceId);
        }
      }
    }

    for (const traceId of traceIds) {
      // Create a filtered copy of this document containing only spans for this traceId.
      // Also ensure every span has a `status` field — the adapter does `span.status.code`
      // without optional chaining, so spans without status crash at runtime.
      const filteredDoc = {
        ...rawDoc,
        resourceSpans: rawDoc.resourceSpans
          .map((rs) => ({
            ...rs,
            scopeSpans: rs.scopeSpans
              .map((ss) => ({
                ...ss,
                spans: ss.spans
                  .filter((s) => s.traceId === traceId)
                  .map((s) => ({
                    ...s,
                    status: s.status ?? { code: "STATUS_CODE_OK" },
                  })),
              }))
              .filter((ss) => ss.spans.length > 0),
          }))
          .filter((rs) => rs.scopeSpans.length > 0),
      } as unknown as OpenTelemetryDocument;

      const existing = traceDocMap.get(traceId);
      if (existing) {
        existing.push(filteredDoc);
      } else {
        traceDocMap.set(traceId, [filteredDoc]);
      }
    }
  }

  const result: TraceViewerData[] = [];

  for (const [traceId, docs] of traceDocMap) {
    const spans = openTelemetrySpanAdapter.convertRawDocumentsToSpans(docs);
    if (spans.length === 0) continue;

    const allSpans = flattenSpans(spans);
    const startTimes = allSpans.map((s) => s.startTime.getTime());
    const endTimes = allSpans.map((s) => s.endTime.getTime());
    const minStart = Math.min(...startTimes);
    const maxEnd = Math.max(...endTimes);
    const durationMs = maxEnd - minStart;

    const name = spans[0]?.title ?? `Trace ${traceId.substring(0, 8)}`;

    result.push({
      traceRecord: {
        id: traceId,
        name,
        spansCount: allSpans.length,
        durationMs,
        agentDescription: "",
        startTime: minStart,
      },
      spans,
    });
  }

  // Sort newest first
  result.sort((a, b) => {
    const aTime = a.traceRecord.startTime ?? 0;
    const bTime = b.traceRecord.startTime ?? 0;
    return bTime - aTime;
  });

  return result;
}
