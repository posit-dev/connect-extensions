import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface Vulnerability {
  id: string;
  versions: Record<string, any>;
  ranges: Array<{
    type: string;
    events: Array<{
      introduced?: string;
      fixed?: string;
    }>;
  }>;
  summary: string;
  details: string;
  modified: string;
  published: string;
}

export interface VulnerabilityMap {
  [packageName: string]: Vulnerability[];
}

export const useVulnsStore = defineStore("vulns", () => {
  // State
  const pypi = ref<VulnerabilityMap>({});
  const cran = ref<VulnerabilityMap>({});
  const isLoading = ref(false);
  const error = ref<Error | null>(null);

  // Track fetch status
  const isFetched = ref(false);
  const lastFetchTime = ref<Date | null>(null);

  // Computed properties
  const totalVulns = computed(() => {
    let count = 0;

    // Count vulnerabilities in pypi
    for (const packageName in pypi.value) {
      count += pypi.value[packageName].length;
    }

    // Count vulnerabilities in cran
    for (const packageName in cran.value) {
      count += cran.value[packageName].length;
    }

    return count;
  });

  const affectedPackageCount = computed(() => {
    return Object.keys(pypi.value).length + Object.keys(cran.value).length;
  });

  // Actions
  async function fetchVulns() {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await fetch("/api/vulns");

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();

      pypi.value = data.pypi || {};
      cran.value = data.cran || {};
      isFetched.value = true;
      lastFetchTime.value = new Date();
    } catch (err) {
      console.error("Error fetching vulnerabilities:", err);
      error.value = err as Error;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    // State
    pypi,
    cran,
    isLoading,
    error,
    isFetched,
    lastFetchTime,

    // Getters
    totalVulns,
    affectedPackageCount,

    // Actions
    fetchVulns,
  };
});
