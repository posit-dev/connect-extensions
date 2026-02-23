<script setup lang="ts">
import type { FlatSpan } from "../types";
import { formatDuration } from "../utils/formatting";
import { otlpValue } from "../utils/trace-builder";

defineProps<{
  span: FlatSpan;
  showName?: boolean;
}>();
</script>

<template>
  <div class="mt-1.5 px-2 py-2 bg-gray-50 border border-gray-100 rounded text-xs">
    <p v-if="showName" class="font-mono font-medium text-gray-700 mb-1.5 truncate">{{ span.name }}</p>

    <!-- Timing -->
    <table class="w-full mb-2">
      <tbody>
        <tr v-if="span.durationMs != null" class="align-top">
          <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">duration</td>
          <td class="pb-0.5 text-gray-700 font-mono break-all">{{ formatDuration(span.durationMs) }}</td>
        </tr>
        <tr v-if="span.selfTimeMs != null" class="align-top">
          <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">self time</td>
          <td class="pb-0.5 text-gray-700 font-mono break-all">{{ formatDuration(span.selfTimeMs) }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Attributes -->
    <table v-if="span.attributes.length" class="w-full mb-2">
      <tbody>
        <tr v-for="attr in span.attributes" :key="attr.key" class="align-top">
          <td class="pr-4 pb-0.5 text-gray-400 font-mono whitespace-nowrap">{{ attr.key }}</td>
          <td class="pb-0.5 text-gray-700 font-mono break-all">{{ otlpValue(attr.value) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="text-gray-400 mb-2">No attributes</p>

    <!-- Error details -->
    <template v-if="span.statusMessage || span.exception">
      <p class="text-gray-600 font-medium mb-1">
        {{ span.exception?.type ?? 'Error' }}: {{ span.statusMessage ?? span.exception?.message }}
      </p>
      <pre v-if="span.exception?.stacktrace"
           class="text-gray-500 whitespace-pre-wrap break-all bg-white border border-gray-100 rounded p-2 max-h-40 overflow-y-auto leading-relaxed">{{ span.exception.stacktrace }}</pre>
    </template>
  </div>
</template>
