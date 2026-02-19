import { defineStore } from "pinia";
import { ref } from "vue";
import type { ContentItem } from "../types";
import { apiBase } from "../api";

export const useContentStore = defineStore("content", () => {
  const items = ref<ContentItem[]>([]);
  const selectedContent = ref<ContentItem | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchContent() {
    if (items.value.length > 0) return;
    isLoading.value = true;
    error.value = null;
    try {
      const response = await fetch(`${apiBase}/api/content`);
      if (!response.ok) throw new Error("Failed to fetch content");
      items.value = await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Unknown error";
    } finally {
      isLoading.value = false;
    }
  }

  function selectContent(item: ContentItem) {
    selectedContent.value = item;
  }

  function clearSelection() {
    selectedContent.value = null;
  }

  return { items, selectedContent, isLoading, error, fetchContent, selectContent, clearSelection };
});
