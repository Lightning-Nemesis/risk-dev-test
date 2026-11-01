# Plan: risk-dev-test

Working plan for the Beneficient take-home. It combines a read of every file and the sample database with tests of the running Docker app on 10/31/2026. An independent review then checked it against the README and code (section 6). Section 5 maps every README requirement to a step.

## 1. Current state of the running app

| Feature | Status | Evidence |
|---|---|---|
| Page loads, drop-downs fill, table and scatter chart show | ✅ Works | `GET /api/options` and `GET /api/observations` return 200 (750 rows, ~17 ms, ~170 KB) |
| Client code compiles | ✅ Works | Vite serves all 6 source modules; no errors in either container's log |
| Save Observation | ❌ Does nothing | The form has `@submit.prevent` with no handler. No server route: `POST /api/observations` → 405 |
| Delete Matching Observations | ❌ Does nothing | The button has no click handler. `DELETE /api/observations` → 405. `delete_matching` is `pass` |
| Graph Type drop-down | ❌ Does nothing | `drawChart()` never reads `graphType`. No "Average Item Price by City" chart exists |
| Point size by count | ❌ Missing | Every marker is the same size; nothing counts duplicates |
| `MAX_PRICE`, `VITE_CURRENCY` | ❌ Unused | Not referenced anywhere in the code |
| API error messages | ⚠️ Generic | Flask returns HTML error pages (e.g. the 405 above), so `api.js` can't read `body.error` and shows "Request to … failed with status 405" |
| Item drop-down | ⚠️ Starts blank | The form default `'USDA Grade-A eggs'` isn't in the options (`'USDA Grade-A eggs, Dozen'`) |

## 2. Problems found

Each ID is referenced by the step that fixes it.

### Must fix (the six tasks can't be correct without these)

| ID | Problem | Evidence | Step |
|---|---|---|---|
| P1 | Mixed date formats: sample rows store `'2022-06-20 00:00:00'`, but the form sends `'2026-10-31'` and `write()` stores it unchanged | API output, `sqlize` | 3 |
| P2 | SQL is built by string interpolation (`sqlize` + f-string in `write()`) | `cpi.py:83-88` | 3 |
| P3 | The default Item isn't a valid item | `ObservationForm.vue:19` | 5 |
| P4 | All 750 sample rows share one `AddedOn` (`2022-06-29 19:47:11`), so "most recent first" ties | API output | 4 |
| P5 | No input validation: Price and delete count are free text, and any Category/Item/State/City combination is accepted | Form; no server checks | 5, 6 |
| P6 | Flask error responses are HTML, not JSON. With `FLASK_DEBUG=1`, unexpected errors skip a `500` handler entirely and show the Werkzeug debugger page | 405 response above; tested in the container | 2 |
| P7 | In SQLite, `LIMIT -1` means "no limit", so a negative count would delete every matching row | Tested in the server container | 4 |
| P8 | `DELETE … LIMIT` works in the Docker image's SQLite (3.46.1) but is a syntax error in the host's Python 3.11.9 (SQLite 3.45.1), so it isn't portable | Tested both | 4 |
| P9 | `float('nan')` parses in Python, and `nan > MAX_PRICE` is `False`, so a naive check accepts it | Python semantics | 5 |
| P23 | Sample prices have up to 16 decimals: 0 exact (Item, Date, Price) duplicates, but 15 when rounded to cents. Price matching for delete and task 4 needs one consistent rule | Read-only query on `test.db` | 3 |

### Should fix (visible to graders, or bonus points)

| ID | Problem | Evidence | Step |
|---|---|---|---|
| P10 | Sample data covers only 06/20/2022–06/29/2022, and the form's Date defaults to today, so the bar chart is empty on first view | API output | 8 |
| P11 | Sample data has no exact duplicate points, so task 4's sizing only shows after saving identical observations (or after P23's rounding) | API output | 3, 7 |
| P12 | Raw display: `20.587336131853935`, `2022-06-29 00:00:00` | Table | 9 |
| P13 | `AddedOn` comes from SQLite `current_timestamp`, which is UTC, and is sent without a time zone, so a browser reads it as local time | Tested in the container | 9 |
| P14 | New rows land at the bottom of a 750-row scrolling table, so a save looks like it did nothing. Rows are keyed by index | `ObservationTable.vue` | 9 |
| P15 | Items aren't filtered by Category and Cities aren't filtered by State in the drop-downs | `ObservationForm.vue` | 5 |
| P16 | Save and delete errors have nowhere to show (`errorMessage` is set only on page load) | `App.vue` | 5, 6 |
| P17 | Running the tests drops and rebuilds `test.db`. Docker mounts `server/`, so that is the same file you submit | `test_create_table`, `compose.yaml` | 1 |
| P18 | `'Los Angelos'` is misspelled in `state_city_map` and in 150 stored rows. It shows in the drop-down and will show in the bar-chart legend | API output | 3 |
| P24 | JavaScript reads `new Date('2022-06-29')` as UTC midnight, so it displays as **06/28/2022** in US time zones | Tested with `TZ=America/Phoenix` | 9 |

### Nice to fix, or document only

| ID | Problem | Evidence | Step |
|---|---|---|---|
| P19 | `Observation.AddedOn = datetime.datetime.now()` runs once at import; `write()` never uses it | `cpi.py:41` | 10 |
| P20 | `get_test_data` uses three row-by-row `df.apply` calls (slow; can be vectorized) | `cpi.py:122-127` | 10 |
| P21 | `FLASK_DEBUG=1` with host `0.0.0.0` exposes the Werkzeug debugger, which can run code, to anything that reaches port 5001. Fine for local development, not for production | Server log: "Debugger is active!" | 12 (document) |
| P22 | `server/README.md:22` and `client/README.md:16` point to an "If a port is already in use" section of the main README that doesn't exist | Those lines | 12 |

## 3. Decisions

Recommendation first. Record each final choice in the READMEs, since graders look for reasoning.

| # | Question | Recommendation | Why |
|---|---|---|---|
| D1 | What does "matching" mean for delete? | Match the form's Date, Category, Item, State and City. Add Price only when it's filled in, using exact equality, which works because every stored price is rounded to the cent (D5) | One rule everywhere; the `<column> = value` contract in the `delete_matching` docstring stays true |
| D2 | What does "Delete Most Recent First" sort by? | `AddedOn` (entry time), newest first, with `rowid` as tiebreaker. Unchecked = oldest first | Every matched row already has the same Date, so sorting by Date would change nothing |
| D3 | How to fix the stored data (P1, P18, P23)? | One idempotent script, `server/migrate.py`: dates → `YYYY-MM-DD`, prices rounded to cents, `'Los Angelos'` → `'Los Angeles'`. Also fix `get_test_data` and `write()` so new data comes out clean | Repeatable: it can be re-run on the backup at submission, and reviewers can read exactly what changed |
| D4 | What does "in proportion" mean for point size (task 4)? | Group by Item, Date **and** Price (the README says item and price; a point on the chart is also a date). Marker **area** proportional to count (`sizemode: 'area'`) with a **fixed** `sizeref` | People judge dots by area. A fixed scale keeps single dots the same size when the first duplicate appears. Write both choices in the README |
| D5 | Round prices? | Round to the cent (2 decimal places, still in dollars, e.g. `20.59`) on save and in the migration | Prices are money, and it makes "same price" meaningful |
| D6 | Endpoint shapes | As listed in steps 5–8 | RESTful and easy to explain |
| D7 | The empty bar chart (P10) | Show "No observations on MM/DD/YYYY", plus the latest date that has data (the endpoint returns it) | Graders will open the app on a date with no data |
| D8 | Dates and times in the client (P13, P24) | The server sends `Date` as `YYYY-MM-DD` and `AddedOn` as ISO 8601 UTC (`…Z`). The client formats `Date` by splitting the string, never via `new Date()`, and shows `AddedOn` in the viewer's local time | Avoids the one-day shift and the missing time zone |
| D9 | Fix "Los Angelos"? | Yes, in the map and the stored rows in the same change (D3) | It's visible in the UI. Fixing only the code would orphan 150 rows |
| D10 | Allow future dates? | Reject dates more than one day after the server's date (UTC in Docker), and document the rule | You can't observe a future price, and the one-day slack stops users ahead of UTC from being rejected for "today" |

## 4. Work plan

Each step lists the files, the work, and how to check it. Under Docker, server edits reload automatically (`FLASK_DEBUG=1` plus the mounted folder). Client edits do **not**: Docker on Windows doesn't pass file-change events to Vite, so run `docker compose restart client` and hard-refresh the browser (Ctrl + F5). The user chose manual restarts over a polling setting. Commands run from the project root.

### Step 0. Safety net
- ✅ Done 10/31/2026: `server/test.db` copied to `backup_db/test.db` (byte-identical, 750 rows). Step 13 re-runs the migration on this copy, so keep it untouched, and leave `backup_db/` out of the zip.
- **Don't run the tests until Step 1 is done**: they would rebuild `test.db` (P17).
- No git (decided).

**Check:** the backup copy exists.

### Step 1. Tests use a temporary database (P17) ✅ Done 10/31/2026
- `server/test_cpi.py`: in `setUp`, point `cpi.db_file` at a temp file and call `Observation.create_table()`; delete the file in `tearDown`. This works because every `cpi.py` method reads the module global `db_file` when it's called. Set it in `setUp`, not at import: importing `app` (Step 12) resets `cpi.db_file` to the real `test.db` (`app.py:20`).
- Update `server/README.md:50`, which says the tests rebuild `test.db`.

**Check:** `docker compose exec server python -m unittest -v` passes, and `test.db` still has 750 rows with `AddedOn` `2022-06-29 19:47:11`.

### Step 2. JSON errors for every API failure (P6) ✅ Done 10/31/2026
- `server/app.py`: a single `@app.errorhandler(Exception)`:
  - An `HTTPException` (404, 405, …) returns JSON with its own status code, and keeps its headers (e.g. `Allow` on a 405).
  - Anything else is logged and returns a JSON 500.
- A plain `500` handler isn't enough: with `FLASK_DEBUG=1`, Flask passes unhandled exceptions through and never calls it.

**Check:** `curl -i http://localhost:5001/api/nope` returns a JSON 404, and `curl -i -X PUT http://localhost:5001/api/options` returns a JSON 405 with an `Allow` header.

### Step 3. Safe SQL and clean data (P1, P2, P11, P18, P23, D3, D5, D9) ✅ Done 10/31/2026
Result: the first run changed 750 dates, 750 prices and 150 city names; the second changed 0. 750 rows remain and match `backup_db/test.db` row by row, with 15 duplicate (Item, Date, Price) points now.

- `server/cpi.py`:
  - `write()` uses `?` placeholders and stores Date as `YYYY-MM-DD` and Price rounded to the cent (e.g. `20.59`). Remove `sqlize` if nothing else uses it.
  - `get_test_data` produces `YYYY-MM-DD` dates and prices rounded to the cent.
  - Rename `'Los Angelos'` to `'Los Angeles'` in `state_city_map`.
- `server/migrate.py`: an idempotent one-off script (safe to run twice). It converts `Date` with `date(Date)`, rounds `Price` to 2 decimals, and renames the city in the stored rows.
- Run it once: `docker compose exec server python migrate.py`.

**Check:**
- `SELECT DISTINCT length(Date)` returns only `10`, and no rows still have `'Los Angelos'`.
- Running the script again changes nothing.
- The row count is still 750.

### Step 4. Task 2: `Observation.delete_matching` (P4, P7, P8) ✅ Done 10/31/2026
Result: 8 new tests pass (17 total). Three planted bugs (no tie-breaker, negative counts allowed, ASC/DESC swapped) each made the tests fail. On a copy of the real data it deletes the last-added rows when checked and the first-added when unchecked. Unchecked = oldest first (D2), confirmed with the user.
- Keep the signature exactly as given. It's an instance method, so the endpoint calls `Observation().delete_matching(...)`.
- Allowlist the column names usable as filters (kwargs) and as keys in `order_to_delete_in`: `Date, Item, Price, Category, State, City, AddedOn`. An unknown column raises `ValueError`.
- `order_to_delete_in` can hold several keys; turn each into `<col> ASC|DESC` in the dict's order, then append `rowid` as the final tiebreaker. `None` means insertion order (`rowid ASC`).
- No filters at all raises `ValueError`, so the table can never be emptied by accident. This goes beyond the docstring, so document it.
- `n_to_delete` must be an integer ≥ 0. Reject negatives (P7) and booleans; 0 deletes nothing.
- Portable SQL (P8): `DELETE FROM Observation WHERE rowid IN (SELECT rowid FROM Observation WHERE <col> = ? AND … ORDER BY … LIMIT ?)`.
- Return the number of rows deleted (`cursor.rowcount`).
- Tests:
  - Deletes exactly N; fewer matches than N.
  - Ascending vs. descending order, and multiple order keys.
  - Several filters combined with AND.
  - Rejects an unknown column, an empty filter and a negative N.
  - A value like `"x' OR '1'='1"` is treated as data.

**Check:** all tests pass.

### Step 5. Task 1 Save, plus Task 6 `MAX_PRICE` (P3, P5, P9, P15, P16, D5, D10) ✅ Done 10/31/2026 (with Step 6)
Result: 28 tests pass (11 new for Steps 5–6), and four planted validation bugs each made them fail. Tested end to end through the running app, with the data identical afterwards. Changes from the plan:
- The form values stay in `ObservationForm` for now. Step 8 shares the Date with the graph.
- The table's newest-first order (from Step 9) was done here, so a saved row shows at the top.
- Errors list every invalid field at once.
- The test database setup moved into `temp_database.py`.
Server:
- `POST /api/observations` with a JSON body `{Date, Category, Item, Price, State, City}`.
- Validate:
  - Date parses with `datetime.strptime(value, '%Y-%m-%d')`, and passes the D10 rule. `date.fromisoformat` is too loose: in 3.12 it also accepts `20221031` and `2022-W43-1`.
  - Category and State are in the allowed lists, Item belongs to Category, and City belongs to State.
  - Price is a finite number > 0 and ≤ `MAX_PRICE`, rounded to cents. `MAX_PRICE` is read once at startup into a module constant, which tests can patch.
- Invalid input → 400 `{"error": "<field and reason>"}`. Success → 201 with the saved row.
- Extend `GET /api/options` with `category_items`, `state_cities` and `max_price` (keep the existing keys), so the client can filter drop-downs and show the limit without duplicating config.

Client:
- `api.js`: add `createObservation(observation)`.
- Move the form values into `App.vue`, because the graph needs Date in Step 8. Pass them to `ObservationForm` with `defineModel`.
- Fix the default Item (P3). Filter Items by Category and Cities by State (P15).
- On submit: call the API, show success or the server's error message (P16), then reload the table and the current chart.

**Check:**
- In the browser, saving eggs at 3.99 shows a success message, the new row at the top of the table, and a new point on the chart.
- With `curl` (bypassing the browser, whose number input will block some of these after Step 11), each of these returns 400 and saves nothing:
  - prices `20000`, `"abc"`, `"nan"`, `-1` and empty
  - date `20221031`
  - Texas + San Francisco

### Step 6. Task 3 Delete (P5, P16, D1, D2) ✅ Done 10/31/2026 (see Step 5)
- Server: `DELETE /api/observations?Date=…&Category=…&Item=…&State=…&City=…[&Price=…]&count=N&mostRecentFirst=true` calls `delete_matching` and returns 200 `{"deleted": n}`. Validate `count` (a positive integer) and the filters as in Step 5.
- Client: add `deleteObservations(...)` in `api.js` and a click handler on the button. Ask for confirmation ("Delete up to N matching observations?"), show "Deleted n of N requested", then reload the table and chart (in parallel, with `Promise.all`).

**Check:**
- Save the same observation 3 times, then delete 2 with the box ticked: 1 row is left, and it's the oldest one (check `AddedOn`).
- With the box unticked, the oldest rows go first.
- Counts `0`, `-1` and `abc` show an error.

### Step 7. Task 4: point size by count (D4) ✅ Done 10/31/2026
Result: 30 tests pass (2 new). The live data has 15 doubled points and every observation is counted once. Plotly 4.1.2's formula was checked in its code: radius = √(size ÷ 2 ÷ sizeref), so `sizeref = 1/18` gives 1 observation a 6px dot and 4 a 12px dot. If a dot would pass a 20px radius, all dots shrink together. Graph data loads whenever the observations change.
- Server: `GET /api/charts/prices-over-time` groups with `GROUP BY Item, Date, Price` and `COUNT(*)`. It returns the data already shaped per item (one series each: dates, prices, counts), so the client does no grouping.
- Client: when Graph Type is "Item Prices Over Time", draw one trace per series with `marker.size = counts`, `sizemode: 'area'` and a **fixed** `sizeref` (a constant, not derived from the largest count). Keep `sizemin` below the single-dot size; Plotly draws `max(sqrt(size / 2 / sizeref), sizemin)`, so a clamped single dot would break the proportions. Show the count in the hover text.

**Check:**
- Save the same row 4 times. It shows as one dot with 4× the area of a single dot, and the hover says 4 observations.
- The other dots don't change size.

### Step 8. Task 5: grouped bar chart (P10, D7) ✅ Done 10/31/2026
Result: 33 tests pass (3 new), and two planted averaging bugs each made them fail. On live data, 06/25/2022 gives 3 items × 5 cities, and Austin socks (21.122) matches a manual SQL average. Today has no data, so the chart offers 06/29/2022.
- The Date now lives in `App.vue` and is shared with the form and graph via `v-model:date`.
- An empty state has a "Show <latest date>" button.
- Only the newest request draws.
- Server: `GET /api/charts/average-price-by-city?date=YYYY-MM-DD`:
  - Computes `AVG(Price)` and `COUNT(*)` with `WHERE Date = ?` and `GROUP BY Item, City`, then validates the date.
  - Returns one series per city (in the fixed city order from the config) with the items and averages, plus `latest_date` (the most recent date that has data) for the empty state.
- Client: when Graph Type is "Average Item Price by City":
  - Fetch for the form's Date and draw one bar trace per series with `barmode: 'group'`. Fixed series order keeps each city's color across dates.
  - Re-fetch when Date or Graph Type changes, and after a save or delete.
  - Ignore any response that arrives after a newer request was sent (the date input changes on every keystroke).
  - Add the empty state (D7).

**Check:**
- Pick 06/25/2022: 3 item groups with 5 city bars each.
- One bar's height matches a manual `AVG(Price)` query.
- Today's date shows the empty-state message with 06/29/2022.
- Switching Graph Type and Date feels instant.

### Step 9. Task 6 currency, plus US formatting and the table (P12, P13, P14, P24, D8) ✅ Done 10/31/2026
Result:
- 34 tests pass (1 new).
- `format.js` ran in Node (America/Phoenix) with USD, EUR, CHF and JPY:
  - `$4.66`, `€4.66`, `CHF 4.66`, `¥5`
  - `06/29/2022` with no day shift
  - UTC 19:47 shows as 12:47 PM
- Also formatted: the save and delete messages, the empty-chart message, and US dates on the time axis.
- Server: `GET /api/observations` returns rows newest first (`ORDER BY AddedOn DESC, rowid DESC`), each with an `id` (the `rowid`), and `AddedOn` as ISO 8601 UTC (`2022-06-29T19:47:11Z`).
- Client: one shared formatter module (e.g. `client/src/format.js`):
  - Currency via `Intl.NumberFormat('en-US', { style: 'currency', currency: import.meta.env.VITE_CURRENCY })`.
  - `Date` as `MM/DD/YYYY`, built by splitting the `YYYY-MM-DD` string (P24).
  - `AddedOn` as a local date and time.
- Use it in the table. Plotly hover text and axes use d3-format, not JS functions, so:
  - pass the pre-formatted prices as `customdata` to the `hovertemplate`;
  - take the axis `tickprefix` from `Intl.NumberFormat(...).formatToParts`. Don't hardcode `$`.
- Table: key rows by `id`, and right-align the numbers.

**Check:**
- The table shows `$20.59` and `06/29/2022` (not `06/28/2022`).
- Set `VITE_CURRENCY=EUR`, run `docker compose restart client`, and `€` appears. Then set it back to `USD`.

### Step 10. Cleanups (P19, P20) ✅ Done 10/31/2026 (items 1 and 3; item 2 skipped)
Result: 36 tests pass (2 new). Restoring each old bug in a scratch copy made its test fail.
1. **P19:** `AddedOn` is now `None` until the database stamps it (UTC), instead of the server's start time.
2. **P20:** skipped. `get_test_data` measured at 8 ms, so vectorizing would only change how the random sample data is generated, for no real gain.
3. **New finding:** the unknown-field warning in `__init__` could never fire, because `setattr` doesn't raise `AttributeError`, so a typo like `Observation(Prise=3.99)` was stored silently. Names are now checked against `Observation.columns`, and unknown ones are warned about and ignored.

Left as it was: the empty `if __name__ == '__main__': pass` at the end of `cpi.py`, which is in the original and harmless.
- Remove the stale `AddedOn` class attribute, or comment why it's there.
- Optional: vectorize `get_test_data`.

**Check:** tests pass.

### Step 10b. Editable options file ✅ Done 10/31/2026 (user request)
Categories, items, states and cities moved from `cpi.py` into `server/options.json`. `Observation.load_options()` checks it at import and names the first mistake.

Decisions:
- **D11:** JSON (user's choice).
- **D12:** the file also holds sample prices, so sample data keeps working for new items.
- **D13:** a city name may appear in only one state, because the graphs group by city name.
- **D14:** the form starts on the first category and state in the file (Food / eggs / California / Los Angeles, matching the design).

Related changes:
- The `lru_cache` on the `available_*` lists is removed, since cached lists would go stale after a reload.
- The server reloads when the file is saved (`extra_files`).
- Tests use their own `test_options.json`.
- Table dots are colored by item, and the palette has 8 colors.

Result: 40 tests pass (4 new), and `/api/options` is identical to before. A scratch server with a duplicated city refused to start with a clear message.

### Step 10c. Extra enhancements ✅ Done 10/31/2026 (user's picks)
1. **The table loads only the newest 200 rows, plus the true total.**
   - `/api/observations` now returns `{total, observations}` and takes an optional `?limit=N`.
   - At 75,000 rows a reload went from 687 ms / 18 MB to 58 ms / 0.05 MB. The charts still use all the data.
   - `clean_count` became the general `clean_whole_number`.
2. **Every delete is logged** at INFO level: what was matched, requested vs. deleted, and the order. The logger is set to INFO, so this works even without debug mode.
3. **Client tests:** Vitest 5.0.5 (`--save-exact`, dev dependency) and `npm test`. There are 8 tests for `format.js`, run in the America/Phoenix time zone. Two planted bugs each made a test fail.

Result: 43 server tests and 8 client tests pass, and `test.db` was untouched.

Open:
- `npm audit` reports a high-severity advisory in **Vite 8.3.2**, the version the project shipped with (fixed in 8.3.5). On 10/31/2026 the user decided not to upgrade. Mention it in the README as known and left as shipped.
- Not done (the user didn't pick it): limiting the Docker ports to localhost.

### Step 11. UI polish (bonus) ✅ Done 10/31/2026
Built from `design_sample.png`, in the existing Vue components and plain CSS: no new framework, Plotly kept.
- **Colors:** sampled from the PNG (navy `#0c2236`, teal `#0f7f7c`, series gold/blue/teal) and stored as CSS variables.
- **Charts:** Plotly styled to match: Inter, white background, light gridlines, `$` ticks from $0, "Jun 20" dates, legend colors, and dots at 55% opacity.
- **Shared colors:** `theme.js` keeps one color per category or item in both the graph and the table dots.
- **Checked** with headless Edge screenshots of: the default view, the bar chart, its empty state, validation, and a 390px phone width. No console errors. Dates don't shift from Honolulu to Tokyo.
- **Differences from the design, on purpose:**
  - The design's scatter spreads points sideways (jitter). Not added, because it changes where data is plotted.
  - The design's mock data ("Energy", "Houston", "540 total") is replaced by the real data.
- **Label changes:** the design's labels replace the README's names: "Add observation" for Save Observation, "Delete matching", "Delete up to n matches", "Most recent first", and a Graph type picker in the chart header. The user confirmed on 10/31/2026 to keep these; mention the mapping in the README.
- **Known limit:** on a phone, the legend position is chosen when the graph is drawn, so rotating the phone keeps it until the next redraw.
- A consistent theme, spacing and fonts, with a layout that stacks on narrow screens.
- Disable buttons while a request is running, show loading states, and clear success messages automatically.
- Price input `type="number" step="0.01"` with the max from `/api/options`; delete count `type="number" min="1"`. These are a convenience only; the server remains the real check.

### Step 12. Tests and docs ✅ Done 10/31/2026
The root `README.md` now has:
- an "If a port is already in use" section
- an updated file tree
- **Enhancements**, **Key decisions** (12 rows, one line each), **Notes for reviewers** and **Disclosures**

The server and client READMEs were kept up to date step by step. At submission, re-check that no `.claude/` folder has appeared; if one has, include it and update Disclosures.

Also done 10/31/2026:
- Every date label on the scatter chart shows the year on a second line ("Jun 20" over "2022"). The user found "year only under the first label" lopsided.
- Disclosures says `design_sample.png` was made with Claude Design. Notes say it was tested with Docker only; the user doesn't need Option B tested.
- **Load more:** the table opens with 200 rows; each click adds 200, using the existing `?limit=`. Reloads after a save or delete keep the expanded count. The heading shows just "750 total", and a footer says "Showing 200 of 750". Checked in headless Edge: 200 → 400 → 600 → 750, then the footer disappears.
- **READMEs condensed** at the user's request:
  - Main README: short Enhancements, Key decisions centered on architecture, a short notes section, and a one-line Disclosure.
  - Server README: the options field table removed, and sections tightened.
  - Client README: tidied.
- Card headings wrap their count onto a second line on phones.

Original plan for this step:
- API tests with Flask's `app.test_client()` on a temp database (set in `setUp`, after importing `app`; patch the `MAX_PRICE` constant):
  - A valid save returns 201; each invalid case returns 400 with a JSON error, including over `MAX_PRICE`.
  - Delete returns the right count.
  - Both chart endpoints return the expected numbers for a small known dataset.
  - 404 and 405 come back as JSON.
- `server/README.md`:
  - The endpoints table (every new endpoint, with parameters and an example response) and the validation rules.
  - `migrate.py`, decisions D1–D10, and the P21 note.
- `client/README.md`: the components added or changed, how state flows through `App.vue`, and the formatting rules.
- Root `README.md`: add the missing "If a port is already in use" section (P22), and fill in **Enhancements** and **Disclosures**.

### Step 13. Submission (Docker workflow) ✅ Done 10/31/2026 (except the zip, which the user makes)
- `test.db` restored from `backup_db/` and migrated again. Contents are identical to before (fingerprint `4773dc4e…`), with 750 rows and no test rows.
- `requirements.txt` holds 14 exact pins from `pip freeze` in the Python 3.12.16 container.
- Fresh run: `docker compose down -v`, then `up --build -d`. 43 server and 8 client tests pass, `npm ls` is clean, `test.db` was untouched, and the app was clicked through in headless Edge.
- **Bug found and fixed in the final run:** switching bars → scatter left Plotly's guessed "category" axis type, so dates showed raw and tilted. Both charts now set their x-axis `type`.
- No `.claude/` folder, and no secrets.
- The user chose to leave `plan.md` and `.git` out of the zip, and to zip it themselves.

Original plan for this step:
- Python packages, written by the 3.12 container straight into the mounted folder (this avoids PowerShell's file-encoding defaults): `docker compose exec server sh -c "pip freeze > requirements.txt"`.
- npm packages, only if any were added: `docker compose exec client npm install --save-exact <package>`, then `docker compose exec client npm ls --depth=0` (nothing `extraneous`).
- Ship clean data: copy `backup_db/test.db` back over `server/test.db`, run `migrate.py` on it, then confirm 750 rows, one `AddedOn` value, and no test rows.
- Final run from scratch:
  1. `docker compose down -v`. This removes the old `node_modules` volume, which `up --build` would otherwise reuse.
  2. `docker compose up --build`.
  3. Run all tests and every **Check** above.
- Option B (no Docker) is the README's other way to run the app, and graders may use it. It needs Python 3.12, which this machine lacks (`py -3.12` → "No suitable Python runtime found"). Install 3.12 and run Option B once, or state in the README that you tested only with Docker.
- Include `CLAUDE.md`, and check for a `.claude/` folder (Claude Code may create `.claude/settings.local.json`); include it with secrets removed. Note in Disclosures that the project `CLAUDE.md` contains your global guidelines plus project rules.
- Decide whether `plan.md` stays (it documents your process) or goes.
- Zip without `node_modules`, `.venv` and `backup_db/`.

## 5. Crosscheck: README requirements → steps

| README requirement | Step | Covered |
|---|---|---|
| Task 1: Save → new endpoint → new row → update table and graph | 5 | ✅ |
| Task 2: complete `delete_matching` | 4 | ✅ |
| Task 3: Delete → new endpoint → update database, table and graph | 6 | ✅ |
| Task 4: point size proportional to matching observations | 7 | ✅ |
| Task 5: average price by city on the form's Date, grouped by item, colored by city | 8 | ✅ |
| Task 6: reject prices above `MAX_PRICE` | 5 | ✅ |
| Task 6: display prices as `VITE_CURRENCY` currency | 9 | ✅ |
| Filtering, grouping and averaging on the server | 5–9: SQL does the math, and the chart endpoints return data already split into chart series. The client only formats and draws | ✅ |
| Bonus: polished display | 11 | ✅ |
| Bonus: business-logic validations | 5, 6 | ✅ |
| Bonus: American business formatting | 9 | ✅ |
| Bonus: refactoring | 3, 10 | ✅ |
| Bonus: tests for your changes | 1, 4, 12 | ✅ |
| Bonus: document server and client (run, endpoints, components, decisions) | 12 | ✅ |
| Grading: performance when changing graphs or deleting | 6, 7, 8 (small aggregated responses, parallel reloads, stale responses ignored) | ✅ |
| Grading: comments and descriptive names | Every step | ✅ |
| Submission: `pip freeze` from 3.12, exact npm versions, Enhancements, zip | 13 | ✅ |
| Disclosures + AI config files, secrets removed | 12, 13 | ✅ |

Every problem (P1–P24) is assigned to a step in section 2.

## 6. Independent review (10/31/2026)

A separate reviewer checked this plan against the README, the code and the running app, without seeing the reasoning behind it. Its corrections are already applied above:

| Finding | Change made |
|---|---|
| A `500` handler never runs with `FLASK_DEBUG=1`, and a custom 405 loses the `Allow` header | Step 2 uses a single `errorhandler(Exception)` |
| `new Date('2022-06-29')` displays as 06/28/2022 in US time zones; a UTC `AddedOn` without `Z` is read as local | New P24, D8; Step 9 |
| The price-match rules disagreed (exact vs. to-the-cent): 0 exact duplicates, 15 at cent precision | New P23; D1, D3 and Step 3 round to cents, then use exact equality everywhere |
| Data fixes were one-off SQL with no way to repeat them at submission | `migrate.py` (D3, Step 3); Step 13 re-runs it on the backup |
| The final check reused the old `node_modules` volume, and Option B was never tested | Step 13 |
| A `sizeref` based on the largest count resizes every dot; `sizemin` can break the proportions | D4, Step 7 |
| The client was still grouping rows into chart series | Steps 7, 8 return chart-ready series |
| Docker's "today" is UTC, so users ahead of UTC could be rejected | D10 allows one day of slack |
| `date.fromisoformat` accepts `20221031` and `2022-W43-1` | Step 5 uses `strptime` |
| The empty state needs the latest date, but the endpoint didn't return it | Step 8 returns `latest_date` |
| Plotly hover and axis text can't call JS formatters | Step 9 uses `customdata` and `tickprefix` |
| Several `order_to_delete_in` keys, `None`, and the instance-method call weren't specified | Step 4 |
| Out-of-order responses while typing a date | Step 8 |
| Test setup and `MAX_PRICE` patching details; the server README line about tests | Steps 1, 12 |
| Browser number inputs would block the invalid-price checks | Step 5 checks use `curl` |
| Wrong line numbers and counts (P3 line, P22 file count, P8 Python version) | Fixed in section 2 |
| `.claude/` may appear later | Step 13 |

Verified correct by the reviewer:
- The response times and sizes, the 405s, and the missing default item.
- All dates are `YYYY-MM-DD 00:00:00` for June 20–29, 2022, with one `AddedOn` across all rows and 150 "Los Angelos" rows.
- The SQLite behaviors: `DELETE … LIMIT` support differs between the container and the host; `LIMIT -1` has no limit; `rowcount` works for DELETE; `current_timestamp` is UTC.
- The `nan` comparison, and `.env` parsing of `MAX_PRICE`.
- Plotly 4.1.2 sizing options, `defineModel` in Vue 3.5.43, and the Compose `-V` flag.
- The `cpi.py` line references.
