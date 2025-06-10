import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface Package {
  hash: string | null;
  language: string;
  name: string;
  version: string;
}

export const usePackagesStore = defineStore("packages", () => {
  const packages = ref<Package[]>([]);
  const isLoading = ref(false);
  const error = ref<Error | null>(null);
  const currentContentId = ref<string | null>(null);
  
  // Track fetch status
  const isFetched = ref(false);
  const lastFetchTime = ref<Date | null>(null);

  // Computed properties for status info
  const packagesByLanguage = computed(() => {
    const result: Record<string, Package[]> = {};
    
    for (const pkg of packages.value) {
      const language = pkg.language.toLowerCase();
      if (!result[language]) {
        result[language] = [];
      }
      result[language].push(pkg);
    }
    
    return result;
  });

  async function fetchPackagesForContent(contentId: string) {
    isLoading.value = true;
    error.value = null;
    packages.value = [];
    currentContentId.value = contentId;

    try {
      const response = await fetch(`/api/packages/${contentId}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      packages.value = data;
      isFetched.value = true;
      lastFetchTime.value = new Date();
    } catch (err) {
      console.error("Error fetching packages:", err);
      error.value = err as Error;
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  // Reset store state
  function reset() {
    packages.value = [];
    isLoading.value = false;
    error.value = null;
    isFetched.value = false;
    lastFetchTime.value = null;
    currentContentId.value = null;
  }

  return {
    // State
    packages,
    isLoading,
    error,
    isFetched,
    lastFetchTime,
    currentContentId,
    
    // Getters
    packagesByLanguage,
    
    // Actions
    fetchPackagesForContent,
    reset
  };
});