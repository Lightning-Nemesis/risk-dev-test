// Tests for format.js. Run them with: npm test
import { describe, expect, it, vi } from 'vitest'

// Run as if in Arizona (UTC-7), where reading "2022-06-29" as midnight UTC would show June 28. This is set before
// format.js is loaded, because its formatters pick up the time zone when they're created
process.env.TZ = 'America/Phoenix'
const { currencyPrefix, formatDate, formatDateTime, formatPrice } = await import('./format.js')

// Newer versions of Intl put a narrow no-break space before AM/PM; compare with plain spaces
const plainSpaces = (text) => text.replace(/\s/g, ' ')

describe('formatPrice', () => {
  it('shows prices in the currency from client/.env, rounded to the cent', () => {
    expect(formatPrice(4.659)).toBe('$4.66')
    expect(formatPrice(10000)).toBe('$10,000.00')
    expect(currencyPrefix).toBe('$')
  })

  it('shows nothing for a missing price', () => {
    expect(formatPrice(null)).toBe('')
    expect(formatPrice(undefined)).toBe('')
  })

  it('follows VITE_CURRENCY without converting the amount', async () => {
    vi.stubEnv('VITE_CURRENCY', 'EUR')
    vi.resetModules()
    const euro = await import('./format.js')
    expect(euro.formatPrice(4.659)).toBe('€4.66')
    expect(euro.currencyPrefix).toBe('€')
    vi.unstubAllEnvs()
  })
})

describe('formatDate', () => {
  it('runs in a time zone where new Date() would show the day before', () => {
    // Guards the test below: if this time zone weren't applied, the date test couldn't catch the problem
    expect(new Date('2022-06-29').toLocaleDateString('en-US')).toBe('6/28/2022')
  })

  it('shows the same calendar day, without shifting it', () => {
    expect(formatDate('2022-06-29')).toBe('Jun 29, 2022')
    expect(formatDate('2022-01-01')).toBe('Jan 1, 2022')
  })

  it('shows nothing for a missing date', () => {
    expect(formatDate('')).toBe('')
  })
})

describe('formatDateTime', () => {
  it("converts UTC to the viewer's time zone", () => {
    // 19:47 UTC is 12:47 PM in Arizona
    expect(plainSpaces(formatDateTime('2022-06-29T19:47:11Z'))).toBe('Jun 29, 12:47 PM')
  })

  it('shows nothing for a missing time', () => {
    expect(formatDateTime('')).toBe('')
  })
})
