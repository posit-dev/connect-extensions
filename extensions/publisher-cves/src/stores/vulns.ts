import { defineStore } from "pinia";
import { ref } from "vue";

interface VulnerabilityData {
  [key: string]: any;
}

export const useVulnsStore = defineStore("vulns", () => {
  const pypi = ref<VulnerabilityData[]>([]);
  const cran = ref<VulnerabilityData[]>([]);

  const isLoading = ref(false);
  const error = ref<Error | null>(null);

  // Actions
  async function fetchVulns() {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await fetch("/api/vulns");
      const data = await response.json();

      // Data structure based on main.py shows results[repo] = data format
      pypi.value = data.pypi || [];
      cran.value = data.cran || [];
    } catch (err) {
      console.error("Error fetching vulnerabilities:", err);
      error.value = err as Error;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    pypi,
    cran,
    isLoading,
    error,
    fetchVulns,
  };
});
