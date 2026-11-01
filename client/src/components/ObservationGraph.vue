<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { getAveragePriceByCity, getPricesOverTime } from '../api.js'
import { currencyPrefix, formatDate, formatPrice } from '../format.js'
import { SERIES_COLORS } from '../theme.js'

const props = defineProps({
  observations: { type: Array, required: true },
})
// The form's Date field: "Average Item Price by City" shows that date
const date = defineModel('date', { type: String, required: true })

const PRICES_OVER_TIME = 'Item Prices Over Time'
const AVERAGE_BY_CITY = 'Average Item Price by City'
const graphTypes = [PRICES_OVER_TIME, AVERAGE_BY_CITY]
const graphType = ref(graphTypes[0])
const title = computed(() => (graphType.value === PRICES_OVER_TIME ? 'Item prices over time' : 'Average item price by city'))
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

// Chart styling from the page design: Inter text in the page's grays, a white background with light horizontal
// gridlines, and the same series colors as the table
const FONT_FAMILY = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
const baseLayout = {
  colorway: SERIES_COLORS,
  font: { family: FONT_FAMILY, size: 12, color: '#5e6670' },
  paper_bgcolor: '#ffffff',
  plot_bgcolor: '#ffffff',
  hovermode: 'closest',
  hoverlabel: {
    align: 'left',
    bgcolor: '#ffffff',
    bordercolor: '#e3e6e9',
    font: { family: FONT_FAMILY, size: 12, color: '#1a2633' },
  },
  margin: { t: 8, r: 8, b: 8, l: 8 }, // automargin grows these to fit the labels
}
const axisStyle = { automargin: true, ticks: '', zeroline: false, showline: false, gridcolor: '#eff0eb' }
// The bottom axis (dates or items): no vertical gridlines, just a thin baseline
const categoryAxis = { ...axisStyle, showgrid: false, showline: true, linecolor: '#e3e5e0' }
// Price axes start at zero and show the same currency as the table, e.g. "$10", with commas for thousands.
// Up to 8 labels, so the sample prices get one every $10 as in the design
const priceAxis = { ...axisStyle, rangemode: 'tozero', tickprefix: currencyPrefix, tickformat: ',', nticks: 8 }
const plotConfig = { responsive: true, displaylogo: false }

// Below this chart width (e.g. on a phone) the legend moves above the plot and the date axis shows fewer labels,
// so the plot keeps the full width. It's decided each time the graph is drawn
const NARROW_CHART_WIDTH = 560
function isNarrow() {
  return chart.value.clientWidth < NARROW_CHART_WIDTH
}

// Legend titled like the design ("Item", "City"), with one symbol size for every entry: at the top right, or in a
// row above the plot on narrow screens
function legend(text) {
  const style = {
    title: { text, font: { color: '#626a73' } },
    font: { color: '#3b4754' },
    bgcolor: 'rgba(0, 0, 0, 0)',
    itemsizing: 'constant',
    tracegroupgap: 0,
  }
  return isNarrow() ? { ...style, orientation: 'h', x: 0, xanchor: 'left', y: 1.02, yanchor: 'bottom' } : style
}

function drawPricesOverTime(series) {
  // One scatter trace per item, so each item gets its own color. The server already grouped and counted the points
  const maxCount = Math.max(1, ...series.flatMap((s) => s.counts))
  const sizeref = Math.max(SINGLE_OBSERVATION_SIZEREF, maxCount / (2 * MAX_DOT_RADIUS ** 2))
  const traces = series.map(({ item, dates, prices, counts }) => ({
    type: 'scatter',
    mode: 'markers',
    name: item,
    legendgroup: item,
    // Semi-transparent, so overlapping dots stay visible and darken where they stack
    marker: { symbol: 'circle', size: counts, sizemode: 'area', sizeref, opacity: 0.55 },
    // Plotly can't call formatPrice, so each point carries its formatted price (and count) for the hover text
    customdata: prices.map((price, i) => [formatPrice(price), counts[i]]),
    hovertemplate:
      `<b>${item}</b><br>%{x|%b %-d, %Y}<br>Price: %{customdata[0]}<br>Observations: %{customdata[1]}<extra></extra>`,
    x: dates,
    y: prices,
  }))
  const layout = {
    ...baseLayout,
    // Every date label shows the day and, on a second line, the year ("Jun 20" over "2022"), so all labels look alike
    // and stay narrow enough not to tilt. Up to 12 labels: every day across the sample data's 10 days, fewer over
    // longer ranges or narrow screens
    xaxis: { ...categoryAxis, tickformat: '%b %-d<br>%Y', nticks: isNarrow() ? 5 : 12 },
    yaxis: priceAxis,
    legend: legend('Item'),
  }
  Plotly.react(chart.value, traces, layout, plotConfig)
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
      `<b>${city}</b><br>%{x}<br>Average price: %{customdata[0]}<br>Observations: %{customdata[1]}<extra></extra>`,
  }))
  const layout = {
    ...baseLayout,
    barmode: 'group',
    bargap: 0.3,
    bargroupgap: 0.08,
    barcornerradius: 3,
    xaxis: categoryAxis,
    yaxis: priceAxis,
    legend: legend('City'),
  }
  Plotly.react(chart.value, traces, layout, plotConfig)
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
    // Wait for the page's web fonts, so Plotly sizes its labels and legend in Inter rather than a fallback font
    await document.fonts.ready
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
  <section class="card">
    <header class="card-header">
      <h2 class="card-title">{{ title }}</h2>
      <select v-model="graphType" class="control control--sm" aria-label="Graph type">
        <option v-for="type in graphTypes" :key="type" :value="type">{{ type }}</option>
      </select>
    </header>

    <p v-if="errorMessage" class="chart-message error" role="alert">{{ errorMessage }}</p>
    <p v-if="noData" class="chart-message">
      {{ noData.date ? `No observations on ${formatDate(noData.date)}.` : 'Choose a date to see average prices by city.' }}
      <template v-if="noData.latestDate">
        The latest date with observations is {{ formatDate(noData.latestDate) }}.
        <button type="button" class="link-button" @click="showLatestDate">Show {{ formatDate(noData.latestDate) }}</button>
      </template>
    </p>
    <div ref="chart" class="chart"></div>
  </section>
</template>
