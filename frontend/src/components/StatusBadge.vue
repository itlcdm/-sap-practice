<script setup>
import { computed } from "vue";

const props = defineProps({
  status: { type: String, required: true },
});

const LABELS = {
  running: "En curso",
  success: "Exitosa",
  failed: "Fallida",
  active: "Activa",
  inactive: "Inactiva",
  scheduled: "Programada",
  manual: "Manual",
};

const label = computed(() => LABELS[props.status] || props.status);
</script>

<template>
  <span class="badge" :class="`badge-${status}`">{{ label }}</span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

.badge-success,
.badge-active {
  color: #067647;
  background: rgba(6, 118, 71, 0.1);
}

.badge-failed {
  color: #b42318;
  background: rgba(180, 35, 24, 0.08);
}

.badge-running {
  color: #b45309;
  background: rgba(180, 83, 9, 0.1);
}

.badge-inactive {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.12);
}

.badge-scheduled,
.badge-manual {
  color: var(--accent);
  background: var(--accent-bg);
}
</style>
