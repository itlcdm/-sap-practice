<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import PlaceholderView from "../components/PlaceholderView.vue";

const route = useRoute();
const isEdit = computed(() => Boolean(route.params.id));
</script>

<template>
  <PlaceholderView
    :title="isEdit ? 'Editar tarea' : 'Crear tarea'"
    description="Formulario para definir los datos de la tarea."
  />
</template>
