// Every request from the client to the Flask API lives in this file.
// Paths start with /api: the Vite dev server forwards them to the server set in client/.env (API_URL).

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(body.error || `Request to ${path} failed with status ${response.status}`)
    // For invalid input the server also sends a message per field, e.g. { Price: 'Price must be more than 0' }
    error.fields = body.fields || {}
    throw error
  }
  return body
}

export function getOptions() {
  return request('/api/options')
}

// The newest `limit` observations and the total number: { total, observations }
export function getObservations(limit) {
  return request(`/api/observations?${new URLSearchParams({ limit })}`)
}

// One series per item for the "Item Prices Over Time" graph: { item, dates, prices, counts }
export function getPricesOverTime() {
  return request('/api/charts/prices-over-time')
}

// The "Average Item Price by City" graph for one date (YYYY-MM-DD):
// { date, items, series: [{ city, averages, counts }], latest_date }
export function getAveragePriceByCity(date) {
  return request(`/api/charts/average-price-by-city?${new URLSearchParams({ date })}`)
}

// Saves one observation ({ Date, Category, Item, Price, State, City }) and returns it as stored
export function createObservation(observation) {
  return request('/api/observations', { method: 'POST', body: JSON.stringify(observation) })
}

// Deletes up to `count` observations matching the given fields, and returns { deleted, requested }
export function deleteObservations(match) {
  return request(`/api/observations?${new URLSearchParams(match)}`, { method: 'DELETE' })
}
