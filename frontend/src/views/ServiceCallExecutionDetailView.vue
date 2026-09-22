<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import {
  getServiceCallExecution,
  listServiceCallExecutionItems,
  retryFailedItems,
} from "../services/serviceCallExecutionsApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";
import StatusBadge from "../components/StatusBadge.vue";

const route = useRoute();
const execution = ref(null);
const items = ref([]);
const loading = ref(true);
const itemsLoading = ref(false);
const retrying = ref(false);
const error = ref("");

const statusBadge = computed(() => {
  if (!execution.value) return "running";
  if (execution.value.status === "failed" || execution.value.status === "completed_with_errors") return "failed";
  if (execution.value.status === "running") return "running";
  return "success";
});

async function loadItems() {
  itemsLoading.value = true;
  try {
    const limit = Math.max(execution.value?.total_items || 0, 200);
    const result = await listServiceCallExecutionItems(route.params.id, { limit });
    items.value = result.items;
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo cargar el detalle de los elementos");
  } finally {
    itemsLoading.value = false;
  }
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    execution.value = await getServiceCallExecution(route.params.id);
    await loadItems();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo cargar la ejecución");
  } finally {
    loading.value = false;
  }
}

async function retry() {
  retrying.value = true;
  error.value = "";
  try {
    execution.value = await retryFailedItems(route.params.id);
    await loadItems();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo reintentar los elementos");
  } finally {
    retrying.value = false;
  }
}

function itemLabel(item) {
  const payload = item.payload_json || {};
  return [payload.CustomerCode, payload.ItemCode].filter(Boolean).join(" · ") || "—";
}

function shortResponse(item) {
  if (!item.sap_response) return "—";
  const oneLine = item.sap_response.replace(/\s+/g, " ").trim();
  return oneLine.length > 160 ? `${oneLine.slice(0, 160)}…` : oneLine;
}

onMounted(load);
</script>

<template>
  <section class="detail-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">LLAMADA DE SERVICIOS · EJECUCIÓN #{{ route.params.id }}</p>
        <h1>{{ execution?.task_name || "Detalle de ejecución" }}</h1>
        <p class="subtitle">Resultado de la carga de llamadas de servicio hacia SAP Business One.</p>
      </div>
      <router-link class="button secondary" to="/ejecuciones/historial">Volver al historial</router-link>
    </header>

    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="loading" class="empty-state">Cargando detalle…</p>

    <template v-else-if="execution">
      <div class="summary-grid">
        <div class="summary-item"><span>Estado</span><StatusBadge :status="statusBadge" /></div>
        <div class="summary-item">
          <span>Disparador</span>
          <strong>
            {{ execution.trigger_type === "scheduled" ? "Programada" : "Manual" }}
            <small v-if="execution.dry_run">(prueba)</small>
          </strong>
        </div>
        <div class="summary-item"><span>Total</span><strong>{{ execution.total_items }}</strong></div>
        <div class="summary-item"><span>Éxito</span><strong>{{ execution.successful_items }}</strong></div>
        <div class="summary-item"><span>Fallidos</span><strong>{{ execution.failed_items }}</strong></div>
        <div class="summary-item"><span>Revisión</span><strong>{{ execution.review_items }}</strong></div>
        <div class="summary-item"><span>Inicio</span><strong>{{ formatDateTime(execution.started_at) }}</strong></div>
        <div class="summary-item"><span>Finalización</span><strong>{{ formatDateTime(execution.finished_at) }}</strong></div>
      </div>

      <p v-if="execution.error_message" class="alert">{{ execution.error_message }}</p>

      <section class="card">
        <div class="card-header">
          <h2>Elementos</h2>
          <button
            v-if="(execution.failed_items > 0 || execution.review_items > 0) && execution.status !== 'running'"
            type="button"
            class="button secondary"
            :disabled="retrying"
            @click="retry"
          >
            {{ retrying ? "Reintentando…" : "Reintentar fallidos y en revisión" }}
          </button>
        </div>

        <p v-if="itemsLoading" class="empty-state">Cargando elementos…</p>
        <p v-else-if="!items.length" class="empty-state">Sin elementos.</p>
        <div v-else class="table-scroll">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Cliente · Artículo</th>
                <th>Estado</th>
                <th>HTTP</th>
                <th>Respuesta de SAP</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id">
                <td>{{ item.sequence }}</td>
                <td><code>{{ itemLabel(item) }}</code></td>
                <td><StatusBadge :status="item.status === 'succeeded' ? 'success' : item.status === 'needs_review' ? 'scheduled' : 'failed'" /></td>
                <td>{{ item.http_status_code ?? "—" }}</td>
                <td class="response" :title="item.sap_response || ''">{{ shortResponse(item) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
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
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.summary-item, .card { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; box-shadow: var(--shadow); }
.summary-item { display: flex; flex-direction: column; gap: 7px; padding: 16px; }
.summary-item span { color: var(--text); font-size: 12px; }
.summary-item strong { color: var(--text-h); font-size: 14px; }
.summary-item small { color: var(--text); font-weight: 400; }
.card { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; }
.card-header h2 { margin: 0; font-size: 17px; }
.table-scroll { max-height: 460px; overflow-y: auto; overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; min-width: 640px; }
.table th, .table td { padding: 11px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
.table th { position: sticky; top: 0; background: var(--bg); color: var(--text); font-size: 12px; text-transform: uppercase; }
.table tr:last-child td { border-bottom: 0; }
.response { max-width: 360px; white-space: normal; word-break: break-word; color: var(--text); }
.button { padding: 9px 14px; border-radius: 7px; color: var(--text-h); background: var(--code-bg); border: 1px solid var(--border); text-decoration: none; font-size: 13px; cursor: pointer; white-space: nowrap; }
.alert { padding: 12px 16px; color: #b42318; background: rgba(180,35,24,.08); border-radius: 8px; }
.empty-state { color: var(--text); text-align: center; padding: 16px 0; }
@media (max-width: 800px) { .summary-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .summary-grid { grid-template-columns: 1fr; } }
</style>
