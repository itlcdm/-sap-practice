<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "../components/Icon.vue";
import { createCompany, deleteCompany, listCompanies, testCompanyConnection, updateCompany } from "../services/companiesApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";

const companies = ref([]);
const search = ref("");
const loading = ref(true);
const refreshing = ref(false);
const saving = ref(false);
const error = ref("");
const message = ref("");
const showModal = ref(false);
const editingCompany = ref(null);
const form = ref(emptyForm());
const testingId = ref(null);

function emptyForm() {
  return { name: "", service_layer_url: "", company_db: "", username: "", password: "" };
}

const filteredCompanies = computed(() => {
  const query = search.value.trim().toLowerCase();
  if (!query) return companies.value;
  return companies.value.filter((company) => [company.name, company.company_db, company.username, company.service_layer_url].some((value) => value.toLowerCase().includes(query)));
});

function openCreate() {
  editingCompany.value = null;
  form.value = emptyForm();
  error.value = "";
  showModal.value = true;
}

function openEdit(company) {
  editingCompany.value = company;
  form.value = { name: company.name, service_layer_url: company.service_layer_url, company_db: company.company_db, username: company.username, password: "" };
  error.value = "";
  showModal.value = true;
}

function closeModal() {
  if (!saving.value) showModal.value = false;
}

async function testConnection(company) {
  testingId.value = company.id;
  message.value = "";
  error.value = "";
  try {
    const result = await testCompanyConnection(company.id);
    message.value = `${company.name}: ${result.message}.`;
  } catch (err) {
    error.value = extractErrorMessage(err, `No se pudo conectar con ${company.name}`);
  } finally {
    testingId.value = null;
  }
}

async function loadCompanies() {
  refreshing.value = true;
  error.value = "";
  try { companies.value = await listCompanies(); }
  catch (err) { error.value = extractErrorMessage(err, "No se pudieron cargar las empresas"); }
  finally { loading.value = false; refreshing.value = false; }
}

async function saveCompany() {
  error.value = "";
  if (!form.value.name.trim() || !form.value.service_layer_url.trim() || !form.value.company_db.trim() || !form.value.username.trim() || (!editingCompany.value && !form.value.password.trim())) {
    error.value = "Completa todos los campos obligatorios.";
    return;
  }
  saving.value = true;
  try {
    if (editingCompany.value) {
      await updateCompany(editingCompany.value.id, { ...form.value, password: form.value.password || null, is_active: editingCompany.value.is_active });
      message.value = "Empresa actualizada correctamente.";
    } else {
      await createCompany(form.value);
      message.value = "Empresa registrada correctamente.";
    }
    showModal.value = false;
    await loadCompanies();
  } catch (err) { error.value = extractErrorMessage(err, "No se pudo guardar la empresa"); }
  finally { saving.value = false; }
}

async function removeCompany(company) {
  if (!window.confirm(`¿Eliminar la empresa ${company.name}?`)) return;
  error.value = "";
  try { await deleteCompany(company.id); message.value = "Empresa eliminada correctamente."; await loadCompanies(); }
  catch (err) { error.value = extractErrorMessage(err, "No se pudo eliminar la empresa"); }
}

onMounted(loadCompanies);
</script>

<template>
  <section class="companies-page">
    <header class="page-header">
      <div><h1>Empresas</h1><p class="subtitle">Gestiona las conexiones a SAP Business One</p></div>
      <button class="icon-button primary" type="button" data-tooltip="Nueva Empresa" @click="openCreate"><Icon name="plus" /></button>
    </header>

    <div class="toolbar"><div class="search-box"><span aria-hidden="true">⌕</span><input v-model="search" placeholder="Buscar empresas..." aria-label="Buscar empresas" /></div><button class="icon-button" type="button" :disabled="refreshing" :data-tooltip="refreshing ? 'Actualizando…' : 'Actualizar'" @click="loadCompanies"><Icon name="refresh" /></button></div>
    <p v-if="message" class="alert success">{{ message }}</p><p v-if="error && !showModal" class="alert error">{{ error }}</p>

    <div class="table-card"><p v-if="loading" class="empty-state">Cargando empresas…</p><p v-else-if="!filteredCompanies.length" class="empty-state">No hay empresas registradas.</p><table v-else class="companies-table"><thead><tr><th>Nombre</th><th>Base de datos</th><th>URL Service Layer</th><th>Usuario</th><th>Estado</th><th>Creación</th><th>Acciones</th></tr></thead><tbody><tr v-for="company in filteredCompanies" :key="company.id"><td class="company-name">{{ company.name }}</td><td class="mono">{{ company.company_db }}</td><td class="url-cell" :title="company.service_layer_url">{{ company.service_layer_url }}</td><td>{{ company.username }}</td><td><span class="status active"><span>✓</span> Activa</span></td><td class="date">{{ formatDateTime(company.created_at) }}</td><td class="actions"><button type="button" class="icon-button" :disabled="testingId === company.id" :data-tooltip="testingId === company.id ? 'Probando…' : 'Probar conexión'" @click="testConnection(company)"><Icon name="zap" /></button><button type="button" class="icon-button" data-tooltip="Editar" @click="openEdit(company)"><Icon name="edit" /></button><button type="button" class="icon-button delete" data-tooltip="Eliminar" @click="removeCompany(company)"><Icon name="trash" /></button></td></tr></tbody></table></div>

    <div v-if="showModal" class="modal-backdrop" @click.self="closeModal"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="company-modal-title"><button class="close-button" type="button" aria-label="Cerrar" @click="closeModal">×</button><h2 id="company-modal-title">{{ editingCompany ? "Editar Empresa" : "Nueva Empresa" }}</h2><form @submit.prevent="saveCompany"><label>Nombre de la Empresa<input v-model="form.name" placeholder="Mi Empresa SAP" required autofocus /></label><label>URL Service Layer<input v-model="form.service_layer_url" type="url" placeholder="https://sap-server:50000/b1s/v1" required /></label><label>Base de Datos (CompanyDB)<input v-model="form.company_db" placeholder="SBO_EMPRESA" required /></label><div class="two-columns"><label>Usuario<input v-model="form.username" placeholder="manager" required /></label><label>Contraseña<input v-model="form.password" type="password" :placeholder="editingCompany ? 'Dejar vacío para conservar' : '••••••••'" :required="!editingCompany" /></label></div><p v-if="error && showModal" class="alert error">{{ error }}</p><div class="modal-actions"><button class="cancel-button" type="button" :disabled="saving" @click="closeModal">Cancelar</button><button class="primary-button" type="submit" :disabled="saving">{{ saving ? "Guardando…" : editingCompany ? "Guardar cambios" : "Crear Empresa" }}</button></div></form></section></div>
  </section>
</template>

<style scoped>
.companies-page { display: flex; flex-direction: column; gap: 22px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; flex-wrap: wrap; }h1 { margin: 0 0 4px; font-size: 24px; font-weight: 650; }.subtitle { color: var(--text); }
.primary-button, .cancel-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 42px; padding: 0 18px; border: 0; border-radius: 8px; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; }.primary-button { color: #fff; background: #3b96f3; }.cancel-button { color: var(--text-h); background: var(--code-bg); border: 1px solid var(--border); }.primary-button:disabled, .cancel-button:disabled { opacity: .6; cursor: not-allowed; }
.icon-button{position:relative;display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;padding:0;border:1px solid var(--border);border-radius:7px;background:var(--code-bg);color:var(--text-h);cursor:pointer}.icon-button:disabled{opacity:.6;cursor:wait}.icon-button.delete{color:#b42318}.icon-button.primary{width:40px;height:40px;border:0;border-radius:9px;background:var(--accent);color:#fff}.icon-button[data-tooltip]::after{content:attr(data-tooltip);position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%) scale(.96);padding:5px 9px;border-radius:6px;background:#111827;color:#fff;font-size:12px;font-weight:500;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,.2);opacity:0;visibility:hidden;transition:opacity .12s ease,transform .12s ease;pointer-events:none;z-index:5}.icon-button[data-tooltip]:hover::after,.icon-button[data-tooltip]:focus-visible::after{opacity:1;visibility:visible;transform:translateX(-50%) scale(1)}
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 14px; }.search-box { display: flex; align-items: center; gap: 8px; width: min(385px, 100%); height: 46px; padding: 0 14px; box-sizing: border-box; color: #a2acc2; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; }.search-box span { font-size: 24px; line-height: 1; }.search-box input { width: 100%; border: 0; outline: 0; color: var(--text-h); background: transparent; font: inherit; font-size: 14px; }.table-card { overflow-x: auto; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; box-shadow: var(--shadow); }.companies-table { width: 100%; min-width: 1000px; border-collapse: collapse; }.companies-table th, .companies-table td { padding: 17px 16px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }.companies-table th { color: #92a0b9; background: rgba(244, 247, 250, .7); font-size: 12px; font-weight: 650; letter-spacing: .04em; text-transform: uppercase; }.companies-table tbody tr:last-child td { border-bottom: 0; }.company-name { color: #12213e; font-weight: 600; }.mono { font-family: var(--mono); color: #263c66; }.url-cell { max-width: 235px; overflow: hidden; color: #2f5b98; text-overflow: ellipsis; white-space: nowrap; }.date { white-space: nowrap; font-family: var(--mono); color: #33415f; }.status { display: inline-flex; align-items: center; gap: 5px; padding: 7px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; }.status.active { color: #1cb879; background: #e6fbf1; }.actions { display: flex; gap: 8px; white-space: nowrap; }.empty-state { padding: 42px 20px; color: var(--text); text-align: center; }.alert { padding: 12px 16px; border-radius: 8px; font-size: 14px; }.alert.success { color: #067647; background: rgba(6,118,71,.08); }.alert.error { color: #b42318; background: rgba(180,35,24,.08); }
.modal-backdrop { position: fixed; z-index: 20; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(9, 12, 22, .68); }.modal { position: relative; width: min(520px, 100%); max-height: calc(100vh - 40px); overflow-y: auto; box-sizing: border-box; padding: 24px; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 24px 60px rgba(0,0,0,.25); }.modal h2 { margin: 0 0 24px; color: var(--text-h); font-size: 19px; font-weight: 650; }.close-button { position: absolute; top: 12px; right: 14px; border: 0; color: var(--text); background: transparent; font-size: 25px; cursor: pointer; }.modal form { display: flex; flex-direction: column; gap: 17px; }.modal label { display: flex; flex-direction: column; gap: 7px; color: #5e6981; font-size: 13px; font-weight: 600; }.modal input { width: 100%; box-sizing: border-box; min-height: 48px; padding: 0 15px; color: var(--text-h); background: #f7f9fb; border: 1px solid #dfe5ee; border-radius: 8px; outline: 0; font: inherit; }.modal input:focus { border-color: #4a9af7; box-shadow: 0 0 0 3px rgba(74,154,247,.16); }.two-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 2px; }.modal-actions .primary-button, .modal-actions .cancel-button { min-height: 46px; }
@media (max-width: 680px) { .toolbar { align-items: stretch; flex-direction: column; }.search-box { width: 100%; }.two-columns { grid-template-columns: 1fr; }.modal-actions { justify-content: stretch; }.modal-actions > * { flex: 1; } }
</style>
