<script setup lang="ts">
defineProps<{
  hasError: boolean;
  errorMessage?: string;
}>();

defineEmits<{
  retry: [];
}>();
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 text-center">
    <template v-if="hasError">
      <!-- Error icon -->
      <svg class="w-10 h-10 text-red-400 mb-3" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
      </svg>
      <h3 class="text-sm font-medium text-gray-700 mb-1">Failed to load traces</h3>
      <p v-if="errorMessage" class="text-xs text-gray-500 mb-3 max-w-xs">{{ errorMessage }}</p>
      <button
        class="px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
        @click="$emit('retry')"
      >Retry</button>
    </template>
    <template v-else>
      <!-- Empty icon -->
      <svg class="w-10 h-10 text-gray-300 mb-3" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm4.75 9.5a.75.75 0 000 1.5h1.5a.75.75 0 000-1.5h-1.5zM7.5 15a.75.75 0 01.75-.75h3.5a.75.75 0 010 1.5h-3.5A.75.75 0 017.5 15zm.75-5.75a.75.75 0 000 1.5h3.5a.75.75 0 000-1.5h-3.5z" clip-rule="evenodd" />
      </svg>
      <h3 class="text-sm font-medium text-gray-700 mb-1">No trace data available</h3>
      <p class="text-xs text-gray-500 max-w-xs">This job has not produced any OpenTelemetry trace data. Ensure the application is instrumented with OTLP tracing.</p>
    </template>
  </div>
</template>
