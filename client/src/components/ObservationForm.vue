<script setup>
import { computed, reactive, watch } from 'vue'
import { createObservation, deleteObservations } from '../api.js'
import { currencyPrefix, formatDate, formatPrice } from '../format.js'

const props = defineProps({
  options: { type: Object, required: true },
})
// Tells App.vue that observations were saved or deleted, so it reloads the table and graph
const emit = defineEmits(['changed'])
// The Date field lives in App.vue, because the graph uses it too ("Average Item Price by City" shows that date)
const date = defineModel('date', { type: String, required: true })

// Starts empty: when the options arrive, the form picks the first category and state in server/options.json, and the
// watchers below then pick their first item and city
const form = reactive({ Category: '', Item: '', Price: '', State: '', City: '' })

const deleteSettings = reactive({
  count: 1,
  mostRecentFirst: true,
})

watch(
  () => props.options,
  (options) => {
    if (!options.categories.includes(form.Category)) form.Category = options.categories[0] ?? ''
    if (!options.states.includes(form.State)) form.State = options.states[0] ?? ''
  },
)

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
  // Both actions report under the same buttons, so each one clears the other's last message
  Object.assign(deleteStatus, { message: '', error: '' })
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
  Object.assign(saveStatus, { message: '', error: '', fieldErrors: {} })
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
  <div class="card">
    <!-- The fields. "Add observation" below submits this form through its form="observation-form" attribute;
         .prevent stops the page from reloading. The server checks every field -->
    <form id="observation-form" class="form-section" @submit.prevent="saveObservation">
      <h2 class="card-title"><span class="step">1</span>Observation details</h2>
      <div class="field-grid">
        <div class="field">
          <label for="date-input">Date</label>
          <input
            id="date-input"
            v-model="date"
            class="control"
            type="date"
            :aria-invalid="!!saveStatus.fieldErrors.Date"
          />
          <p v-if="saveStatus.fieldErrors.Date" class="field-error">{{ saveStatus.fieldErrors.Date }}</p>
        </div>

        <div class="field">
          <label for="price-input">Price</label>
          <div class="control prefixed" :class="{ invalid: saveStatus.fieldErrors.Price }">
            <span class="prefix" aria-hidden="true">{{ currencyPrefix.trim() }}</span>
            <input
              id="price-input"
              v-model="form.Price"
              type="text"
              inputmode="decimal"
              placeholder="3.99"
              :aria-invalid="!!saveStatus.fieldErrors.Price"
            />
          </div>
          <p v-if="saveStatus.fieldErrors.Price" class="field-error">{{ saveStatus.fieldErrors.Price }}</p>
        </div>

        <div class="field field--full">
          <label for="category-input">Category</label>
          <select
            id="category-input"
            v-model="form.Category"
            class="control"
            :aria-invalid="!!saveStatus.fieldErrors.Category"
          >
            <option v-for="category in options.categories" :key="category" :value="category">{{ category }}</option>
          </select>
          <p v-if="saveStatus.fieldErrors.Category" class="field-error">{{ saveStatus.fieldErrors.Category }}</p>
        </div>

        <div class="field field--full">
          <label for="item-input">Item</label>
          <select id="item-input" v-model="form.Item" class="control" :aria-invalid="!!saveStatus.fieldErrors.Item">
            <option v-for="item in itemsInCategory" :key="item" :value="item">{{ item }}</option>
          </select>
          <p v-if="saveStatus.fieldErrors.Item" class="field-error">{{ saveStatus.fieldErrors.Item }}</p>
        </div>

        <div class="field">
          <label for="state-input">State</label>
          <select id="state-input" v-model="form.State" class="control" :aria-invalid="!!saveStatus.fieldErrors.State">
            <option v-for="state in options.states" :key="state" :value="state">{{ state }}</option>
          </select>
          <p v-if="saveStatus.fieldErrors.State" class="field-error">{{ saveStatus.fieldErrors.State }}</p>
        </div>

        <div class="field">
          <label for="city-input">City</label>
          <select id="city-input" v-model="form.City" class="control" :aria-invalid="!!saveStatus.fieldErrors.City">
            <option v-for="city in citiesInState" :key="city" :value="city">{{ city }}</option>
          </select>
          <p v-if="saveStatus.fieldErrors.City" class="field-error">{{ saveStatus.fieldErrors.City }}</p>
        </div>
      </div>
    </form>

    <!-- The actions: save the observation above, or delete observations matching it -->
    <div class="form-section form-section--muted">
      <h2 class="card-title"><span class="step">2</span>Choose an action</h2>
      <div class="action-buttons">
        <button type="submit" form="observation-form" class="btn btn-primary" :disabled="saveStatus.busy">
          {{ saveStatus.busy ? 'Adding…' : 'Add observation' }}
        </button>
        <button type="button" class="btn btn-danger" :disabled="deleteStatus.busy" @click="deleteMatching">
          {{ deleteStatus.busy ? 'Deleting…' : 'Delete matching' }}
        </button>
      </div>

      <div class="delete-options">
        <span class="delete-count">
          <label for="delete-count">Delete up to</label>
          <input
            id="delete-count"
            v-model="deleteSettings.count"
            class="control count-input"
            type="text"
            inputmode="numeric"
          />
          <span>matches</span>
        </span>
        <label class="checkbox">
          <input v-model="deleteSettings.mostRecentFirst" type="checkbox" />
          Most recent first
        </label>
      </div>
      <p class="hint">Delete matches Date, Category, Item, State and City, plus Price if one is entered.</p>

      <p v-if="saveStatus.message" class="status success" role="status">{{ saveStatus.message }}</p>
      <p v-if="saveGeneralError" class="status error" role="alert">{{ saveGeneralError }}</p>
      <p v-if="deleteStatus.message" class="status success" role="status">{{ deleteStatus.message }}</p>
      <p v-if="deleteStatus.error" class="status error" role="alert">{{ deleteStatus.error }}</p>
    </div>
  </div>
</template>
