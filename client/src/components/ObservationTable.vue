<script setup>
import { formatDate, formatDateTime, formatPrice } from '../format.js'
import { SERIES_COLORS } from '../theme.js'

const props = defineProps({
  observations: { type: Array, required: true },
  // Category names in the server's fixed order. Each category has one item, in the same order as the graph's
  // items, so a category's dot here matches its item's color in the graph
  categories: { type: Array, required: true },
})

// Each column's heading, how to show its values, and its style. Prices are right-aligned, as in a financial report
const columns = [
  { key: 'Date', label: 'Date', format: formatDate },
  { key: 'Item', label: 'Item' },
  { key: 'Price', label: 'Price', format: formatPrice, class: 'numeric price' },
  { key: 'Category', label: 'Category' },
  { key: 'State', label: 'State' },
  { key: 'City', label: 'City' },
  { key: 'AddedOn', label: 'Added On', format: formatDateTime, class: 'muted' },
]

function categoryColor(category) {
  const index = props.categories.indexOf(category)
  return index === -1 ? 'var(--text-muted)' : SERIES_COLORS[index % SERIES_COLORS.length]
}
</script>

<template>
  <section class="card">
    <header class="card-header">
      <h2 class="card-title">
        Recent observations
        <span class="card-count">{{ observations.length.toLocaleString('en-US') }} total</span>
      </h2>
    </header>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key" :class="column.class">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in observations" :key="row.id">
            <td v-for="column in columns" :key="column.key" :class="column.class">
              <span
                v-if="column.key === 'Category'"
                class="dot"
                :style="{ background: categoryColor(row.Category) }"
                aria-hidden="true"
              ></span>
              {{ column.format ? column.format(row[column.key]) : row[column.key] }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
