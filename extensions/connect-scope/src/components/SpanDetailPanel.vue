<script setup lang="ts">
import type { FlatSpan } from "../types";
import { formatDuration } from "../utils/formatting";
import { otlpValue } from "../utils/trace-builder";

defineProps<{
  span: FlatSpan;
  showName?: boolean;
}>();

defineEmits<{
  close: [];
}>();
</script>

<template>
  <div class="relative mt-1.5 px-2 py-2 bg-gray-50 border border-gray-100 rounded text-xs">
    <button
      class="absolute top-1.5 right-1.5 w-5 h-5 flex items-center justify-center rounded text-gray-400 hover:text-gray-600 hover:bg-gray-200 transition-colors"
      title="Close"
      @click.stop="$emit('close')"
    >&times;</button>

    <p v-if="showName" class="font-mono font-medium text-gray-700 mb-1.5 truncate pr-6">{{ span.name }}</p>

    <table class="w-full mb-2">
      <tbody>
        <tr v-if="span.durationMs != null" class="align-top">
          <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">duration</td>
          <td class="pb-0.5 text-gray-700 font-mono break-all">{{ formatDuration(span.durationMs) }}</td>
        </tr>
        <tr v-for="attr in span.attributes" :key="attr.key" class="align-top">
          <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">{{ attr.key }}</td>
          <td class="pb-0.5 text-gray-700 font-mono break-all">{{ otlpValue(attr.value) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!span.attributes.length && span.durationMs == null" class="text-gray-400 mb-2">No attributes</p>

    <!-- Error details -->
    <template v-if="span.statusMessage || span.exception">
      <div class="mt-1 border border-red-100 bg-red-50 rounded p-2">
        <p class="font-mono font-medium text-red-700 mb-1">
          {{ span.exception?.type ?? 'Error' }}
        </p>
        <p v-if="span.statusMessage || span.exception?.message"
           class="text-red-600 whitespace-pre-wrap break-words mb-1">{{ span.statusMessage ?? span.exception?.message }}</p>
        <pre v-if="span.exception?.stacktrace"
             class="text-gray-600 whitespace-pre-wrap break-all bg-white border border-red-100 rounded p-2 mt-1.5 max-h-60 overflow-y-auto leading-relaxed font-mono">{{ span.exception.stacktrace }}</pre>
      </div>
    </template>
  </div>
</template>
