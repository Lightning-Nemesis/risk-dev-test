<script setup>
import { onMounted, ref } from 'vue'
import { getObservations, getOptions } from './api.js'
import ObservationForm from './components/ObservationForm.vue'
import ObservationGraph from './components/ObservationGraph.vue'
import ObservationTable from './components/ObservationTable.vue'

const title = import.meta.env.VITE_APP_TITLE
const options = ref({ categories: [], items: [], states: [], cities: [] })
const observations = ref([])
const errorMessage = ref('')
// The form's Date field, shared with the graph ("Average Item Price by City" shows that date). Starts as today
// in the browser's time zone, formatted YYYY-MM-DD for <input type="date">
const now = new Date()
const selectedDate = ref([
  now.getFullYear(),
  String(now.getMonth() + 1).padStart(2, '0'),
  String(now.getDate()).padStart(2, '0'),
].join('-'))

async function loadObservations() {
  observations.value = await getObservations()
}

// After the form saves or deletes observations, reload them so the table and graph show the change
async function reloadObservations() {
  try {
    await loadObservations()
  } catch (error) {
    errorMessage.value = `Could not reload the observations (${error.message})`
  }
}

onMounted(async () => {
  try {
    options.value = await getOptions()
    await loadObservations()
  } catch (error) {
    errorMessage.value = `Could not load data. Is the server running? (${error.message})`
  }
})
</script>

<template>
  <main class="layout">
    <section class="panel">
      <h1>{{ title }}</h1>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <ObservationForm v-model:date="selectedDate" :options="options" @changed="reloadObservations" />
    </section>

    <section class="panel">
      <ObservationGraph v-model:date="selectedDate" :observations="observations" />
      <ObservationTable :observations="observations" />
    </section>
  </main>
</template>
