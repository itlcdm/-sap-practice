import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/dashboard" },
  {
    path: "/dashboard",
    name: "dashboard",
    component: () => import("../views/DashboardView.vue"),
  },
  {
    path: "/empresas",
    name: "companies",
    component: () => import("../views/CompaniesView.vue"),
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
    path: "/tareas/monedas",
    name: "currency-tasks",
    component: () => import("../views/CurrencyTasksView.vue"),
  },
  {
    path: "/tareas/llamadas-servicio",
    name: "service-call-tasks",
    component: () => import("../views/ServiceCallsView.vue"),
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
    path: "/ejecuciones/moneda/:id",
    name: "currency-execution-detail",
    component: () => import("../views/CurrencyExecutionDetailView.vue"),
    props: true,
  },
  {
    path: "/ejecuciones/llamadas/:id",
    name: "service-call-execution-detail",
    component: () => import("../views/ServiceCallExecutionDetailView.vue"),
    props: true,
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
