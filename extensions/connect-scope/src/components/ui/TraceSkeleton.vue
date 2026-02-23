<template>
  <div class="space-y-2 mt-4">
    <div v-for="i in 5" :key="i" class="flex items-center gap-2 animate-pulse">
      <div class="w-80 shrink-0 flex items-center gap-2 pl-1">
        <div class="w-3 h-3 bg-gray-200 rounded"></div>
        <div>
          <div class="h-3.5 bg-gray-200 rounded" :style="{ width: `${100 + i * 20}px` }"></div>
          <div class="h-2.5 bg-gray-100 rounded mt-1" style="width: 80px"></div>
        </div>
      </div>
      <div class="flex-1 h-5 bg-gray-100 rounded overflow-hidden">
        <div class="h-full bg-gray-200 rounded" :style="{ width: `${30 + i * 12}%` }"></div>
      </div>
      <div class="w-16 h-3 bg-gray-200 rounded shrink-0"></div>
    </div>
  </div>
</template>
