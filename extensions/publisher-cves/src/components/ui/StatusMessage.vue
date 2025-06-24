<script setup lang="ts">
defineProps<{
  type: "error" | "warning" | "success" | "info";
  message: string;
  details?: string;
}>();
</script>

<template>
  <div
    class="p-4 rounded-md border-l-4 mb-4"
    :class="{
      'bg-red-50 border-red-500 text-red-700': type === 'error',
      'bg-yellow-50 border-yellow-400 text-yellow-800': type === 'warning',
      'bg-green-50 border-green-500 text-green-700': type === 'success',
      'bg-blue-50 border-blue-500 text-blue-700': type === 'info',
    }"
  >
    <p class="font-medium">{{ message }}</p>
    <p v-if="details" class="mt-1 text-sm opacity-80">{{ details }}</p>
    <slot></slot>
  </div>
</template>
