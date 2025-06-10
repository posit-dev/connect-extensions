import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface Package {
  hash: string | null;
  language: string;
  name: string;
  version: string;
}

export interface ContentItem {
  guid: string;
  title: string;
  content_url?: string;
  dashboard_url?: string;
  packages: Package[];
  isLoading: boolean;
  error: Error | null;
  isFetched: boolean;
  lastFetchTime: Date | null;
}

export const usePackagesStore = defineStore("packages", () => {
  // Map of content items by GUID
  const contentItems = ref<Record<string, ContentItem>>({});
  const isLoading = ref(false);
  const error = ref<Error | null>(null);
  const currentContentId = ref<string | null>(null);
  const contentList = ref<Array<{guid: string; title: string; app_mode?: string; content_url?: string; dashboard_url?: string}>>([]);
  const contentListLoading = ref(false);
  const contentListError = ref<Error | null>(null);

  // Get the current content item based on currentContentId
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

  // Fetch all available content items
  async function fetchContentList() {
    contentListLoading.value = true;
    contentListError.value = null;
    
    try {
      const response = await fetch("/api/content");
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      contentList.value = data;
    } catch (err) {
      console.error("Error fetching content list:", err);
      contentListError.value = err as Error;
      throw err;
    } finally {
      contentListLoading.value = false;
    }
  }

  // Set current content ID
  function setCurrentContentId(contentId: string) {
    currentContentId.value = contentId;
  }

  // Fetch packages for a specific content ID
  async function fetchPackagesForContent(contentId: string) {
    // Set this as the current content ID
    currentContentId.value = contentId;
    
    // Initialize or update the content item
    if (!contentItems.value[contentId]) {
      // Find content info from the content list
      const contentInfo = contentList.value.find(item => item.guid === contentId);
      
      // Initialize content item
      contentItems.value[contentId] = {
        guid: contentId,
        title: contentInfo?.title || contentId,
        content_url: contentInfo?.content_url,
        dashboard_url: contentInfo?.dashboard_url,
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
  function reset(preserveContentList = true) {
    // Reset content-specific state
    contentItems.value = {};
    isLoading.value = false;
    error.value = null;
    currentContentId.value = null;
    
    // Optionally reset content list (usually preserve it)
    if (!preserveContentList) {
      contentList.value = [];
      contentListLoading.value = false;
      contentListError.value = null;
    }
  }

  return {
    // State
    contentItems,
    contentList,
    contentListLoading,
    contentListError,
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
    fetchContentList,
    fetchPackagesForContent,
    setCurrentContentId,
    reset
  };
});