<script setup>
defineProps({
  name: { type: String, required: true },
});
</script>

<template>
  <svg
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'dashboard'">
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </template>

    <template v-else-if="name === 'inventory'">
      <path d="M12 3 20 7.5V16.5L12 21 4 16.5V7.5Z" />
      <path d="M4 7.5 12 12 20 7.5" />
      <path d="M12 12V21" />
    </template>

    <template v-else-if="name === 'catalog'">
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path
        d="M9 1.5h6a1 1 0 0 1 1 1V4a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V2.5a1 1 0 0 1 1-1Z"
      />
      <path d="M8 10h8M8 13.5h8M8 17h5" />
    </template>

    <template v-else-if="name === 'schedule'">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </template>

    <template v-else-if="name === 'running'">
      <circle cx="12" cy="12" r="9" />
      <path d="M10 8.5 15 12 10 15.5Z" />
    </template>

    <template v-else-if="name === 'history'">
      <path d="M4 4v6h6" />
      <path d="M4.5 10A8 8 0 1 0 6 5" />
    </template>

    <template v-else-if="name === 'settings'">
      <circle cx="12" cy="12" r="3" />
      <path
        d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"
      />
    </template>

    <template v-else-if="name === 'logout'">
      <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" />
      <path d="M16 15l4-3-4-3" />
      <path d="M20 12H9" />
    </template>
  </svg>
</template>

<style scoped>
.icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
</style>
