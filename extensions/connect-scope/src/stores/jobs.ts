import { defineStore } from "pinia";
import { ref } from "vue";
import type { Job } from "../types";

export const useJobsStore = defineStore("jobs", () => {
  const jobs = ref<Job[]>([]);
  const selectedJob = ref<Job | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchJobs(guid: string) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await fetch(`/api/content/${guid}/jobs`);
      if (!response.ok) throw new Error("Failed to fetch jobs");
      jobs.value = await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Unknown error";
    } finally {
      isLoading.value = false;
    }
  }

  function selectJob(job: Job) {
    selectedJob.value = job;
  }

  function clearSelection() {
    jobs.value = [];
    selectedJob.value = null;
  }

  return { jobs, selectedJob, isLoading, error, fetchJobs, selectJob, clearSelection };
});
