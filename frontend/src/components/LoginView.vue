<script setup>
import { ref } from "vue";
import { useAuth } from "../composables/useAuth";

const { login } = useAuth();

const email = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

async function handleSubmit() {
  if (!email.value.trim() || !password.value.trim()) {
    error.value = "Escribe tu correo y contraseña";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    await login(email.value.trim(), password.value);
  } catch (err) {
    error.value =
      err.response?.data?.detail || "Error al iniciar sesión";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-main">
    <header class="page-header">
      <h1>SAP Inventory Explorer</h1>
      <p class="subtitle">Inicia sesión para continuar</p>
    </header>

    <form class="card login-card" @submit.prevent="handleSubmit">
      <label class="field-label" for="login-email">Correo</label>

      <input
        id="login-email"
        v-model="email"
        type="email"
        placeholder="admin@empresa.com"
        autocomplete="username"
        :disabled="loading"
      />

      <label class="field-label" for="login-password">Contraseña</label>

      <input
        id="login-password"
        v-model="password"
        type="password"
        placeholder="••••••••"
        autocomplete="current-password"
        :disabled="loading"
      />

      <p v-if="error" class="alert alert-error">
        {{ error }}
      </p>

      <button type="submit" :disabled="loading">
        <span v-if="loading" class="spinner" aria-hidden="true"></span>
        {{ loading ? "Verificando..." : "Iniciar sesión" }}
      </button>
    </form>
  </main>
</template>

<style scoped>
.login-main {
  max-width: 400px;
  margin: 0 auto;
  padding: 96px 20px 40px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 24px;
}

.page-header {
  text-align: center;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 4px;
  white-space: nowrap;
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

.login-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-h);
  margin-top: 12px;
  margin-bottom: 8px;
}

.field-label:first-child {
  margin-top: 0;
}

input {
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
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 20px;
  font-size: 16px;
  font-weight: 500;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  cursor: pointer;
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
  margin-top: 8px;
  padding: 14px 16px;
  border-radius: 8px;
  font-size: 15px;
}

.alert-error {
  color: #b42318;
  background: rgba(180, 35, 24, 0.08);
  border: 1px solid rgba(180, 35, 24, 0.25);
}
</style>
