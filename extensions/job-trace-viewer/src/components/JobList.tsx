import { useEffect, useState } from "react";

import { fetchJobs, type ContentItem, type Job } from "../api";

interface JobListProps {
  content: ContentItem;
  onSelect: (job: Job) => void;
  onBack: () => void;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function jobStatusLabel(job: Job): string {
  if (!job.finalized) return "Running";
  if (job.exit_code === 0) return "Success";
  if (job.exit_code !== null) return `Failed (exit ${job.exit_code})`;
  return "Finalized";
}

function jobStatusClass(job: Job): string {
  if (!job.finalized)
    return "text-agentprism-pending bg-agentprism-pending-muted";
  if (job.exit_code === 0)
    return "text-agentprism-success bg-agentprism-success-muted";
  return "text-agentprism-error bg-agentprism-error-muted";
}

export function JobList({ content, onSelect, onBack }: JobListProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJobs(content.guid)
      .then(setJobs)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load jobs");
      })
      .finally(() => setLoading(false));
  }, [content.guid]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <button
          onClick={onBack}
          className="text-sm text-agentprism-muted-foreground hover:text-agentprism-foreground transition-colors"
        >
          ← Back
        </button>
      </div>

      <div>
        <h1 className="text-2xl font-semibold text-agentprism-foreground mb-1">
          {content.title}
        </h1>
        <p className="text-xs text-agentprism-muted-foreground">{content.guid}</p>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="text-agentprism-muted-foreground">Loading jobs...</div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded border border-agentprism-error text-agentprism-error">
          {error}
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div className="text-agentprism-muted-foreground text-sm py-8 text-center">
          No jobs found for this content item.
        </div>
      )}

      {!loading && !error && jobs.length > 0 && (
        <div className="flex flex-col gap-2">
          {jobs.map((job) => (
            <button
              key={job.key}
              onClick={() => onSelect(job)}
              className="text-left px-4 py-3 rounded border border-agentprism-border bg-agentprism-background hover:bg-agentprism-accent hover:border-agentprism-primary transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-sm text-agentprism-foreground">
                  {job.key}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${jobStatusClass(job)}`}
                >
                  {jobStatusLabel(job)}
                </span>
              </div>
              <div className="text-xs text-agentprism-muted-foreground mt-1">
                Started: {formatDate(job.start_time)}
                {job.end_time && ` · Ended: ${formatDate(job.end_time)}`}
              </div>
              {job.tag && (
                <div className="text-xs text-agentprism-muted-foreground mt-0.5">
                  Tag: {job.tag}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
