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

    <template v-else-if="name === 'company'">
      <rect x="4" y="4" width="16" height="17" rx="1.5" />
      <path d="M8 21V8h8v13M8 11H5M8 15H5M16 11h3M16 15h3M11 11h2M11 15h2" />
      <path d="M9 4 12 2l3 2" />
    </template>

    <template v-else-if="name === 'catalog'">
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path
        d="M9 1.5h6a1 1 0 0 1 1 1V4a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V2.5a1 1 0 0 1 1-1Z"
      />
      <path d="M8 10h8M8 13.5h8M8 17h5" />
    </template>

    <template v-else-if="name === 'currency'">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 6v12M15 8.5c-.7-.7-1.7-1-3-1-1.7 0-3 .8-3 2s1.3 2 3 2 3 .8 3 2-1.3 2-3 2c-1.3 0-2.3-.3-3-1" />
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

    <template v-else-if="name === 'play'">
      <circle cx="12" cy="12" r="9" />
      <path d="M10 8.5 15.5 12 10 15.5Z" />
    </template>

    <template v-else-if="name === 'edit'">
      <path d="M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17v3Z" />
      <path d="M14 6.5 17.5 10" />
    </template>

    <template v-else-if="name === 'plus'">
      <path d="M12 5v14M5 12h14" />
    </template>

    <template v-else-if="name === 'refresh'">
      <path d="M20 11A8 8 0 0 0 6.3 6.3L4 8.5" />
      <path d="M4 4v4.5h4.5" />
      <path d="M4 13a8 8 0 0 0 13.7 4.7L20 15.5" />
      <path d="M20 20v-4.5h-4.5" />
    </template>

    <template v-else-if="name === 'zap'">
      <path d="M13 2 4 14h6l-1 8 9-12h-6Z" />
    </template>

    <template v-else-if="name === 'call'">
      <path
        d="M5 4h3l1.5 4-2 1.5a11 11 0 0 0 5 5l1.5-2 4 1.5v3a1.5 1.5 0 0 1-1.6 1.5A16.5 16.5 0 0 1 3.5 5.6 1.5 1.5 0 0 1 5 4Z"
      />
    </template>

    <template v-else-if="name === 'folder'">
      <path d="M4 6.5A1.5 1.5 0 0 1 5.5 5H10l2 2.5h6.5A1.5 1.5 0 0 1 20 9v9.5A1.5 1.5 0 0 1 18.5 20h-13A1.5 1.5 0 0 1 4 18.5Z" />
    </template>

    <template v-else-if="name === 'chevron-down'">
      <path d="M6 9l6 6 6-6" />
    </template>

    <template v-else-if="name === 'trash'">
      <path d="M4 7h16" />
      <path d="M9 7V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V7" />
      <path d="M6 7l1 13a1.5 1.5 0 0 0 1.5 1.4h7A1.5 1.5 0 0 0 17 20l1-13" />
      <path d="M10 11v6M14 11v6" />
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
