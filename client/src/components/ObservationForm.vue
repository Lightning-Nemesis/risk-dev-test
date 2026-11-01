<script setup>
import { computed, reactive, watch } from 'vue'
import { createObservation, deleteObservations } from '../api.js'
import { formatDate, formatPrice } from '../format.js'

const props = defineProps({
  options: { type: Object, required: true },
})
// Tells App.vue that observations were saved or deleted, so it reloads the table and graph
const emit = defineEmits(['changed'])
// The Date field lives in App.vue, because the graph uses it too ("Average Item Price by City" shows that date)
const date = defineModel('date', { type: String, required: true })

const form = reactive({
  Category: 'Food',
  Item: 'USDA Grade-A eggs, Dozen',
  Price: '',
  State: 'Texas',
  City: 'Dallas',
})

const deleteSettings = reactive({
  count: 1,
  mostRecentFirst: true,
})

// Only offer the items in the chosen category and the cities in the chosen state
const itemsInCategory = computed(() => props.options.category_items?.[form.Category] ?? [])
const citiesInState = computed(() => props.options.state_cities?.[form.State] ?? [])
// When the category or state changes, switch to its first item or city if the current one doesn't belong to it
watch(itemsInCategory, (items) => {
  if (!items.includes(form.Item)) form.Item = items[0] ?? ''
})
watch(citiesInState, (cities) => {
  if (!cities.includes(form.City)) form.City = cities[0] ?? ''
})

// Outcome of the last save and the last delete. fieldErrors has the server's message for each invalid field
const saveStatus = reactive({ busy: false, message: '', error: '', fieldErrors: {} })
const deleteStatus = reactive({ busy: false, message: '', error: '' })
// A save error that isn't about one field (e.g. the server can't be reached); field errors show under each field
const saveGeneralError = computed(() => (Object.keys(saveStatus.fieldErrors).length ? '' : saveStatus.error))

async function saveObservation() {
  Object.assign(saveStatus, { busy: true, message: '', error: '', fieldErrors: {} })
  try {
    const saved = await createObservation({ ...form, Date: date.value })
    saveStatus.message =
      `Saved ${saved.Item} at ${formatPrice(saved.Price)} in ${saved.City}, ${saved.State} on ${formatDate(saved.Date)}.`
    emit('changed')
  } catch (error) {
    saveStatus.error = error.message
    saveStatus.fieldErrors = error.fields ?? {}
  } finally {
    saveStatus.busy = false
  }
}

async function deleteMatching() {
  const { count, mostRecentFirst } = deleteSettings
  const order = mostRecentFirst ? 'most recent first' : 'oldest first'
  const matching = [form.Item, `${form.City}, ${form.State}`, formatDate(date.value), form.Price && `price ${form.Price}`]
    .filter(Boolean)
    .join(' · ')
  // Ask first. If the count isn't a whole number, skip the question: the server rejects it and says why
  if (/^\s*\d+\s*$/.test(count) && !window.confirm(`Delete up to ${count} matching observations, ${order}?\n\n${matching}`)) {
    return
  }
  Object.assign(deleteStatus, { busy: true, message: '', error: '' })
  try {
    const { deleted, requested } = await deleteObservations({ ...form, Date: date.value, count, mostRecentFirst })
    deleteStatus.message = deleted
      ? `Deleted ${deleted} of ${requested} requested observations.`
      : 'No observations match, so nothing was deleted.'
    if (deleted) emit('changed')
  } catch (error) {
    deleteStatus.error = error.message
  } finally {
    deleteStatus.busy = false
  }
}
</script>

<template>
  <!-- "Save Observation" submits this form; .prevent stops the page from reloading. The server checks every field -->
  <form class="form" @submit.prevent="saveObservation">
    <label for="date-input">Date</label>
    <input id="date-input" v-model="date" type="date" :aria-invalid="!!saveStatus.fieldErrors.Date" />
    <p v-if="saveStatus.fieldErrors.Date" class="error">{{ saveStatus.fieldErrors.Date }}</p>

    <label for="category-input">Category</label>
    <select id="category-input" v-model="form.Category" :aria-invalid="!!saveStatus.fieldErrors.Category">
      <option v-for="category in options.categories" :key="category" :value="category">{{ category }}</option>
    </select>
    <p v-if="saveStatus.fieldErrors.Category" class="error">{{ saveStatus.fieldErrors.Category }}</p>

    <label for="item-input">Item</label>
    <select id="item-input" v-model="form.Item" :aria-invalid="!!saveStatus.fieldErrors.Item">
      <option v-for="item in itemsInCategory" :key="item" :value="item">{{ item }}</option>
    </select>
    <p v-if="saveStatus.fieldErrors.Item" class="error">{{ saveStatus.fieldErrors.Item }}</p>

    <label for="price-input">Price</label>
    <input
      id="price-input"
      v-model="form.Price"
      type="text"
      inputmode="decimal"
      placeholder="e.g. 3.99"
      :aria-invalid="!!saveStatus.fieldErrors.Price"
    />
    <p v-if="saveStatus.fieldErrors.Price" class="error">{{ saveStatus.fieldErrors.Price }}</p>

    <label for="state-input">State</label>
    <select id="state-input" v-model="form.State" :aria-invalid="!!saveStatus.fieldErrors.State">
      <option v-for="state in options.states" :key="state" :value="state">{{ state }}</option>
    </select>
    <p v-if="saveStatus.fieldErrors.State" class="error">{{ saveStatus.fieldErrors.State }}</p>

    <label for="city-input">City</label>
    <select id="city-input" v-model="form.City" :aria-invalid="!!saveStatus.fieldErrors.City">
      <option v-for="city in citiesInState" :key="city" :value="city">{{ city }}</option>
    </select>
    <p v-if="saveStatus.fieldErrors.City" class="error">{{ saveStatus.fieldErrors.City }}</p>

    <button type="submit" :disabled="saveStatus.busy">{{ saveStatus.busy ? 'Saving…' : 'Save Observation' }}</button>
    <p v-if="saveStatus.message" class="success">{{ saveStatus.message }}</p>
    <p v-if="saveGeneralError" class="error">{{ saveGeneralError }}</p>
  </form>

  <!-- Deletes observations matching the form above -->
  <div class="form">
    <label for="delete-count">Number of Matching Observations to delete</label>
    <input id="delete-count" v-model="deleteSettings.count" type="text" inputmode="numeric" />
    <p class="hint">Matches the Date, Category, Item, State and City above, and the Price if one is entered.</p>

    <label class="checkbox">
      <input v-model="deleteSettings.mostRecentFirst" type="checkbox" />
      Delete Most Recent First?
    </label>

    <button type="button" :disabled="deleteStatus.busy" @click="deleteMatching">Delete Matching Observations</button>
    <p v-if="deleteStatus.message" class="success">{{ deleteStatus.message }}</p>
    <p v-if="deleteStatus.error" class="error">{{ deleteStatus.error }}</p>
  </div>
</template>
