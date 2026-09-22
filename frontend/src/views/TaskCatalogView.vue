<script setup>
import { onMounted, ref } from "vue";
import Icon from "../components/Icon.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { createTask, deleteTask, getTask, listTasks, runTask, updateTask } from "../services/tasksApi";
import { extractErrorMessage } from "../utils/format";

const tasks = ref([]);
const loading = ref(true);
const saving = ref(false);
const runningId = ref(null);
const error = ref("");
const message = ref("");
const showForm = ref(false);
const editingTask = ref(null);
const form = ref(emptyForm());

function emptyForm() {
  return {
    name: "",
    description: "",
    connection_name: "InventarioDb",
    mail_to: "",
    mail_cc: "",
    mail_subject_template: "",
    is_active: true,
    reports: [{ stored_procedure: "", excel_file_name: "", sheet_name: "" }],
  };
}

function addReport() {
  form.value.reports.push({ stored_procedure: "", excel_file_name: "", sheet_name: "" });
}

function removeReport(index) {
  if (form.value.reports.length > 1) form.value.reports.splice(index, 1);
}

async function load() {
  loading.value = true;
  error.value = "";

  try {
    tasks.value = await listTasks();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudieron cargar las tareas");
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingTask.value = null;
  form.value = emptyForm();
  error.value = "";
  showForm.value = true;
}

async function openEdit(task) {
  error.value = "";

  try {
    const full = await getTask(task.id);
    editingTask.value = full;
    form.value = {
      ...full,
      description: full.description || "",
      mail_cc: full.mail_cc || "",
      mail_subject_template: full.mail_subject_template || "",
      reports: full.reports.map(({ stored_procedure, excel_file_name, sheet_name }) => ({
        stored_procedure,
        excel_file_name,
        sheet_name,
      })),
    };
    showForm.value = true;
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo cargar la tarea");
  }
}

async function save() {
  error.value = "";

  if (!form.value.name.trim() || !form.value.connection_name.trim() || !form.value.mail_to.trim()) {
    error.value = "Completa el nombre, la conexión y el destinatario principal.";
    return;
  }

  if (form.value.reports.some((r) => !r.stored_procedure || !r.excel_file_name || !r.sheet_name)) {
    error.value = "Completa todos los campos de cada reporte.";
    return;
  }

  saving.value = true;
  const payload = {
    ...form.value,
    description: form.value.description || null,
    mail_cc: form.value.mail_cc || null,
    mail_subject_template: form.value.mail_subject_template || null,
  };

  try {
    if (editingTask.value) {
      await updateTask(editingTask.value.id, payload);
      message.value = "Tarea actualizada correctamente.";
    } else {
      await createTask(payload);
      message.value = "Tarea creada correctamente.";
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
    await deleteTask(task.id);
    message.value = "Tarea eliminada.";
    await load();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo eliminar la tarea");
  }
}

async function run(task) {
  runningId.value = task.id;
  error.value = "";
  message.value = "";

  try {
    const { execution_id } = await runTask(task.id);
    message.value = `Ejecución #${execution_id} de "${task.name}" iniciada.`;
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo ejecutar la tarea");
  } finally {
    runningId.value = null;
  }
}

onMounted(load);
</script>

<template>
  <section class="catalog-page">
    <header class="page-header">
      <div>
        <h1>Reportería Automática</h1>
        <p class="subtitle">Tareas configuradas para generar y enviar reportes</p>
      </div>

      <div class="header-actions">
        <button
          type="button"
          class="icon-button"
          :disabled="loading"
          :data-tooltip="loading ? 'Actualizando…' : 'Actualizar'"
          @click="load"
        >
          <Icon name="refresh" />
        </button>
        <button type="button" class="icon-button primary" data-tooltip="Nueva tarea" @click="openCreate">
          <Icon name="plus" />
        </button>
      </div>
    </header>

    <p v-if="message" class="alert success">{{ message }}</p>
    <p v-if="error" class="alert error">{{ error }}</p>

    <div class="card">
      <p v-if="loading" class="empty">Cargando tareas…</p>
      <p v-else-if="!tasks.length" class="empty">No hay tareas creadas todavía.</p>

      <table v-else class="table">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Descripción</th>
            <th>Programación</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id">
            <td class="strong">
              <span
                class="status-dot"
                :class="task.is_active ? 'active' : 'inactive'"
                :data-tooltip="task.is_active ? 'Activa' : 'Inactiva'"
              ></span>
              {{ task.name }}
            </td>
            <td>{{ task.description || "—" }}</td>
            <td>
              <StatusBadge v-if="task.has_schedule" status="scheduled" />
              <span v-else class="muted">Sin programar</span>
            </td>
            <td class="actions">
              <button
                type="button"
                class="icon-button"
                :disabled="runningId === task.id"
                :data-tooltip="runningId === task.id ? 'Ejecutando…' : 'Ejecutar ahora'"
                @click="run(task)"
              >
                <Icon name="play" />
              </button>
              <button type="button" class="icon-button" data-tooltip="Editar" @click="openEdit(task)">
                <Icon name="edit" />
              </button>
              <router-link class="icon-button" :to="`/tareas/${task.id}/programar`" data-tooltip="Programar">
                <Icon name="schedule" />
              </router-link>
              <button type="button" class="icon-button delete" data-tooltip="Eliminar" @click="remove(task)">
                <Icon name="trash" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="backdrop">
      <form class="modal" @submit.prevent="save">
        <h2>{{ editingTask ? "Editar tarea" : "Nueva tarea" }}</h2>

        <label>Nombre<input v-model="form.name" placeholder="Inventario diario" required /></label>
        <label>Conexión SQL Server<input v-model="form.connection_name" required /></label>
        <label>Descripción<textarea v-model="form.description" rows="2" /></label>

        <div class="grid">
          <label>Para<input v-model="form.mail_to" type="email" required placeholder="equipo@empresa.com" /></label>
          <label>CC<input v-model="form.mail_cc" placeholder="opcional" /></label>
        </div>

        <label>
          Asunto del correo
          <input v-model="form.mail_subject_template" placeholder="Reportes {task_name} - {timestamp}" />
        </label>

        <fieldset class="reports-fieldset">
          <legend>
            Reportes
            <button type="button" class="add-report" @click="addReport">+ Agregar reporte</button>
          </legend>

          <div v-for="(report, index) in form.reports" :key="index" class="report-row">
            <input v-model="report.stored_procedure" required placeholder="Stored procedure" />
            <input v-model="report.excel_file_name" required placeholder="Archivo.xlsx" />
            <input v-model="report.sheet_name" required placeholder="Hoja" />
            <button
              type="button"
              class="icon-button delete"
              :disabled="form.reports.length === 1"
              data-tooltip="Quitar"
              @click="removeReport(index)"
            >
              <Icon name="trash" />
            </button>
          </div>
        </fieldset>

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
.catalog-page {
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

.card {
  overflow: auto;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 8px 24px;
}

.table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 13px 10px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.table th {
  color: var(--text);
  font-size: 12px;
  text-transform: uppercase;
}

.table tr:last-child td {
  border-bottom: 0;
}

.strong {
  color: var(--text-h);
  font-weight: 600;
}

.muted {
  color: var(--text);
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 8px;
  white-space: nowrap;
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

.icon-button.primary {
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 9px;
  background: var(--accent);
  color: #fff;
}

.icon-button[data-tooltip]::after,
.status-dot[data-tooltip]::after {
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
.icon-button[data-tooltip]:focus-visible::after,
.status-dot[data-tooltip]:hover::after {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) scale(1);
}

.status-dot {
  position: relative;
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-right: 8px;
  border-radius: 50%;
  vertical-align: middle;
}

.status-dot.active {
  background: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.15);
}

.status-dot.inactive {
  background: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.15);
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
  width: min(640px, 100%);
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
select,
textarea {
  box-sizing: border-box;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--bg);
  color: var(--text-h);
  font: inherit;
}

textarea {
  resize: vertical;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.reports-fieldset {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 14px;
}

.reports-fieldset legend {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.add-report {
  border: 0;
  background: none;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.report-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 8px;
  align-items: center;
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
  .grid,
  .report-row {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
