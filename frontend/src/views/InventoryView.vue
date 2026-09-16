<script setup>
import { ref, computed, onMounted } from "vue";
import api from "../services/api";

const DETAIL_FIELDS = [
  { key: "ItemsGroupCode", label: "Grupo" },
  { key: "InventoryUOM", label: "Unidad de inventario" },
  { key: "SalesUnit", label: "Unidad de venta" },
  { key: "PurchaseUnit", label: "Unidad de compra" },
  { key: "BarCode", label: "Código de barras" },
  { key: "DefaultWarehouse", label: "Almacén predeterminado" },
];

const itemCode = ref("");
const item = ref(null);
const loading = ref(false);
const error = ref("");
const warehouseNames = ref({});
const saving = ref(false);
const saveError = ref("");
const saveSuccess = ref(false);

onMounted(async () => {
  try {
    const response = await api.get("/api/warehouses");

    warehouseNames.value = Object.fromEntries(
      response.data.map((w) => [w.WarehouseCode, w.WarehouseName])
    );
  } catch (err) {
    console.error("No se pudieron cargar los nombres de bodega", err);
  }
});

const details = computed(() => {
  if (!item.value) return [];

  return DETAIL_FIELDS.map(({ key, label }) => ({
    label,
    value: item.value[key],
  })).filter(
    ({ value }) => value !== null && value !== undefined && value !== ""
  );
});

const isActive = computed(() => {
  const valid = item.value?.Valid;

  if (valid === undefined || valid === null || valid === "") return null;

  return valid === "Y" || valid === "tYES";
});

const warehouseRows = computed(() => {
  const collection = item.value?.ItemWarehouseInfoCollection || [];

  return collection
    .filter((w) => w.InStock || w.Committed || w.Ordered)
    .map((w) => ({
      code: w.WarehouseCode,
      name: warehouseNames.value[w.WarehouseCode] || w.WarehouseCode,
      stock: w.InStock,
      committed: w.Committed,
      ordered: w.Ordered,
      available: w.InStock - w.Committed + w.Ordered,
    }))
    .sort((a, b) => b.stock - a.stock);
});

async function buscarArticulo() {
  if (!itemCode.value.trim()) {
    error.value = "Escribe un código de artículo";
    return;
  }

  loading.value = true;
  error.value = "";
  item.value = null;
  saveError.value = "";
  saveSuccess.value = false;

  try {
    const response = await api.get(
      `/api/items/${itemCode.value.trim()}`
    );

    item.value = response.data;
  } catch (err) {
    console.error(err);

    error.value =
      err.response?.data?.detail ||
      "Error consultando el artículo";
  } finally {
    loading.value = false;
  }
}

async function guardarEnBaseDeDatos() {
  saving.value = true;
  saveError.value = "";
  saveSuccess.value = false;

  try {
    await api.post("/api/inventory/save", {
      codigo_articulo: item.value.ItemCode,
      nombre_articulo: item.value.ItemName || "",
      grupo: String(item.value.ItemsGroupCode ?? ""),
      unidad_venta: item.value.SalesUnit || "",
      unidad_compra: item.value.PurchaseUnit || "",
      almacen_predeterminado: item.value.DefaultWarehouse || "",
      activo: isActive.value ?? true,
      bodegas: warehouseRows.value.map((w) => ({
        codigo_bodega: w.code,
        nombre_bodega: w.name,
        stock: w.stock,
        comprometido: w.committed,
        pedido: w.ordered,
      })),
    });

    saveSuccess.value = true;
  } catch (err) {
    console.error(err);

    saveError.value =
      err.response?.data?.detail ||
      "Error guardando el inventario en la base de datos";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="inventory">
    <header class="page-header">
      <h1>Consulta de inventario</h1>
      <p class="subtitle">Consulta de artículos en SAP Business One</p>
    </header>

    <section class="card search-card">
      <label class="field-label" for="item-code">Código del artículo</label>

      <div class="busqueda">
        <input
          id="item-code"
          v-model="itemCode"
          type="text"
          placeholder="Ej. A00001"
          :disabled="loading"
          @keyup.enter="buscarArticulo"
        />

        <button :disabled="loading" @click="buscarArticulo">
          <span v-if="loading" class="spinner" aria-hidden="true"></span>
          {{ loading ? "Buscando..." : "Buscar" }}
        </button>
      </div>
    </section>

    <p v-if="error" class="alert alert-error">
      {{ error }}
    </p>

    <section v-if="item" class="card result-card">
      <div class="result-header">
        <span class="item-code">{{ item.ItemCode }}</span>

        <span
          v-if="isActive !== null"
          class="badge"
          :class="isActive ? 'badge-active' : 'badge-inactive'"
        >
          {{ isActive ? "Activo" : "Inactivo" }}
        </span>
      </div>

      <p class="item-name">{{ item.ItemName }}</p>

      <dl v-if="details.length" class="detail-grid">
        <template v-for="detail in details" :key="detail.label">
          <dt>{{ detail.label }}</dt>
          <dd>{{ detail.value }}</dd>
        </template>
      </dl>

      <div class="warehouse-section">
        <h3 class="warehouse-title">Inventario por bodega</h3>

        <table v-if="warehouseRows.length" class="preview-table">
          <thead>
            <tr>
              <th>Bodega</th>
              <th>Nombre</th>
              <th>Stock</th>
              <th>Comprometido</th>
              <th>Pedido</th>
              <th>Disponible</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in warehouseRows" :key="row.code">
              <td>{{ row.code }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.stock }}</td>
              <td>{{ row.committed }}</td>
              <td>{{ row.ordered }}</td>
              <td>{{ row.available }}</td>
            </tr>
          </tbody>
        </table>

        <p v-else class="empty-state warehouse-empty">
          Sin existencias registradas en ninguna bodega
        </p>
      </div>

      <div class="save-section">
        <button
          type="button"
          class="save-button"
          :disabled="saving"
          @click="guardarEnBaseDeDatos"
        >
          <span v-if="saving" class="spinner" aria-hidden="true"></span>
          {{ saving ? "Guardando..." : "Guardar en base de datos" }}
        </button>

        <p v-if="saveSuccess" class="alert alert-success">
          Inventario guardado correctamente
        </p>

        <p v-if="saveError" class="alert alert-error">
          {{ saveError }}
        </p>
      </div>
    </section>

    <p v-else-if="!loading && !error" class="empty-state">
      Escribe un código de artículo para comenzar
    </p>
  </section>
</template>

<style scoped>
.inventory {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 4px;
}

.subtitle {
  color: var(--text);
}

.card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 24px;
  text-align: left;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-h);
  margin-bottom: 8px;
}

.busqueda {
  display: flex;
  gap: 12px;
}

input {
  flex: 1;
  padding: 12px 14px;
  font-size: 16px;
  font-family: var(--sans);
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text-h);
}

input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  font-size: 16px;
  font-weight: 500;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}

button:hover:not(:disabled) {
  opacity: 0.9;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.alert {
  padding: 14px 16px;
  border-radius: 8px;
  font-size: 15px;
}

.alert-error {
  color: #b42318;
  background: rgba(180, 35, 24, 0.08);
  border: 1px solid rgba(180, 35, 24, 0.25);
}

.alert-success {
  color: #067647;
  background: rgba(6, 118, 71, 0.08);
  border: 1px solid rgba(6, 118, 71, 0.25);
}

.save-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

.save-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-h);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.save-button:hover:not(:disabled) {
  border-color: var(--accent);
}

.save-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.save-section .alert {
  margin-top: 12px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.item-code {
  font-family: var(--mono);
  font-size: 20px;
  font-weight: 600;
  color: var(--text-h);
}

.badge {
  font-size: 13px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 999px;
}

.badge-active {
  color: #067647;
  background: rgba(6, 118, 71, 0.1);
}

.badge-inactive {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.12);
}

.item-name {
  margin-top: 4px;
  color: var(--text);
}

.detail-grid {
  margin: 20px 0 0;
  display: grid;
  grid-template-columns: max-content 1fr;
  column-gap: 20px;
  row-gap: 10px;
}

.detail-grid dt {
  color: var(--text);
  font-size: 14px;
}

.detail-grid dd {
  margin: 0;
  color: var(--text-h);
  font-size: 14px;
  text-align: right;
}

.empty-state {
  text-align: center;
  color: var(--text);
  padding: 20px 0;
}

.warehouse-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

.warehouse-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-h);
  margin: 0 0 12px;
}

.warehouse-empty {
  padding: 0;
  text-align: left;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
}

.preview-table th {
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.preview-table td {
  font-size: 14px;
  color: var(--text-h);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}

.preview-table td:nth-child(n + 3) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.preview-table tbody tr:last-child td {
  border-bottom: none;
}
</style>
