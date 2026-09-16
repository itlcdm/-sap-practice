<script setup>
import { useAuth } from "./composables/useAuth";
import LoginView from "./components/LoginView.vue";
import AppLayout from "./layouts/AppLayout.vue";

const { isAuthenticated } = useAuth();
</script>

<template>
  <LoginView v-if="!isAuthenticated" />
  <AppLayout v-else />
</template>
