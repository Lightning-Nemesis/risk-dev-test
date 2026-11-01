# Server

Flask REST API (`app.py`) on top of the Python data logic (`cpi.py`).

## Run

Use Python 3.12. From the `server` folder:

```bash
py -3.12 -m venv .venv          # Windows
python3.12 -m venv .venv        # macOS / Linux
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
python app.py
```

Run `python --version` after activating to confirm it shows 3.12.

The API runs at http://localhost:5001. To check it, open http://localhost:5001/api/observations. You should see JSON.

If port 5001 is busy, see "If a port is already in use" in the main README.

## Settings (`.env`)

| Variable | Value | Used for |
|---|---|---|
| `FLASK_RUN_PORT` | `5001` | Port the API listens on |
| `FLASK_DEBUG` | `1` | Reload on code changes and show detailed errors |
| `DATABASE_PATH` | `test.db` | SQLite database file, relative to this folder |
| `MAX_PRICE` | `10000` | Highest price the API should accept (task 6) |

Restart the server after editing `.env`. If you change the port, change `API_URL` in `client/.env` to match.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/options` | Categories, items, states and cities for the drop-downs, plus which items belong to each category (`category_items`) and which cities to each state (`state_cities`) |
| GET | `/api/observations` | `{"total": n, "observations": [...]}`: observations newest first, each with a unique `id`, and the total number. Optional `?limit=N` returns only the newest N rows; the client's table asks for 200, so its reloads stay small however much data there is. `AddedOn` is UTC in ISO 8601 (e.g. `2022-06-29T19:47:11Z`), so browsers show it in local time |
| GET | `/api/charts/prices-over-time` | Data for the "Item Prices Over Time" graph: one series per item (`item`, `dates`, `prices`, `counts`), with a point for each date and price and how many observations share it. Items always come in the same order, so each keeps its color |
| GET | `/api/charts/average-price-by-city?date=YYYY-MM-DD` | Data for the "Average Item Price by City" graph: the `items` (bar groups) and one series per city (bar colors) with the average price and observation count of each item on that date; `null` where a city has no observations of an item. Also returns `latest_date`, the most recent date with any observations |
| POST | `/api/observations` | Save one observation. JSON body: `Date` (YYYY-MM-DD), `Category`, `Item`, `Price`, `State`, `City`. Returns 201 with the values as saved |
| DELETE | `/api/observations` | Delete up to `count` matching observations. Query parameters: `Date`, `Category`, `Item`, `State`, `City`, optional `Price`, `count`, and `mostRecentFirst` (`true` deletes the most recently added first, `false` the oldest first). Returns `{"deleted": n, "requested": count}` |

Add the endpoints you create to this table.

Every error comes back as JSON `{"error": "<message>"}` with the matching HTTP status (for example 404 for an unknown URL, 405 for a wrong method), so `client/src/api.js` can show the message. An unexpected server error returns a generic 500 message; the full traceback goes to the server log, never to the browser.

### Validation

Saving and deleting check every field and report all the problems at once, with status 400 and `{"error": "<summary>", "fields": {"Price": "Price must be at most 10,000.00", ...}}`, so the client can show each message under its field.

| Field | Rule |
|---|---|
| `Date` | A real date as YYYY-MM-DD, at most one day after the server's today (the server runs on UTC, where it's already tomorrow for some users) |
| `Category`, `State` | One of the options from `/api/options` |
| `Item`, `City` | Must belong to the chosen `Category` / `State` |
| `Price` | A number above 0 and at most `MAX_PRICE`, rounded to the cent. Optional when deleting: if it's blank, any price matches |
| `count` (delete) | A whole number of 1 or more |
| `mostRecentFirst` (delete) | `true` or `false` |
| `limit` (list) | Optional; a whole number of 1 or more |

### Delete log

Deleting can't be undone, so every delete is written to the server log (the terminal running `python app.py`, or `docker compose logs server`), for example:

```
Deleted 2 of 2 requested observations matching Date=2022-06-29, Category=Food, Item=USDA Grade-A eggs, Dozen, State=Texas, City=Dallas, most recent first
```

### Performance

Measured with 75,000 rows, 100 times the sample data:

| Request | Time |
|---|---|
| The table's newest 200 rows (`?limit=200`) | 58 ms, 0.05 MB (all 75,000 rows: 687 ms, 18 MB) |
| Item Prices Over Time | 90 ms |
| Average Item Price by City | 9 ms |
| Delete | 10 ms |

Database indexes weren't needed at this size.

## Tests

```bash
python -m unittest -v
docker compose exec server python -m unittest -v   # same, inside the running Docker container (from the project root)
```

Each test runs against its own temporary database with fresh sample data, so `test.db` is never changed.

## Editing the options (`options.json`)

The categories, items, states and cities offered in the form all come from `options.json`. To add, rename or remove one, edit that file; no code changes are needed. For example, this adds a second Food item and a third Texas city:

```json
{
  "categories": [
    {
      "name": "Food",
      "items": [
        { "name": "USDA Grade-A eggs, Dozen", "sample_base_price": 2.99 },
        { "name": "Whole Milk, Gallon", "sample_base_price": 3.49 }
      ]
    }
  ],
  "states": [
    {
      "name": "Texas",
      "cities": ["Austin", "Dallas", "Houston"],
      "sample_price_level": 1.0,
      "sample_price_spread": 0.1
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `categories[].name` | A category in the Category drop-down |
| `categories[].items[].name` | An item in that category |
| `categories[].items[].sample_base_price` | A typical price for the item, above 0. Used only to generate sample data |
| `states[].name` | A state in the State drop-down |
| `states[].cities` | The state's cities |
| `states[].sample_price_level` | Sample prices in this state are the base price times this, above 0 (e.g. 1.5 for 50% higher) |
| `states[].sample_price_spread` | How much sample prices vary around that, 0 or more (e.g. 0.1 for about ±10%) |

The server checks the file when it starts:

- Every name is text without spaces at either end.
- Every name appears only once: no repeated categories, items or states, and **no city name in two states**. The graphs group by city name, so two cities with the same name would be merged.
- Every category has at least one item, and every state at least one city.

**After editing:**
- With `FLASK_DEBUG=1` (the default in `.env`, also in Docker), the server restarts by itself when you save the file. Otherwise restart it.
- Then refresh the page.
- If the file has a mistake, the server stops and its log names the problem, e.g. `options.json: states[2] repeats the city 'Dallas': each city name can appear only once`. Fix the file and start the server again (`python app.py`, or `docker compose up`).

**Order matters.** The form starts on the first category and the first state. Items and cities take their graph colors in the order they're listed.

**Saved observations don't change.** Renaming or removing an option leaves old rows as they are:
- They still show in the table.
- The graphs only draw items and cities that are in the file.
- The form can no longer save or delete rows under the old name.

To rename existing rows too, add a fix to `migrate.py`, as was done for "Los Angelos".

**Sample prices** are used only by `Observation.create_table()` to generate sample data. They never affect real observations.

**Tests** use their own fixed copy, `test_options.json`, so editing `options.json` doesn't break them. One test does check that `options.json` itself is valid.

## Cleaning up existing data (`migrate.py`)

The app stores dates as `YYYY-MM-DD` and prices in dollars rounded to the cent. `migrate.py` updates rows written before that: it converts dates such as `2022-06-20 00:00:00` to `2022-06-20`, rounds prices to the cent, and fixes the spelling of Los Angeles (previously "Los Angelos"). It only changes rows that still need it, so it's safe to run more than once, and it prints how many rows each fix changed.

```bash
python migrate.py
docker compose exec server python migrate.py   # same, inside the running Docker container (from the project root)
```

## Adding packages

Install packages with `pip install <package>` while the virtual environment is active. Before you submit, save the exact versions of everything installed:

```bash
pip freeze > requirements.txt
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask app and API routes |
| `cpi.py` | `Observation` model, database access and sample data |
| `test_cpi.py` | Unit tests for `cpi.py` |
| `test_app.py` | Unit tests for the API in `app.py` |
| `migrate.py` | One-off clean-up of existing rows (see above) |
| `test_migrate.py` | Unit tests for `migrate.py` |
| `temp_database.py` | Test helper that gives each test its own throwaway database |
| `options.json` | Categories, items, states and cities for the drop-downs (see "Editing the options") |
| `test_options.json` | The tests' fixed copy of the options |
| `test.db` | SQLite database with sample data |
| `requirements.txt` | Python packages |
| `Dockerfile` | Container image for the server |
