<script setup>
import { onMounted, ref } from "vue";
import {
  getAppSettings,
  updateAppSettings,
  getMailSettings,
  updateMailSettings,
  sendTestEmail,
  listSqlConnections,
  createSqlConnection,
  updateSqlConnection,
  deleteSqlConnection,
  getAuthInfo,
  getPostgresSettings,
} from "../services/settingsApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";
import Icon from "../components/Icon.vue";

const loading = ref(true);
const error = ref("");

const sqlConnections = ref([]);
const authInfo = ref(null);
const postgres = ref(null);

const appForm = ref({ timezone_offset_hours: -5, default_batch_size: 20, max_retry_attempts: 5 });
const appSavedAt = ref(null);
const savingApp = ref(false);
const appError = ref("");

const mailForm = ref({ smtp_server: "", smtp_port: 587, mail_user: "", mail_from: "", mail_password: "" });
const mailPasswordConfigured = ref(false);
const savingMail = ref(false);
const mailError = ref("");
const mailSaved = ref(false);

const testEmailTo = ref("");
const sendingTest = ref(false);
const testResult = ref("");
const testError = ref("");

const showConnectionForm = ref(false);
const editingConnection = ref(null);
const connectionForm = ref(emptyConnectionForm());
const savingConnection = ref(false);
const connectionError = ref("");

const TIMEZONE_OPTIONS = [
  { value: -6, label: "UTC-06:00" },
  { value: -5, label: "UTC-05:00 (Panamá)" },
  { value: -4, label: "UTC-04:00" },
];

function emptyConnectionForm() {
  return {
    name: "",
    driver: "ODBC Driver 17 for SQL Server",
    server: "",
    database: "",
    username: "",
    password: "",
    extra_params: "TrustServerCertificate=yes;",
  };
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [appSettings, mailSettings, connections, auth, postgresSettings] = await Promise.all([
      getAppSettings(),
      getMailSettings(),
      listSqlConnections(),
      getAuthInfo(),
      getPostgresSettings(),
    ]);
    appForm.value = {
      timezone_offset_hours: appSettings.timezone_offset_hours,
      default_batch_size: appSettings.default_batch_size,
      max_retry_attempts: appSettings.max_retry_attempts,
    };
    appSavedAt.value = appSettings.updated_at;
    mailForm.value = {
      smtp_server: mailSettings.smtp_server,
      smtp_port: mailSettings.smtp_port,
      mail_user: mailSettings.mail_user,
      mail_from: mailSettings.mail_from,
      mail_password: "",
    };
    mailPasswordConfigured.value = mailSettings.password_configured;
    sqlConnections.value = connections;
    authInfo.value = auth;
    postgres.value = postgresSettings;
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo cargar la configuración");
  } finally {
    loading.value = false;
  }
}

async function saveAppSettings() {
  savingApp.value = true;
  appError.value = "";
  try {
    const result = await updateAppSettings(appForm.value);
    appSavedAt.value = result.updated_at;
  } catch (err) {
    appError.value = extractErrorMessage(err, "No se pudieron guardar los parámetros");
  } finally {
    savingApp.value = false;
  }
}

async function saveMailSettings() {
  savingMail.value = true;
  mailError.value = "";
  mailSaved.value = false;
  try {
    const result = await updateMailSettings(mailForm.value);
    mailPasswordConfigured.value = result.password_configured;
    mailForm.value.mail_password = "";
    mailSaved.value = true;
  } catch (err) {
    mailError.value = extractErrorMessage(err, "No se pudieron guardar los datos de correo");
  } finally {
    savingMail.value = false;
  }
}

async function testEmail() {
  if (!testEmailTo.value) return;
  sendingTest.value = true;
  testResult.value = "";
  testError.value = "";
  try {
    await sendTestEmail(testEmailTo.value);
    testResult.value = `Correo de prueba enviado a ${testEmailTo.value}.`;
  } catch (err) {
    testError.value = extractErrorMessage(err, "No se pudo enviar el correo de prueba");
  } finally {
    sendingTest.value = false;
  }
}

function openCreateConnection() {
  editingConnection.value = null;
  connectionForm.value = emptyConnectionForm();
  connectionError.value = "";
  showConnectionForm.value = true;
}

function openEditConnection(conn) {
  editingConnection.value = conn;
  connectionForm.value = {
    name: conn.name,
    driver: conn.driver,
    server: conn.server,
    database: conn.database,
    username: conn.username,
    password: "",
    extra_params: conn.extra_params,
  };
  connectionError.value = "";
  showConnectionForm.value = true;
}

function closeConnectionForm() {
  showConnectionForm.value = false;
}

async function saveConnection() {
  savingConnection.value = true;
  connectionError.value = "";
  try {
    if (editingConnection.value) {
      await updateSqlConnection(editingConnection.value.id, {
        driver: connectionForm.value.driver,
        server: connectionForm.value.server,
        database: connectionForm.value.database,
        username: connectionForm.value.username,
        password: connectionForm.value.password || null,
        extra_params: connectionForm.value.extra_params,
      });
    } else {
      await createSqlConnection(connectionForm.value);
    }
    sqlConnections.value = await listSqlConnections();
    showConnectionForm.value = false;
  } catch (err) {
    connectionError.value = extractErrorMessage(err, "No se pudo guardar la conexión");
  } finally {
    savingConnection.value = false;
  }
}

async function removeConnection(conn) {
  if (!confirm(`¿Eliminar la conexión "${conn.name}"?`)) return;
  try {
    await deleteSqlConnection(conn.id);
    sqlConnections.value = await listSqlConnections();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo eliminar la conexión");
  }
}

onMounted(load);
</script>

<template>
  <section class="page-view">
    <header class="page-header">
      <div>
        <h1>Configuración</h1>
        <p class="subtitle">Ajustes generales del sistema de tareas.</p>
      </div>
    </header>

    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="loading" class="empty-state">Cargando…</p>

    <template v-else>
      <section class="card">
        <h2>Notificaciones por correo</h2>
        <p class="hint">Se usan para enviar los resúmenes de cada carga y reporte.</p>
        <div class="form-grid">
          <label>Servidor SMTP<input v-model="mailForm.smtp_server" /></label>
          <label>Puerto<input v-model.number="mailForm.smtp_port" type="number" min="1" max="65535" /></label>
          <label>Usuario<input v-model="mailForm.mail_user" /></label>
          <label>Remitente<input v-model="mailForm.mail_from" /></label>
          <label>
            Contraseña
            <input
              v-model="mailForm.mail_password"
              type="password"
              :placeholder="mailPasswordConfigured ? 'Configurada (dejar en blanco para mantener)' : 'Sin configurar'"
            />
          </label>
        </div>
        <div class="save-row">
          <button type="button" class="button primary" :disabled="savingMail" @click="saveMailSettings">
            {{ savingMail ? "Guardando…" : "Guardar cambios" }}
          </button>
          <span v-if="mailSaved" class="success-text">Guardado.</span>
        </div>
        <p v-if="mailError" class="alert">{{ mailError }}</p>

        <div class="test-email">
          <input v-model="testEmailTo" type="email" placeholder="correo@ejemplo.com" />
          <button type="button" class="button" :disabled="sendingTest || !testEmailTo" @click="testEmail">
            {{ sendingTest ? "Enviando…" : "Enviar correo de prueba" }}
          </button>
        </div>
        <p v-if="testResult" class="success-text">{{ testResult }}</p>
        <p v-if="testError" class="alert">{{ testError }}</p>
      </section>

      <section class="card">
        <div class="card-header">
          <h2>Conexiones SQL Server</h2>
          <button type="button" class="icon-button primary" data-tooltip="Nueva conexión" @click="openCreateConnection">
            <Icon name="plus" />
          </button>
        </div>
        <p v-if="!sqlConnections.length" class="empty-state">No hay conexiones configuradas.</p>
        <table v-else class="table">
          <thead>
            <tr><th>Nombre</th><th>Servidor</th><th>Base de datos</th><th>Usuario</th><th>Contraseña</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="conn in sqlConnections" :key="conn.id">
              <td>{{ conn.name }}</td>
              <td>{{ conn.server }}</td>
              <td>{{ conn.database }}</td>
              <td>{{ conn.username }}</td>
              <td>
                <strong :class="conn.password_configured ? 'ok' : 'warn'">
                  {{ conn.password_configured ? "Configurada" : "No configurada" }}
                </strong>
              </td>
              <td class="actions">
                <button type="button" class="icon-button" data-tooltip="Editar" @click="openEditConnection(conn)">
                  <Icon name="edit" />
                </button>
                <button type="button" class="icon-button delete" data-tooltip="Eliminar" @click="removeConnection(conn)">
                  <Icon name="trash" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="card">
        <h2>Base de datos de la aplicación (PostgreSQL)</h2>
        <p class="hint">
          Solo lectura: esta conexión se necesita para poder leer la configuración de la base de datos,
          así que debe permanecer en el .env del servidor.
        </p>
        <div class="info-grid">
          <div class="info-item"><span>Host</span><strong>{{ postgres.host }}</strong></div>
          <div class="info-item"><span>Puerto</span><strong>{{ postgres.port }}</strong></div>
          <div class="info-item"><span>Base de datos</span><strong>{{ postgres.database }}</strong></div>
          <div class="info-item"><span>Usuario</span><strong>{{ postgres.user }}</strong></div>
          <div class="info-item">
            <span>Contraseña</span>
            <strong :class="postgres.password_configured ? 'ok' : 'warn'">
              {{ postgres.password_configured ? "Configurada" : "No configurada" }}
            </strong>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>Parámetros de tareas</h2>
        <p class="hint">
          Zona horaria usada para el etiquetado de cargas, y valores por defecto de Llamada de Servicios.
        </p>
        <div class="form-grid">
          <label>
            Zona horaria
            <select v-model.number="appForm.timezone_offset_hours">
              <option v-for="tz in TIMEZONE_OPTIONS" :key="tz.value" :value="tz.value">{{ tz.label }}</option>
            </select>
          </label>
          <label>
            Tamaño de lote por defecto
            <input v-model.number="appForm.default_batch_size" type="number" min="1" max="50" />
          </label>
          <label>
            Máximo de reintentos por elemento
            <input v-model.number="appForm.max_retry_attempts" type="number" min="1" max="20" />
          </label>
        </div>
        <div class="save-row">
          <button type="button" class="button primary" :disabled="savingApp" @click="saveAppSettings">
            {{ savingApp ? "Guardando…" : "Guardar cambios" }}
          </button>
          <span v-if="appSavedAt" class="hint">Última actualización: {{ formatDateTime(appSavedAt) }}</span>
        </div>
        <p v-if="appError" class="alert">{{ appError }}</p>
      </section>

      <section class="card">
        <h2>Autenticación</h2>
        <div class="info-grid">
          <div class="info-item">
            <span>Estado</span>
            <strong :class="authInfo.enabled ? 'ok' : 'warn'">
              {{ authInfo.enabled ? "Habilitada" : "Deshabilitada" }}
            </strong>
          </div>
        </div>
        <p class="hint">{{ authInfo.note }}</p>
      </section>
    </template>

    <div v-if="showConnectionForm" class="backdrop">
      <form class="modal" @submit.prevent="saveConnection">
        <h2>{{ editingConnection ? "Editar conexión" : "Nueva conexión SQL Server" }}</h2>

        <label>Nombre<input v-model="connectionForm.name" :disabled="!!editingConnection" required /></label>
        <label>Driver ODBC<input v-model="connectionForm.driver" required /></label>

        <div class="grid">
          <label>Servidor<input v-model="connectionForm.server" required /></label>
          <label>Base de datos<input v-model="connectionForm.database" required /></label>
        </div>

        <div class="grid">
          <label>Usuario<input v-model="connectionForm.username" required /></label>
          <label>
            Contraseña
            <input
              v-model="connectionForm.password"
              type="password"
              :placeholder="editingConnection ? 'Dejar en blanco para mantener' : ''"
              :required="!editingConnection"
            />
          </label>
        </div>

        <label>Parámetros adicionales<input v-model="connectionForm.extra_params" /></label>

        <p v-if="connectionError" class="alert">{{ connectionError }}</p>

        <div class="modal-actions">
          <button type="button" class="button" @click="closeConnectionForm">Cancelar</button>
          <button type="submit" class="button primary" :disabled="savingConnection">
            {{ savingConnection ? "Guardando…" : "Guardar" }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.page-view { display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
h1 { font-size: 24px; margin: 0 0 4px; }
.subtitle { color: var(--text); }
.card { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); padding: 20px 24px; overflow-x: auto; }
.card h2 { margin: 0 0 6px; font-size: 17px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.card-header h2 { margin: 0; }
.hint { margin: 0 0 14px; color: var(--text); font-size: 12px; }
.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 4px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-item span { color: var(--text); font-size: 12px; }
.info-item strong { color: var(--text-h); font-size: 14px; }
strong.ok { color: #067647; }
strong.warn { color: #b45309; }
.test-email { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
.test-email input { flex: 1; min-width: 220px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 7px; background: var(--code-bg); color: var(--text-h); }
.form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }
.form-grid label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text); }
.form-grid input, .form-grid select { padding: 8px 10px; border: 1px solid var(--border); border-radius: 7px; background: var(--code-bg); color: var(--text-h); font-size: 14px; }
.save-row { display: flex; align-items: center; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
.button { padding: 9px 14px; border-radius: 7px; border: 1px solid var(--border); color: var(--text-h); background: var(--code-bg); cursor: pointer; font-size: 13px; white-space: nowrap; }
.button.primary { color: #fff; background: var(--accent); border-color: var(--accent); }
.button:disabled { opacity: 0.6; cursor: wait; }
.table { width: 100%; border-collapse: collapse; min-width: 640px; }
.table th, .table td { padding: 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
.table th { color: var(--text); font-size: 12px; text-transform: uppercase; }
.table tr:last-child td { border-bottom: 0; }
.table .actions { display: flex; gap: 6px; }
.alert { padding: 12px 16px; color: #b42318; background: rgba(180,35,24,.08); border-radius: 8px; margin-top: 10px; }
.success-text { color: #067647; font-size: 13px; }
.empty-state { padding: 12px 0; color: var(--text); text-align: center; }

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
  cursor: pointer;
}
.icon-button.primary { color: var(--accent); border-color: var(--accent-border); }
.icon-button.delete { color: #b42318; }

.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 50;
}
.modal {
  background: var(--bg);
  border-radius: 12px;
  padding: 24px;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: var(--shadow);
}
.modal h2 { margin: 0; font-size: 18px; }
.modal label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--text); }
.modal input { padding: 8px 10px; border: 1px solid var(--border); border-radius: 7px; background: var(--code-bg); color: var(--text-h); font-size: 14px; }
.modal input:disabled { opacity: 0.6; }
.modal .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
</style>
