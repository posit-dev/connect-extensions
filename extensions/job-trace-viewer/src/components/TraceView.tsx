import { useEffect, useState } from "react";

import { fetchTraces, type ContentItem, type Job } from "../api";
import { TraceViewer } from "./agent-prism/TraceViewer/TraceViewer";
import { groupTracesByTraceId } from "../utils/traces";
import type { TraceViewerData } from "./agent-prism/TraceViewer/TraceViewer";

interface TraceViewProps {
  content: ContentItem;
  job: Job;
  onBack: () => void;
}

export function TraceView({ content, job, onBack }: TraceViewProps) {
  const [traces, setTraces] = useState<TraceViewerData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noTraces, setNoTraces] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNoTraces(false);

    fetchTraces(content.guid, job.key)
      .then((docs) => {
        if (!docs.length) {
          setNoTraces(true);
          return;
        }
        const grouped = groupTracesByTraceId(docs);
        if (grouped.length === 0) {
          setNoTraces(true);
        } else {
          setTraces(grouped);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load traces");
      })
      .finally(() => setLoading(false));
  }, [content.guid, job.key]);

  return (
    <div className="flex flex-col h-screen">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-agentprism-border bg-agentprism-background shrink-0">
        <button
          onClick={onBack}
          className="text-sm text-agentprism-muted-foreground hover:text-agentprism-foreground transition-colors"
        >
          ← Jobs
        </button>
        <span className="text-agentprism-border">|</span>
        <span className="text-sm font-medium text-agentprism-foreground truncate">
          {content.title}
        </span>
        <span className="text-agentprism-border">·</span>
        <span className="text-sm font-mono text-agentprism-muted-foreground">
          {job.key}
        </span>
      </div>

      <div className="flex-1 overflow-hidden">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-agentprism-muted-foreground">
              Loading traces...
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 m-4 rounded border border-agentprism-error text-agentprism-error">
            {error}
          </div>
        )}

        {!loading && !error && noTraces && (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <div className="text-agentprism-muted-foreground">
              No trace data available for this job.
            </div>
            <div className="text-xs text-agentprism-muted-foreground">
              Traces are only recorded for content that emits OpenTelemetry spans.
            </div>
          </div>
        )}

        {!loading && !error && traces.length > 0 && (
          <TraceViewer data={traces} />
        )}
      </div>
    </div>
  );
}
