import { defineStore } from "pinia";
import { computed, ref } from "vue";
import type { ContentItem } from "../types";
import { apiBase } from "../api";
import { useUserStore } from "./user";

export type OwnerFilter = "mine" | "all";

export const useContentStore = defineStore("content", () => {
  const items = ref<ContentItem[]>([]);
  const selectedContent = ref<ContentItem | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const search = ref("");
  const ownerFilter = ref<OwnerFilter>("mine");

  const filteredItems = computed(() => {
    const userStore = useUserStore();
    let result = items.value;

    if (ownerFilter.value === "mine" && userStore.user?.guid) {
      result = result.filter((item) => item.owner_guid === userStore.user!.guid);
    }

    const query = search.value.trim().toLowerCase();
    if (query) {
      result = result.filter((item) => {
        const title = (item.title || "").toLowerCase();
        const name = item.name.toLowerCase();
        const ownerUsername = (item.owner?.username || "").toLowerCase();
        return (
          title.includes(query) ||
          name.includes(query) ||
          ownerUsername.includes(query)
        );
      });
    }

    return result;
  });

  async function fetchContent() {
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

  return {
    items,
    selectedContent,
    isLoading,
    error,
    search,
    ownerFilter,
    filteredItems,
    fetchContent,
    selectContent,
    clearSelection,
  };
});
