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
| GET | `/api/observations` | All observations, newest first, each with a unique `id`. `AddedOn` is UTC in ISO 8601 (e.g. `2022-06-29T19:47:11Z`), so browsers show it in local time |
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

## Tests

```bash
python -m unittest -v
docker compose exec server python -m unittest -v   # same, inside the running Docker container (from the project root)
```

Each test runs against its own temporary database with fresh sample data, so `test.db` is never changed.

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
| `test.db` | SQLite database with sample data |
| `requirements.txt` | Python packages |
| `Dockerfile` | Container image for the server |
