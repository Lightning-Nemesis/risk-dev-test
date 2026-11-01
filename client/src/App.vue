<script setup>
import { onMounted, ref } from 'vue'
import { getObservations, getOptions } from './api.js'
import ObservationForm from './components/ObservationForm.vue'
import ObservationGraph from './components/ObservationGraph.vue'
import ObservationTable from './components/ObservationTable.vue'

const title = import.meta.env.VITE_APP_TITLE
const options = ref({ categories: [], items: [], states: [], cities: [] })
// The table shows only the newest observations, so reloading after each save or delete stays fast however many there
// are (the graphs get their own grouped data from the server). The server also sends the total number
const RECENT_LIMIT = 200
const observations = ref([])
const observationTotal = ref(0)
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
  const data = await getObservations(RECENT_LIMIT)
  observations.value = data.observations
  observationTotal.value = data.total
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
  <header class="hero">
    <div class="hero-inner">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span>Beneficient</div>
      <p class="eyebrow">Data entry</p>
      <h1>{{ title }}</h1>
      <p class="subtitle">Record prices as you observe them and see how they move across items, states and cities.</p>
    </div>
  </header>

  <main class="layout">
    <p v-if="errorMessage" class="alert" role="alert">{{ errorMessage }}</p>
    <ObservationForm v-model:date="selectedDate" :options="options" @changed="reloadObservations" />
    <div class="results">
      <ObservationGraph v-model:date="selectedDate" :observations="observations" />
      <ObservationTable :observations="observations" :total="observationTotal" :items="options.items" />
    </div>
  </main>
</template>
