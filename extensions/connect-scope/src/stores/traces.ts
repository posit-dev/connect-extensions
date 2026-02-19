import { defineStore } from "pinia";
import { ref } from "vue";
import type { TraceData } from "../types";
import { apiBase } from "../api";

export const useTracesStore = defineStore("traces", () => {
  const traceData = ref<TraceData | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const selectedTraceId = ref<string | null>(null);

  async function fetchTraces(guid: string, jobKey: string) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await fetch(`${apiBase}/api/content/${guid}/jobs/${jobKey}/traces`);
      if (!response.ok) throw new Error("Failed to fetch traces");
      traceData.value = await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Unknown error";
    } finally {
      isLoading.value = false;
    }
  }

  function clear() {
    traceData.value = null;
    error.value = null;
    selectedTraceId.value = null;
  }

  return { traceData, isLoading, error, fetchTraces, clear, selectedTraceId };
});
