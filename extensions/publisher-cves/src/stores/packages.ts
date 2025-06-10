import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useContentStore } from "./content";

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
  const currentContentId = ref<string | null>(null);

  // Get the current content packages based on currentContentId
  const currentContent = computed(() => {
    if (!currentContentId.value || !contentItems.value[currentContentId.value]) {
      return null;
    }
    return contentItems.value[currentContentId.value];
  });

  // Get current packages based on currentContentId
  const packages = computed(() => {
    return currentContent.value ? currentContent.value.packages : [];
  });

  // Track if any packages are currently being fetched
  const isFetchingAny = computed(() => {
    return Object.values(contentItems.value).some(item => item.isLoading);
  });

  // Check if the current content has been fetched
  const isFetched = computed(() => {
    return currentContent.value ? currentContent.value.isFetched : false;
  });

  // Get the last fetch time for the current content
  const lastFetchTime = computed(() => {
    return currentContent.value ? currentContent.value.lastFetchTime : null;
  });

  // Computed properties for status info for the current content
  const packagesByLanguage = computed(() => {
    const result: Record<string, Package[]> = {};
    
    if (!packages.value) return result;
    
    for (const pkg of packages.value) {
      const language = pkg.language.toLowerCase();
      if (!result[language]) {
        result[language] = [];
      }
      result[language].push(pkg);
    }
    
    return result;
  });

  // Set current content ID
  function setCurrentContentId(contentId: string) {
    currentContentId.value = contentId;
  }

  // Fetch packages for a specific content ID
  async function fetchPackagesForContent(contentId: string) {
    // Set this as the current content ID
    currentContentId.value = contentId;
    
    // Get the content info from the content store
    const contentStore = useContentStore();
    
    // Initialize or update the content item
    if (!contentItems.value[contentId]) {
      // Initialize content item
      contentItems.value[contentId] = {
        guid: contentId,
        packages: [],
        isLoading: true,
        error: null,
        isFetched: false,
        lastFetchTime: null
      };
    } else {
      // Update existing content item loading state
      contentItems.value[contentId].isLoading = true;
      contentItems.value[contentId].error = null;
    }

    try {
      const response = await fetch(`/api/packages/${contentId}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update the content item with the fetched packages
      contentItems.value[contentId].packages = data;
      contentItems.value[contentId].isFetched = true;
      contentItems.value[contentId].lastFetchTime = new Date();
    } catch (err) {
      console.error("Error fetching packages:", err);
      contentItems.value[contentId].error = err as Error;
      throw err;
    } finally {
      contentItems.value[contentId].isLoading = false;
    }
  }

  // Reset store state
  function reset() {
    // Reset packages state
    contentItems.value = {};
    isLoading.value = false;
    error.value = null;
    currentContentId.value = null;
  }

  return {
    // State
    contentItems,
    currentContentId,
    isLoading,
    error,
    
    // Computed getters
    packages,
    currentContent,
    isFetched,
    lastFetchTime,
    isFetchingAny,
    packagesByLanguage,
    
    // Actions
    fetchPackagesForContent,
    setCurrentContentId,
    reset
  };
});