// How values are shown on the page, in American business style. The data itself stays as the server sends it.

// Currency from client/.env (task 6). This only changes how prices look: they are not converted
const priceFormat = new Intl.NumberFormat('en-US', { style: 'currency', currency: import.meta.env.VITE_CURRENCY })

// 4.66 -> "$4.66" (or "€4.66" with VITE_CURRENCY=EUR). A missing price shows as nothing
export function formatPrice(price) {
  return price === null || price === undefined ? '' : priceFormat.format(price)
}

// What comes before the number in a price, e.g. "$", for the graph axes (Plotly can't call formatPrice)
const priceParts = priceFormat.formatToParts(1)
export const currencyPrefix = priceParts
  .slice(0, priceParts.findIndex((part) => part.type === 'integer'))
  .map((part) => part.value)
  .join('')

// "2022-06-29" -> "06/29/2022". This splits the text instead of using new Date(), which reads a date without a
// time as midnight UTC, and so would show the day before anywhere in the Americas
export function formatDate(isoDate) {
  if (!isoDate) return ''
  const [year, month, day] = isoDate.split('-')
  return `${month}/${day}/${year}`
}

// "2022-06-29T19:47:11Z" (UTC) -> "06/29/2022, 12:47 PM" in the viewer's own time zone
const dateTimeFormat = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: 'numeric',
  minute: '2-digit',
})
export function formatDateTime(isoDateTime) {
  return isoDateTime ? dateTimeFormat.format(new Date(isoDateTime)) : ''
}
