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
