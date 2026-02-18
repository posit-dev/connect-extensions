<script setup lang="ts">
import { onMounted } from "vue";
import LoadingSpinner from "./components/ui/LoadingSpinner.vue";
import { useUserStore } from "./stores/user";

const userStore = useUserStore();

onMounted(() => {
  userStore.fetchCurrentUser();
});
</script>

<template>
  <div class="flex flex-col min-h-svh bg-gray-100">
    <header class="bg-white border-b border-gray-200 px-6 py-4">
      <h1 class="text-xl font-semibold text-gray-800">Connect Scope</h1>
    </header>

    <main class="flex-1 p-6">
      <LoadingSpinner
        v-if="userStore.isLoading"
        message="Loading..."
        class="mt-16"
      />

      <div v-else-if="userStore.error" class="text-red-600 text-sm">
        {{ userStore.error }}
      </div>

      <div v-else-if="userStore.user" class="max-w-2xl mx-auto">
        <p class="text-gray-600">
          Welcome, {{ userStore.user.first_name || userStore.user.username }}.
        </p>
      </div>
    </main>
  </div>
</template>
