<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { getCurrencyExecution } from "../services/currencyTasksApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";
import StatusBadge from "../components/StatusBadge.vue";

const route = useRoute();
const execution = ref(null);
const loading = ref(true);
const error = ref("");

const parsedRates = computed(() => {
  return (execution.value?.updated_rates || []).map((entry) => {
    const [pair, rate] = entry.split(":").map((part) => part.trim());
    return { pair, rate: rate ?? "—" };
  });
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    execution.value = await getCurrencyExecution(route.params.id);
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo cargar la ejecución");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="detail-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">CAMBIO DE MONEDA · EJECUCIÓN #{{ route.params.id }}</p>
        <h1>{{ execution?.task_name || "Detalle de ejecución" }}</h1>
        <p class="subtitle">Estado y resultado de la actualización de tasas de cambio.</p>
      </div>
      <router-link class="button secondary" to="/ejecuciones/historial">Volver al historial</router-link>
    </header>

    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="loading" class="empty-state">Cargando detalle…</p>

    <template v-else-if="execution">
      <div class="summary-grid">
        <div class="summary-item"><span>Estado</span><StatusBadge :status="execution.status" /></div>
        <div class="summary-item"><span>Filial</span><strong>{{ execution.company_name }}</strong></div>
        <div class="summary-item">
          <span>Disparador</span>
          <strong>{{ execution.trigger_type === "scheduled" ? "Programada" : "Manual" }}</strong>
        </div>
        <div class="summary-item"><span>Inicio</span><strong>{{ formatDateTime(execution.started_at) }}</strong></div>
        <div class="summary-item"><span>Finalización</span><strong>{{ formatDateTime(execution.finished_at) }}</strong></div>
      </div>

      <p v-if="execution.error_message" class="alert">{{ execution.error_message }}</p>

      <section class="card">
        <h2>Tasas actualizadas</h2>
        <p v-if="!parsedRates.length" class="empty-state">No se actualizó ninguna moneda en esta ejecución.</p>
        <table v-else class="table">
          <thead>
            <tr><th>Par de monedas</th><th>Tasa</th></tr>
          </thead>
          <tbody>
            <tr v-for="(rate, index) in parsedRates" :key="index">
              <td>{{ rate.pair }}</td>
              <td>{{ rate.rate }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
</template>

<style scoped>
.detail-view { display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.eyebrow { margin: 0 0 4px; color: var(--accent); font-size: 11px; letter-spacing: .08em; }
h1 { font-size: 24px; margin: 0 0 4px; }
.subtitle { color: var(--text); }
.summary-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.summary-item, .card { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; box-shadow: var(--shadow); }
.summary-item { display: flex; flex-direction: column; gap: 7px; padding: 16px; }
.summary-item span { color: var(--text); font-size: 12px; }
.summary-item strong { color: var(--text-h); font-size: 14px; }
.card { padding: 20px; overflow-x: auto; }
.card h2 { margin: 0 0 14px; font-size: 17px; }
.table { width: 100%; border-collapse: collapse; min-width: 320px; }
.table th, .table td { padding: 11px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
.table th { color: var(--text); font-size: 12px; text-transform: uppercase; }
.table tr:last-child td { border-bottom: 0; }
.button { padding: 9px 14px; border-radius: 7px; color: var(--text-h); background: var(--code-bg); border: 1px solid var(--border); text-decoration: none; font-size: 13px; white-space: nowrap; }
.alert { padding: 12px 16px; color: #b42318; background: rgba(180,35,24,.08); border-radius: 8px; }
.empty-state { color: var(--text); text-align: center; padding: 16px 0; }
@media (max-width: 800px) { .summary-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .summary-grid { grid-template-columns: 1fr; } }
</style>
