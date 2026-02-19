import { defineStore } from "pinia";
import { ref } from "vue";
import { apiBase } from "../api";

interface User {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
}

export const useUserStore = defineStore("user", () => {
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchCurrentUser() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await fetch(`${apiBase}/api/user`);
      if (!response.ok) throw new Error("Failed to fetch user");
      user.value = await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Unknown error";
    } finally {
      isLoading.value = false;
    }
  }

  return { user, isLoading, error, fetchCurrentUser };
});
