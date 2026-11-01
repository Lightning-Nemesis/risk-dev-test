<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { getAveragePriceByCity, getPricesOverTime } from '../api.js'
import { currencyPrefix, formatDate, formatPrice } from '../format.js'

const props = defineProps({
  observations: { type: Array, required: true },
})
// The form's Date field: "Average Item Price by City" shows that date
const date = defineModel('date', { type: String, required: true })

const PRICES_OVER_TIME = 'Item Prices Over Time'
const AVERAGE_BY_CITY = 'Average Item Price by City'
const graphTypes = [PRICES_OVER_TIME, AVERAGE_BY_CITY]
const graphType = ref(graphTypes[0])
const chart = ref(null)
const errorMessage = ref('')
// Set when the bar chart has no bars: { date, latestDate }, where date is '' if the Date field is empty
const noData = ref(null)

// Each point's area is proportional to how many observations share its item, date and price (task 4).
// Plotly draws a point of size s with radius sqrt(s / 2 / sizeref) px, so this sizeref gives one observation
// Plotly's default 6px dot, and 4 identical observations a 12px dot with 4 times the area
const SINGLE_OBSERVATION_SIZEREF = 1 / 18
// Largest dot radius in px. If a count would go past it, every dot shrinks by the same factor, keeping proportions
const MAX_DOT_RADIUS = 20

// Same look as the original Dash app, which drew px.scatter(df, x='Date', y='Price', color='Item')
// with Plotly Express's default "plotly" template
const axisStyle = {
  gridcolor: 'white',
  linecolor: 'white',
  zerolinecolor: 'white',
  zerolinewidth: 2,
  ticks: '',
  automargin: true,
}
const baseLayout = {
  colorway: ['#636efa', '#EF553B', '#00cc96', '#ab63fa', '#FFA15A', '#19d3f3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'],
  plot_bgcolor: '#E5ECF6',
  paper_bgcolor: 'white',
  font: { color: '#2a3f5f' },
  hovermode: 'closest',
  hoverlabel: { align: 'left' },
  margin: { t: 60 },
}
// Price axes show the same currency as the table, e.g. "$10", with commas for thousands
const priceAxisFormat = { tickprefix: currencyPrefix, tickformat: ',' }

function drawPricesOverTime(series) {
  // One scatter trace per item, so each item gets its own color. The server already grouped and counted the points
  const maxCount = Math.max(1, ...series.flatMap((s) => s.counts))
  const sizeref = Math.max(SINGLE_OBSERVATION_SIZEREF, maxCount / (2 * MAX_DOT_RADIUS ** 2))
  const traces = series.map(({ item, dates, prices, counts }) => ({
    type: 'scatter',
    mode: 'markers',
    name: item,
    legendgroup: item,
    marker: { symbol: 'circle', size: counts, sizemode: 'area', sizeref },
    // Plotly can't call formatPrice, so each point carries its formatted price (and count) for the hover text
    customdata: prices.map((price, i) => [formatPrice(price), counts[i]]),
    hovertemplate:
      `Item=${item}<br>Date=%{x|%m/%d/%Y}<br>Price=%{customdata[0]}<br>Observations=%{customdata[1]}<extra></extra>`,
    x: dates,
    y: prices,
  }))
  const layout = {
    ...baseLayout,
    xaxis: { ...axisStyle, title: { text: 'Date', standoff: 15 }, tickformat: '%m/%d/%Y' },
    yaxis: { ...axisStyle, ...priceAxisFormat, title: { text: 'Price', standoff: 15 } },
    // Keep the legend's symbols one size, while the points on the graph vary with their counts
    legend: { title: { text: 'Item' }, tracegroupgap: 0, itemsizing: 'constant' },
  }
  Plotly.react(chart.value, traces, layout, { responsive: true })
}

function drawAverageByCity(data) {
  // data is null when the Date field is empty, e.g. while it's being cleared
  const series = data?.series ?? []
  const hasBars = series.some((s) => s.counts.some((count) => count > 0))
  noData.value = hasBars ? null : { date: data?.date ?? '', latestDate: data?.latest_date ?? null }
  // One bar trace per city, so each city gets its own color; barmode 'group' puts them side by side for each item
  const traces = series.map(({ city, averages, counts }) => ({
    type: 'bar',
    name: city,
    x: data.items,
    y: averages,
    customdata: averages.map((average, i) => [formatPrice(average), counts[i]]),
    hovertemplate:
      `City=${city}<br>Item=%{x}<br>Average price=%{customdata[0]}<br>Observations=%{customdata[1]}<extra></extra>`,
  }))
  const layout = {
    ...baseLayout,
    barmode: 'group',
    xaxis: { ...axisStyle, title: { text: 'Item', standoff: 15 } },
    yaxis: { ...axisStyle, ...priceAxisFormat, title: { text: 'Average price', standoff: 15 } },
    legend: { title: { text: 'City' } },
  }
  Plotly.react(chart.value, traces, layout, { responsive: true })
}

// Numbers each request, so only the newest one draws: the Date changes with every edit, and an older, slower
// response must not replace the graph for a newer date
let latestRequest = 0

async function showGraph() {
  const request = ++latestRequest
  const showAverages = graphType.value === AVERAGE_BY_CITY
  try {
    let data = null // stays null for the bar chart while the Date field is empty: there's nothing to ask for
    if (!showAverages) {
      data = await getPricesOverTime()
    } else if (date.value) {
      data = await getAveragePriceByCity(date.value)
    }
    if (request !== latestRequest) return // a newer request was sent meanwhile, and it will draw instead
    errorMessage.value = ''
    if (showAverages) {
      drawAverageByCity(data)
    } else {
      noData.value = null
      drawPricesOverTime(data)
    }
  } catch (error) {
    if (request === latestRequest) errorMessage.value = `Could not load the graph (${error.message})`
  }
}

function showLatestDate() {
  date.value = noData.value.latestDate
}

// Draw the chosen graph, and reload its data whenever the observations change (first load, save or delete)
watch([graphType, () => props.observations], showGraph)
// The bar chart shows the form's Date, so redraw it when the Date changes
watch(date, () => {
  if (graphType.value === AVERAGE_BY_CITY) showGraph()
})
onBeforeUnmount(() => Plotly.purge(chart.value))
</script>

<template>
  <label for="graph-type">Graph Type</label>
  <select id="graph-type" v-model="graphType">
    <option v-for="type in graphTypes" :key="type" :value="type">{{ type }}</option>
  </select>

  <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
  <p v-if="noData" class="hint">
    {{ noData.date ? `No observations on ${formatDate(noData.date)}.` : 'Choose a date to see average prices by city.' }}
    <template v-if="noData.latestDate">
      The latest date with observations is {{ formatDate(noData.latestDate) }}.
      <button type="button" @click="showLatestDate">Show {{ formatDate(noData.latestDate) }}</button>
    </template>
  </p>
  <div ref="chart" class="chart"></div>
</template>
