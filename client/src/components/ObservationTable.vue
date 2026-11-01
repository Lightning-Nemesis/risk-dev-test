<script setup>
import { formatDate, formatDateTime, formatPrice } from '../format.js'

defineProps({
  observations: { type: Array, required: true },
})

// Each column's heading, and how to show its values. Numbers are right-aligned, as in a financial report
const columns = [
  { key: 'Date', label: 'Date', format: formatDate },
  { key: 'Item', label: 'Item' },
  { key: 'Price', label: 'Price', format: formatPrice, numeric: true },
  { key: 'Category', label: 'Category' },
  { key: 'State', label: 'State' },
  { key: 'City', label: 'City' },
  { key: 'AddedOn', label: 'Added On', format: formatDateTime },
]
</script>

<template>
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th v-for="column in columns" :key="column.key" :class="{ numeric: column.numeric }">{{ column.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in observations" :key="row.id">
          <td v-for="column in columns" :key="column.key" :class="{ numeric: column.numeric }">
            {{ column.format ? column.format(row[column.key]) : row[column.key] }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
