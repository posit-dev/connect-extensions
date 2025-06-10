import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface ContentListItem {
  guid: string;
  title: string;
  app_mode?: string;
  content_url?: string;
  dashboard_url?: string;
  name?: string;
  description?: string;
  last_deployed_time?: string;
  py_version?: string;
  r_version?: string;
}

export const useContentStore = defineStore("content", () => {
  const contentList = ref<ContentListItem[]>([]);
  const isLoading = ref(false);
  const error = ref<Error | null>(null);
  const currentContentId = ref<string>();

  // Track if content has been loaded
  const isContentLoaded = ref(false);

  // Get the current content item
  const currentContent = computed(() => {
    if (!currentContentId.value) return null;
    return (
      contentList.value.find(
        (content) => content.guid === currentContentId.value
      ) || null
    );
  });

  // Fetch all available content items
  async function fetchContentList() {
    // Skip if content is already loaded
    if (isContentLoaded.value && contentList.value.length > 0) return;

    isLoading.value = true;
    error.value = null;

    try {
      const response = await fetch("/api/content");

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      contentList.value = data;
      isContentLoaded.value = true;
    } catch (err) {
      console.error("Error fetching content list:", err);
      error.value = err as Error;
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    // State
    contentList,
    isLoading,
    error,
    currentContentId,
    isContentLoaded,

    // Computed getters
    currentContent,

    // Actions
    fetchContentList,
  };
});
