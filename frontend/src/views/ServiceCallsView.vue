<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { listCompanies } from "../services/companiesApi";
import {
  getServiceCallExecution,
  listServiceCallExecutionItems,
  listServiceCallExecutions,
  retryFailedItems,
} from "../services/serviceCallExecutionsApi";
import {
  createServiceCallTask,
  deleteServiceCallTask,
  listServiceCallTasks,
  previewServiceCallTask,
  runServiceCallTask,
  updateServiceCallTask,
} from "../services/serviceCallTasksApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";

const tasks = ref([]);
const companies = ref([]);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const message = ref("");

const activeTaskId = ref(null);
const preview = ref(null);
const previewLoading = ref(false);
const previewError = ref("");

const showForm = ref(false);
const editingTask = ref(null);
const form = ref(emptyForm());

const executions = ref([]);
const executionsLoading = ref(false);
const running = ref(false);
const expandedExecutionId = ref(null);
const expandedItems = ref([]);
const expandedItemsLoading = ref(false);
let pollTimer = null;

const activeTask = computed(() => tasks.value.find((t) => t.id === activeTaskId.value) || null);
const hasRunningExecution = computed(() => executions.value.some((e) => e.status === "running"));

const WEEKDAYS = [
  { value: "mon", label: "Lun" },
  { value: "tue", label: "Mar" },
  { value: "wed", label: "Mié" },
  { value: "thu", label: "Jue" },
  { value: "fri", label: "Vie" },
  { value: "sat", label: "Sáb" },
  { value: "sun", label: "Dom" },
];

function emptyForm() {
  return {
    name: "",
    company_id: "",
    connection_name: "InventarioDb",
    source_view: "",
    run_at: "08:00",
    schedule_type: "weekly",
    run_days: ["mon", "tue", "wed", "thu", "fri"],
    run_day_of_month: 1,
    mail_to: "",
    mail_cc: "",
    is_active: true,
  };
}

function describeRunDays(task) {
  if (task.schedule_type === "monthly") {
    return `Día ${task.run_day_of_month} de cada mes`;
  }

  const labels = WEEKDAYS.filter((d) => task.run_days.includes(d.value)).map((d) => d.label);
  return labels.length === 7 ? "Todos los días" : labels.join(", ");
}

async function load() {
  loading.value = true;
  error.value = "";

  try {
    [tasks.value, companies.value] = await Promise.all([listServiceCallTasks(), listCompanies()]);

    if (!tasks.value.some((t) => t.id === activeTaskId.value)) {
      activeTaskId.value = tasks.value[0]?.id ?? null;
    }
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudieron cargar las tareas de llamadas de servicio");
  } finally {
    loading.value = false;
  }
}

async function loadPreview() {
  if (!activeTaskId.value) {
    preview.value = null;
    return;
  }

  previewLoading.value = true;
  previewError.value = "";

  try {
    preview.value = await previewServiceCallTask(activeTaskId.value);
  } catch (err) {
    preview.value = null;
    previewError.value = extractErrorMessage(err, "No se pudo consultar la vista de origen");
  } finally {
    previewLoading.value = false;
  }
}

async function loadExecutions() {
  if (!activeTaskId.value) {
    executions.value = [];
    return;
  }

  executionsLoading.value = true;

  try {
    executions.value = await listServiceCallExecutions(activeTaskId.value, { limit: 5 });
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo cargar el historial de cargas");
  } finally {
    executionsLoading.value = false;
  }
}

function ensurePolling() {
  if (pollTimer) return;

  pollTimer = window.setInterval(() => {
    if (hasRunningExecution.value) {
      loadExecutions();
    } else {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  }, 4000);
}

watch(activeTaskId, () => {
  loadPreview();
  loadExecutions();
  expandedExecutionId.value = null;
});

async function runNow() {
  if (!activeTask.value) return;

  running.value = true;
  error.value = "";
  message.value = "";

  try {
    const { execution_id } = await runServiceCallTask(activeTask.value.id);
    message.value = `Carga #${execution_id} de "${activeTask.value.name}" iniciada.`;
    await loadExecutions();
    ensurePolling();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo iniciar la carga");
  } finally {
    running.value = false;
  }
}

async function retryFailed(execution) {
  error.value = "";

  try {
    await retryFailedItems(execution.id);
    message.value = `Reintentando los registros fallidos de la carga #${execution.id}.`;
    await loadExecutions();
    ensurePolling();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo reintentar la carga");
  }
}

async function toggleExpand(execution) {
  if (expandedExecutionId.value === execution.id) {
    expandedExecutionId.value = null;
    return;
  }

  expandedExecutionId.value = execution.id;
  expandedItemsLoading.value = true;

  try {
    const result = await listServiceCallExecutionItems(execution.id, { status: "needs_review", limit: 50 });
    const failedResult =
      result.items.length < 50
        ? await listServiceCallExecutionItems(execution.id, { status: "failed", limit: 50 - result.items.length })
        : { items: [] };
    expandedItems.value = [...result.items, ...failedResult.items];
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudieron cargar los detalles de la carga");
  } finally {
    expandedItemsLoading.value = false;
  }
}

onUnmounted(() => {
  if (pollTimer) window.clearInterval(pollTimer);
});

function openCreate() {
  editingTask.value = null;
  form.value = { ...emptyForm(), company_id: companies.value[0]?.id || "" };
  error.value = "";
  showForm.value = true;
}

function openEdit(task) {
  editingTask.value = task;
  form.value = {
    name: task.name,
    company_id: task.company_id,
    connection_name: task.connection_name,
    source_view: task.source_view,
    run_at: String(task.run_at).slice(0, 5),
    schedule_type: task.schedule_type,
    run_days: task.run_days.length ? [...task.run_days] : ["mon", "tue", "wed", "thu", "fri"],
    run_day_of_month: task.run_day_of_month || 1,
    mail_to: task.mail_to,
    mail_cc: task.mail_cc || "",
    is_active: task.is_active,
  };
  error.value = "";
  showForm.value = true;
}

async function save() {
  if (!form.value.name || !form.value.company_id || !form.value.source_view || !form.value.mail_to) {
    error.value = "Completa nombre, filial, vista de origen y destinatario.";
    return;
  }

  if (form.value.schedule_type === "weekly" && !form.value.run_days.length) {
    error.value = "Selecciona al menos un día de la semana.";
    return;
  }

  if (form.value.schedule_type === "monthly" && !form.value.run_day_of_month) {
    error.value = "Selecciona el día del mes.";
    return;
  }

  saving.value = true;
  error.value = "";

  try {
    const payload = { ...form.value, company_id: Number(form.value.company_id), mail_cc: form.value.mail_cc || null };

    if (editingTask.value) {
      await updateServiceCallTask(editingTask.value.id, payload);
      message.value = "Tarea actualizada.";
    } else {
      const created = await createServiceCallTask(payload);
      activeTaskId.value = created.id;
      message.value = "Tarea creada.";
    }

    showForm.value = false;
    await load();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo guardar la tarea");
  } finally {
    saving.value = false;
  }
}

async function remove(task) {
  if (!window.confirm(`¿Eliminar la tarea "${task.name}"?`)) return;

  error.value = "";

  try {
    await deleteServiceCallTask(task.id);
    message.value = "Tarea eliminada.";
    await load();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo eliminar la tarea");
  }
}

onMounted(async () => {
  await load();
  await loadPreview();
  await loadExecutions();
  ensurePolling();
});
</script>

<template>
  <section class="service-calls-page">
    <header class="page-header">
      <div>
        <h1>Llamada de Servicios</h1>
        <p class="subtitle">Vista previa de las llamadas de servicio a cargar en SAP por Service Layer</p>
      </div>

      <div class="header-actions">
        <button type="button" class="icon-button" :disabled="loading" :data-tooltip="loading ? 'Actualizando…' : 'Actualizar'" @click="load">
          <Icon name="refresh" />
        </button>
        <button type="button" class="icon-button primary" data-tooltip="Nueva tarea" @click="openCreate">
          <Icon name="plus" />
        </button>
      </div>
    </header>

    <p v-if="message" class="alert success">{{ message }}</p>
    <p v-if="error" class="alert error">{{ error }}</p>

    <p v-if="loading" class="empty">Cargando tareas…</p>

    <template v-else-if="!tasks.length">
      <div class="card"><p class="empty">No hay tareas de llamadas de servicio configuradas.</p></div>
    </template>

    <template v-else>
      <div class="tabs">
        <button
          v-for="task in tasks"
          :key="task.id"
          type="button"
          class="tab"
          :class="{ active: task.id === activeTaskId }"
          @click="activeTaskId = task.id"
        >
          <span class="status-dot" :class="task.is_active ? 'active' : 'inactive'"></span>
          {{ task.name }}
        </button>
      </div>

      <div v-if="activeTask" class="card">
        <div class="tab-toolbar">
          <div class="tab-meta">
            <strong>{{ activeTask.company_name }}</strong>
            <span class="muted">
              {{ activeTask.source_view }} · {{ describeRunDays(activeTask) }} · {{ activeTask.run_at }}
            </span>
          </div>

          <div class="tab-total" v-if="preview">
            <strong>{{ preview.total_count }}</strong> {{ preview.total_count === 1 ? "registro" : "registros" }}
          </div>

          <div class="tab-actions">
            <button
              type="button"
              class="icon-button accent"
              :disabled="running || hasRunningExecution"
              :data-tooltip="hasRunningExecution ? 'Ya hay una carga en curso' : 'Cargar a SAP'"
              @click="runNow"
            >
              <Icon name="zap" />
            </button>
            <button type="button" class="icon-button" :disabled="previewLoading" data-tooltip="Refrescar listado" @click="loadPreview">
              <Icon name="refresh" />
            </button>
            <button type="button" class="icon-button" data-tooltip="Editar" @click="openEdit(activeTask)">
              <Icon name="edit" />
            </button>
            <button type="button" class="icon-button delete" data-tooltip="Eliminar" @click="remove(activeTask)">
              <Icon name="trash" />
            </button>
          </div>
        </div>

        <p v-if="previewLoading" class="empty">Consultando la vista de origen…</p>
        <p v-else-if="previewError" class="alert error">{{ previewError }}</p>
        <p v-else-if="!preview?.rows?.length" class="empty">La vista no devolvió filas.</p>

        <template v-else>
          <p v-if="preview.total_count > preview.rows.length" class="muted truncated-note">
            Mostrando los primeros {{ preview.rows.length }} de {{ preview.total_count }} registros.
          </p>

          <div class="preview-scroll">
          <table class="table">
            <thead>
              <tr>
                <th v-for="column in preview.columns" :key="column">{{ column }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in preview.rows" :key="rowIndex">
                <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell ?? "—" }}</td>
              </tr>
            </tbody>
          </table>
          </div>
        </template>

        <div class="executions-section">
          <h3>Historial de cargas</h3>

          <p v-if="executionsLoading && !executions.length" class="empty">Cargando historial…</p>
          <p v-else-if="!executions.length" class="empty">Todavía no se ha cargado esta tarea a SAP.</p>

          <table v-else class="table executions-table">
            <thead>
              <tr>
                <th>Inicio</th>
                <th>Disparador</th>
                <th>Estado</th>
                <th>Total</th>
                <th>Éxito</th>
                <th>Fallidos</th>
                <th>Revisión</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="execution in executions" :key="execution.id">
                <tr>
                  <td>{{ formatDateTime(execution.started_at) }}</td>
                  <td>
                    {{ execution.trigger_type === "scheduled" ? "Programada" : "Manual" }}
                    <span v-if="execution.dry_run" class="dry-run-tag">Prueba</span>
                  </td>
                  <td><StatusBadge :status="execution.status === 'running' ? 'running' : execution.status === 'failed' ? 'failed' : execution.status === 'completed_with_errors' ? 'failed' : 'success'" /></td>
                  <td>{{ execution.total_items }}</td>
                  <td>{{ execution.successful_items }}</td>
                  <td>{{ execution.failed_items }}</td>
                  <td>{{ execution.review_items }}</td>
                  <td class="actions">
                    <button
                      v-if="(execution.failed_items > 0 || execution.review_items > 0) && execution.status !== 'running'"
                      type="button"
                      class="icon-button"
                      data-tooltip="Reintentar fallidos y en revisión"
                      @click="retryFailed(execution)"
                    >
                      <Icon name="refresh" />
                    </button>
                    <button
                      v-if="execution.failed_items > 0 || execution.review_items > 0"
                      type="button"
                      class="icon-button"
                      :data-tooltip="expandedExecutionId === execution.id ? 'Ocultar detalle' : 'Ver detalle'"
                      @click="toggleExpand(execution)"
                    >
                      <Icon name="edit" />
                    </button>
                  </td>
                </tr>
                <tr v-if="expandedExecutionId === execution.id">
                  <td colspan="8" class="expanded-cell">
                    <p v-if="expandedItemsLoading" class="empty">Cargando detalle…</p>
                    <p v-else-if="!expandedItems.length" class="empty">Sin registros fallidos o por revisar.</p>
                    <ul v-else class="items-list">
                      <li v-for="item in expandedItems" :key="item.id">
                        <StatusBadge :status="item.status === 'needs_review' ? 'scheduled' : 'failed'" />
                        <code>{{ item.payload_json.CustomerCode }} · {{ item.payload_json.ItemCode }}</code>
                        <span class="item-response">{{ item.sap_response || "—" }}</span>
                      </li>
                    </ul>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-if="showForm" class="backdrop">
      <form class="modal" @submit.prevent="save">
        <h2>{{ editingTask ? "Editar tarea" : "Nueva tarea de llamadas de servicio" }}</h2>

        <label>Nombre<input v-model="form.name" placeholder="Llamadas de servicio MEDICA" required /></label>

        <label>
          Filial
          <select v-model="form.company_id" required>
            <option value="" disabled>Selecciona una empresa</option>
            <option v-for="company in companies" :key="company.id" :value="company.id">
              {{ company.name }} · {{ company.company_db }}
            </option>
          </select>
        </label>

        <div class="grid">
          <label>Conexión SQL Server<input v-model="form.connection_name" required /></label>
          <label>Hora de ejecución<input v-model="form.run_at" type="time" required /></label>
        </div>

        <label>
          Vista de origen
          <input v-model="form.source_view" placeholder="[dbo].[V019_LLAMADA_SERVICIOS]" required />
        </label>

        <fieldset class="schedule-type-fieldset">
          <legend>Tipo de programación</legend>
          <label class="choice">
            <input v-model="form.schedule_type" type="radio" value="weekly" /> Días específicos de la semana
          </label>
          <label class="choice">
            <input v-model="form.schedule_type" type="radio" value="monthly" /> Un día específico del mes
          </label>
        </fieldset>

        <fieldset v-if="form.schedule_type === 'weekly'" class="days-fieldset">
          <legend>Días de ejecución</legend>
          <label v-for="day in WEEKDAYS" :key="day.value" class="check">
            <input v-model="form.run_days" type="checkbox" :value="day.value" /> {{ day.label }}
          </label>
        </fieldset>

        <label v-else>
          Día del mes
          <input v-model.number="form.run_day_of_month" type="number" min="1" max="28" required />
          <small>Usa un día entre 1 y 28 para que funcione en todos los meses.</small>
        </label>

        <div class="grid">
          <label>Correo destinatario<input v-model="form.mail_to" type="email" required /></label>
          <label>CC<input v-model="form.mail_cc" placeholder="opcional" /></label>
        </div>

        <label v-if="editingTask" class="check">
          <input v-model="form.is_active" type="checkbox" /> Tarea activa
        </label>

        <div class="modal-actions">
          <button type="button" class="secondary" @click="showForm = false">Cancelar</button>
          <button class="primary-button" :disabled="saving">
            {{ saving ? "Guardando…" : editingTask ? "Guardar cambios" : "Crear tarea" }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.service-calls-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

h1 {
  font-size: 24px;
  margin: 0 0 4px;
}

.subtitle {
  color: var(--text);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border);
  padding-bottom: 2px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 14px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--text);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.tab:hover {
  color: var(--text-h);
}

.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.card {
  overflow: auto;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 20px 24px;
}

.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.tab-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.tab-meta strong {
  color: var(--text-h);
  font-size: 15px;
}

.tab-total {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--code-bg);
  color: var(--text);
  font-size: 13px;
  white-space: nowrap;
}

.tab-total strong {
  color: var(--text-h);
  font-size: 16px;
}

.truncated-note {
  margin: 0 0 10px;
  font-size: 12px;
}

.tab-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.muted {
  color: var(--text);
  font-size: 13px;
}

.preview-scroll {
  overflow: auto;
  max-height: 480px;
}

.table {
  width: 100%;
  min-width: 600px;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  white-space: nowrap;
}

.table th {
  position: sticky;
  top: 0;
  color: var(--text);
  font-size: 12px;
  text-transform: uppercase;
  background: var(--bg);
}

.table tr:last-child td {
  border-bottom: 0;
}

.icon-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--code-bg);
  color: var(--text-h);
  text-decoration: none;
  cursor: pointer;
}

.icon-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.icon-button.delete {
  color: #b42318;
}

.icon-button.accent {
  color: var(--accent);
  border-color: var(--accent-border);
}

.executions-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

.executions-section h3 {
  margin: 0 0 12px;
  font-size: 15px;
  color: var(--text-h);
}

.executions-table {
  min-width: 700px;
}

.dry-run-tag {
  margin-left: 6px;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--code-bg);
  color: var(--text);
  font-size: 11px;
}

.expanded-cell {
  background: var(--code-bg);
  white-space: normal;
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 10px 0;
  list-style: none;
}

.items-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.items-list code {
  color: var(--text-h);
  white-space: nowrap;
}

.item-response {
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
}

.icon-button.primary {
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 9px;
  background: var(--accent);
  color: #fff;
}

.icon-button[data-tooltip]::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%) scale(0.96);
  padding: 5px 9px;
  border-radius: 6px;
  background: #111827;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.12s ease, transform 0.12s ease;
  pointer-events: none;
  z-index: 5;
}

.icon-button[data-tooltip]:hover::after,
.icon-button[data-tooltip]:focus-visible::after {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) scale(1);
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.active {
  background: #16a34a;
}

.status-dot.inactive {
  background: #dc2626;
}

.empty {
  text-align: center;
  color: var(--text);
  padding: 30px;
}

.alert {
  padding: 12px 16px;
  border-radius: 8px;
}

.success {
  color: #067647;
  background: rgba(6, 118, 71, 0.08);
}

.error {
  color: #b42318;
  background: rgba(180, 35, 24, 0.08);
}

.backdrop {
  position: fixed;
  z-index: 20;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(9, 12, 22, 0.65);
}

.modal {
  width: min(560px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  background: var(--bg);
  border-radius: 10px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
}

h2 {
  margin: 0;
  color: var(--text-h);
  font-size: 19px;
}

label,
legend {
  color: var(--text-h);
  font-size: 13px;
  font-weight: 600;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

input,
select {
  box-sizing: border-box;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--bg);
  color: var(--text-h);
  font: inherit;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.check {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 7px;
  font-weight: 400;
}

.check input {
  width: auto;
}

.schedule-type-fieldset {
  display: flex;
  gap: 20px;
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 14px;
}

.choice {
  flex-direction: row;
  align-items: center;
  gap: 7px;
  font-weight: 400;
}

.choice input {
  width: auto;
}

small {
  color: var(--text);
  font-weight: 400;
}

.days-fieldset {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 14px;
}

.days-fieldset .check {
  justify-content: center;
}

@media (max-width: 500px) {
  .days-fieldset {
    grid-template-columns: repeat(4, 1fr);
  }
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.primary-button,
.secondary {
  padding: 9px 13px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--code-bg);
  color: var(--text-h);
  cursor: pointer;
}

.primary-button {
  color: #fff;
  background: var(--accent);
  border: 0;
  font-weight: 600;
}

.primary-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

@media (max-width: 650px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
