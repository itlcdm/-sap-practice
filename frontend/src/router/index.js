import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/dashboard",
    name: "dashboard",
    component: () => import("../views/DashboardView.vue"),
  },
  {
    path: "/inventario",
    name: "inventory",
    component: () => import("../views/InventoryView.vue"),
  },
  {
    path: "/tareas",
    name: "task-catalog",
    component: () => import("../views/TaskCatalogView.vue"),
  },
  {
    path: "/tareas/nueva",
    name: "task-create",
    component: () => import("../views/TaskFormView.vue"),
  },
  {
    path: "/tareas/:id/editar",
    name: "task-edit",
    component: () => import("../views/TaskFormView.vue"),
    props: true,
  },
  {
    path: "/tareas/:id/programar",
    name: "task-schedule",
    component: () => import("../views/TaskScheduleView.vue"),
    props: true,
  },
  {
    path: "/programaciones",
    name: "schedules",
    component: () => import("../views/SchedulesView.vue"),
  },
  {
    path: "/ejecuciones/en-curso",
    name: "executions-running",
    component: () => import("../views/RunningExecutionsView.vue"),
  },
  {
    path: "/ejecuciones/historial",
    name: "executions-history",
    component: () => import("../views/ExecutionHistoryView.vue"),
  },
  {
    path: "/ejecuciones/:id",
    name: "execution-detail",
    component: () => import("../views/ExecutionDetailView.vue"),
    props: true,
  },
  {
    path: "/configuracion",
    name: "settings",
    component: () => import("../views/SettingsView.vue"),
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
