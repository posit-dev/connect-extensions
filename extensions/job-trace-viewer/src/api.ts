export interface ContentItem {
  guid: string;
  name: string;
  title: string;
  description: string;
  app_mode: string;
  created_time: string | null;
  last_deployed_time: string | null;
  dashboard_url: string;
}

export interface Job {
  id: number;
  ppid: number;
  pid: number;
  key: string;
  app_id: number;
  variant_id: number;
  bundle_id: number | null;
  start_time: string;
  end_time: string | null;
  exit_code: number | null;
  finalized: boolean;
  tag: string;
  hostname: string;
}

export interface JobsResponse {
  results: Job[];
  total: number;
}

export async function fetchContent(): Promise<ContentItem[]> {
  const response = await fetch("/api/content");
  if (!response.ok) {
    throw new Error(`Failed to fetch content: ${response.statusText}`);
  }
  return response.json() as Promise<ContentItem[]>;
}

export async function fetchJobs(guid: string): Promise<Job[]> {
  const response = await fetch(`/api/content/${guid}/jobs`);
  if (!response.ok) {
    throw new Error(`Failed to fetch jobs: ${response.statusText}`);
  }
  const data = (await response.json()) as JobsResponse | Job[];
  // Connect returns { results: [...], total: N }
  if (Array.isArray(data)) return data;
  return data.results;
}

export async function fetchTraces(guid: string, key: string): Promise<unknown[]> {
  const response = await fetch(`/api/content/${guid}/jobs/${key}/traces`);
  if (!response.ok) {
    throw new Error(`Failed to fetch traces: ${response.statusText}`);
  }
  return response.json() as Promise<unknown[]>;
}
