import { defineStore } from "pinia";
import { ref } from "vue";

export interface Package {
  hash: string | null;
  language: string;
  name: string;
  version: string;
}

export interface ContentPackages {
  guid: string;
  packages: Package[];
  isLoading: boolean;
  error: Error | null;
  isFetched: boolean;
  lastFetchTime: Date | null;
}

export const usePackagesStore = defineStore("packages", () => {
  // Map of content packages by GUID
  const contentItems = ref<Record<string, ContentPackages>>({});
  const isLoading = ref(false);
  const error = ref<Error | null>(null);

  // Fetch packages for a specific content ID
  async function fetchPackagesForContent(contentId: string) {
    // Initialize or update the content item
    if (!contentItems.value[contentId]) {
      // Initialize content item
      contentItems.value[contentId] = {
        guid: contentId,
        packages: [],
        isLoading: true,
        error: null,
        isFetched: false,
        lastFetchTime: null,
      };
    } else {
      // Update existing content item loading state
      contentItems.value[contentId].isLoading = true;
      contentItems.value[contentId].error = null;
    }

    try {
      const response = await fetch(`/api/packages/${contentId}`);

      if (!response.ok) {
        throw new Error(`HTTP error - Status: ${response.status}`);
      }

      const data = await response.json();

      // Update the content item with the fetched packages
      contentItems.value[contentId].packages = data;
      contentItems.value[contentId].isFetched = true;
      contentItems.value[contentId].lastFetchTime = new Date();
    } catch (err) {
      console.error("Error fetching packages:", err);
      contentItems.value[contentId].error = err as Error;
      contentItems.value[contentId].isFetched = true;
      throw err;
    } finally {
      contentItems.value[contentId].isLoading = false;
    }
  }

  return {
    // State
    contentItems,
    isLoading,
    error,

    // Actions
    fetchPackagesForContent,
  };
});
