export interface ContentItem {
  guid: string;
  name: string;
  title: string | null;
  app_mode: string | null;
  created_time: string;
  last_deployed_time: string | null;
}

export type JobStatus = 0 | 1 | 2; // 0=Active, 1=Finished, 2=Finalized

export interface Job {
  id: string;
  key: string;
  tag: string;
  status: JobStatus;
  start_time: string;
  end_time: string | null;
  exit_code: number | null;
  hostname: string;
}

export type TraceData = unknown;

export interface OtlpAnyValue {
  stringValue?: string;
  intValue?: string;    // proto3 int64 transmitted as string
  floatValue?: number;
  boolValue?: boolean;
  arrayValue?: { values?: OtlpAnyValue[] };
  kvlistValue?: { values?: Array<{ key: string; value: OtlpAnyValue }> };
}

export interface OtlpSpan {
  name: string;
  traceId?: string;
  spanId?: string;
  parentSpanId?: string;
  startTimeUnixNano?: string;
  endTimeUnixNano?: string;
  attributes?: Array<{ key: string; value: OtlpAnyValue }>;
  events?: Array<{
    timeUnixNano?: string;
    name: string;
    attributes?: Array<{ key: string; value: OtlpAnyValue }>;
  }>;
  status?: { code?: number; message?: string }; // code 2 = ERROR
}

export interface OtlpRecord {
  resourceSpans?: Array<{
    scopeSpans?: Array<{
      spans?: OtlpSpan[];
    }>;
  }>;
}

export interface FlatSpan {
  name: string;
  spanId: string;
  parentSpanId: string | null;
  startNs: bigint;
  durationMs: number | null;
  depth: number;
  offsetPct: number; // left offset as % of total trace duration
  widthPct: number;  // width as % of total trace duration
  hasError: boolean;
  attributes: Array<{ key: string; value: OtlpAnyValue }>;
  statusMessage: string | null;
  exception: { type?: string; message?: string; stacktrace?: string } | null;
}
