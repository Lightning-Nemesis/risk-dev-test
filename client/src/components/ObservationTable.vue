<script setup>
import { formatDate, formatDateTime, formatPrice } from '../format.js'
import { SERIES_COLORS } from '../theme.js'

const props = defineProps({
  // The newest observations, and how many there are in all (there can be more than the table shows)
  observations: { type: Array, required: true },
  total: { type: Number, required: true },
  // Item names in the order of server/options.json, the same order the graph colors its items in
  items: { type: Array, required: true },
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

// The dot beside each category is the row's item color in the graph, so it still matches when a category has
// several items. Items no longer in the options file get a gray dot
function itemColor(item) {
  const index = props.items.indexOf(item)
  return index === -1 ? 'var(--text-muted)' : SERIES_COLORS[index % SERIES_COLORS.length]
}
</script>

<template>
  <section class="card">
    <header class="card-header">
      <h2 class="card-title">
        Recent observations
        <span class="card-count">
          {{ total.toLocaleString('en-US') }} total<template v-if="total > observations.length">
            · showing the newest {{ observations.length.toLocaleString('en-US') }}</template>
        </span>
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
                :style="{ background: itemColor(row.Item) }"
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
