<script setup>
import { reactive } from "vue";
import { useRoute } from "vue-router";
import { useAuth } from "../composables/useAuth";
import Icon from "../components/Icon.vue";

const { logout } = useAuth();
const route = useRoute();

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/empresas", label: "Empresas", icon: "company" },
  {
    label: "Gestión de Tareas",
    icon: "folder",
    children: [
      { to: "/inventario", label: "Consulta de inventario", icon: "inventory" },
      { to: "/tareas", label: "Reporteria Automatica", icon: "catalog" },
      { to: "/tareas/monedas", label: "Cambio de monedas", icon: "currency" },
      { to: "/tareas/llamadas-servicio", label: "Llamada de Servicios", icon: "call" },
    ],
  },
  { to: "/programaciones", label: "Tareas programadas", icon: "schedule" },
  {
    to: "/ejecuciones/en-curso",
    label: "Ejecuciones en curso",
    icon: "running",
    dividerBefore: true,
  },
  {
    to: "/ejecuciones/historial",
    label: "Historial de ejecuciones",
    icon: "history",
  },
  {
    to: "/configuracion",
    label: "Configuración",
    icon: "settings",
    dividerBefore: true,
  },
];

const expandedGroups = reactive({});
for (const item of NAV_ITEMS) {
  if (item.children) {
    expandedGroups[item.label] = item.children.some((child) => route.path.startsWith(child.to));
  }
}

function toggleGroup(label) {
  expandedGroups[label] = !expandedGroups[label];
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">SP</span>
        <span class="brand-name">SAP Practice</span>
      </div>

      <nav class="nav">
        <template v-for="item in NAV_ITEMS" :key="item.label || item.to">
          <div v-if="item.dividerBefore" class="nav-divider" />

          <template v-if="item.children">
            <button
              type="button"
              class="nav-link nav-group-toggle"
              :class="{ 'group-active': item.children.some((child) => route.path.startsWith(child.to)) }"
              @click="toggleGroup(item.label)"
            >
              <Icon :name="item.icon" />
              <span>{{ item.label }}</span>
              <Icon name="chevron-down" class="chevron" :class="{ open: expandedGroups[item.label] }" />
            </button>
            <div v-show="expandedGroups[item.label]" class="nav-subgroup">
              <router-link v-for="child in item.children" :key="child.to" :to="child.to" class="nav-link nav-sublink">
                <Icon :name="child.icon" />
                <span>{{ child.label }}</span>
              </router-link>
            </div>
          </template>

          <router-link v-else :to="item.to" class="nav-link">
            <Icon :name="item.icon" />
            <span>{{ item.label }}</span>
          </router-link>
        </template>
      </nav>

      <button class="logout-button" @click="logout">
        <Icon name="logout" />
        <span>Cerrar sesión</span>
      </button>
    </aside>

    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex: 1;
  min-height: 0;
}

.sidebar {
  --sb-bg: #111827;
  --sb-border: rgba(255, 255, 255, 0.08);
  --sb-text: #9ca3af;
  --sb-text-strong: #f3f4f6;
  --sb-accent: #60a5fa;
  --sb-accent-bg: rgba(96, 165, 250, 0.14);

  width: 252px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--sb-bg);
  border-right: 1px solid var(--sb-border);
  padding: 20px 14px;
  box-sizing: border-box;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 6px 24px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: linear-gradient(135deg, #60a5fa, #2563eb);
  color: #fff;
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.brand-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--sb-text-strong);
  white-space: nowrap;
}

.nav {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-divider {
  height: 1px;
  margin: 10px 10px;
  background: var(--sb-border);
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--sb-text);
  text-decoration: none;
  transition: background-color 0.15s, color 0.15s;
}

.nav-link .icon {
  opacity: 0.75;
  transition: opacity 0.15s, color 0.15s;
}

.nav-link:hover {
  color: var(--sb-text-strong);
  background: rgba(255, 255, 255, 0.06);
}

.nav-link:hover .icon {
  opacity: 0.9;
}

.nav-link.router-link-exact-active {
  color: #fff;
  background: var(--sb-accent-bg);
}

.nav-link.router-link-exact-active .icon {
  opacity: 1;
  color: var(--sb-accent);
}

.nav-link.router-link-exact-active::before {
  content: "";
  position: absolute;
  left: -14px;
  top: 4px;
  bottom: 4px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--sb-accent);
}

.nav-group-toggle {
  width: 100%;
  border: none;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}

.nav-group-toggle.group-active {
  color: var(--sb-text-strong);
}

.chevron {
  margin-left: auto;
  width: 14px;
  height: 14px;
  opacity: 0.6;
  transition: transform 0.15s;
}

.chevron.open {
  transform: rotate(180deg);
}

.nav-subgroup {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 18px;
}

.nav-sublink {
  font-size: 13px;
}

.logout-button {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  padding: 9px 10px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--sb-text);
  background: transparent;
  border: 1px solid var(--sb-border);
  border-radius: 8px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background-color 0.15s;
}

.logout-button:hover {
  color: var(--sb-text-strong);
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.04);
}

.content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 36px 42px 48px;
  box-sizing: border-box;
  text-align: left;
}

@media (max-width: 720px) {
  .shell {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--sb-border);
  }

  .brand {
    padding-bottom: 16px;
  }

  .nav {
    flex-direction: row;
    flex-wrap: wrap;
    overflow: visible;
    gap: 6px;
  }

  .nav-divider {
    width: 1px;
    height: 20px;
    margin: 0 4px;
  }

  .nav-link.router-link-exact-active::before {
    display: none;
  }

  .content {
    padding: 24px 20px 32px;
  }
}
</style>
