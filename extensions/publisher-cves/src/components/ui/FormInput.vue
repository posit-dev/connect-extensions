<script setup lang="ts">
import { ref } from "vue";

defineProps<{
  placeholder?: string;
  disabled?: boolean;
  buttonText?: string;
  loadingText?: string;
  isLoading?: boolean;
}>();

const emit = defineEmits<{
  (e: "submit", value: string): void;
}>();

const inputValue = ref("");

function handleSubmit(event: Event) {
  event.preventDefault();
  emit("submit", inputValue.value.trim());
}
</script>

<template>
  <form @submit="handleSubmit" class="flex flex-col md:flex-row gap-3">
    <input
      v-model="inputValue"
      type="text"
      :placeholder="placeholder || 'Enter value'"
      class="flex-1 p-2 border border-gray-300 rounded text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
      :disabled="disabled || isLoading"
    />

    <button
      type="submit"
      class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="disabled || isLoading"
    >
      <span v-if="isLoading" class="flex items-center justify-center">
        <span
          class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-[var(--animate-spin)] mr-2"
        ></span>
        {{ loadingText || "Loading..." }}
      </span>
      <span v-else>{{ buttonText || "Submit" }}</span>
    </button>
  </form>
</template>
