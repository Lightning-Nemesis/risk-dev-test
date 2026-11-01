# Server

Flask REST API (`app.py`) on top of the data logic (`cpi.py`), storing observations in SQLite.

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

The API runs at http://localhost:5001. Open http://localhost:5001/api/observations to check it. If the port is busy, see "If a port is already in use" in the main README.

## Settings (`.env`)

| Variable | Value | Used for |
|---|---|---|
| `FLASK_RUN_PORT` | `5001` | Port the API listens on |
| `FLASK_DEBUG` | `1` | Reload on code changes and show detailed errors |
| `DATABASE_PATH` | `test.db` | SQLite database file, relative to this folder |
| `MAX_PRICE` | `10000` | Highest price the API accepts |

Restart the server after editing `.env`. If you change the port, change `API_URL` in `client/.env` to match.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/api/options` | Returns the drop-down choices, including which items belong to each category and which cities to each state |
| GET | `/api/observations` | Returns `{total, observations}`, newest first. `?limit=N` returns only the newest N |
| GET | `/api/charts/prices-over-time` | Returns one series per item: dates, prices, and how many observations share each point |
| GET | `/api/charts/average-price-by-city?date=YYYY-MM-DD` | Returns one series per city with each item's average price on that date, plus `latest_date`, the latest date with data |
| POST | `/api/observations` | Saves an observation (`Date`, `Category`, `Item`, `Price`, `State`, `City`) and returns it as stored |
| DELETE | `/api/observations` | Deletes up to `count` rows matching `Date`, `Category`, `Item`, `State`, `City`, and `Price` if given. Removes the newest first when `mostRecentFirst=true`. Returns `{deleted, requested}` |

## Validation and errors

Saving and deleting check every field and return all problems at once (status 400, with a message per field), so the form can show each one under its field:

- **Date:** a real date, at most one day ahead. The server runs on UTC, where it's already tomorrow for some users.
- **Category and State:** one of the options. **Item and City:** must belong to them.
- **Price:** above 0 and at most `MAX_PRICE`, rounded to the cent. Optional when deleting.
- **`count` and `limit`:** whole numbers of 1 or more, up to 9,223,372,036,854,775,807, the largest number SQLite can store.

Other errors come back as JSON too. An unexpected error returns a generic message, and its details go only to the server log.

## Options (`options.json`)

Categories, items, states and cities come from `options.json`, so new ones can be added without changing code. The prices in it (an item's `sample_base_price`, a state's `sample_price_level` and `sample_price_spread`) are used only to generate sample data.

```json
{
  "categories": [
    { "name": "Food", "items": [{ "name": "Whole Milk, Gallon", "sample_base_price": 3.49 }] }
  ],
  "states": [
    { "name": "Texas", "cities": ["Austin", "Dallas"], "sample_price_level": 1.0, "sample_price_spread": 0.1 }
  ]
}
```

- The server checks the file at startup and names any mistake, such as a missing price or a city listed in two states. City names must be unique, because the charts group by city.
- In debug mode the server restarts when the file is saved. Refresh the page to see the change.
- Order matters: the form starts on the first category and state, and chart colors follow the list.
- Renaming an option doesn't rename saved observations. `migrate.py` shows how to do that.

## Data clean-up (`migrate.py`)

A one-off script that brought the existing rows in line with the app: dates as `YYYY-MM-DD`, prices rounded to the cent, and "Los Angelos" spelled correctly. It only changes rows that need it, so it's safe to run again.

```bash
python migrate.py
```

## Delete log

Deletes can't be undone, so each one is recorded in the server log:

```
Deleted 2 of 2 requested observations matching Date=2022-06-29, Category=Food, Item=USDA Grade-A eggs, Dozen, State=Texas, City=Dallas, most recent first
```

## Performance

Measured with 75,000 rows (100 times the sample data):

- The table's 200-row request takes 58 ms. Loading every row took 687 ms and 18 MB.
- The charts take 9–90 ms, and a delete takes 10 ms.

Database indexes weren't needed at this size.

## Tests

```bash
python -m unittest -v
docker compose exec server python -m unittest -v   # in Docker, from the project root
```

Each test gets its own temporary database and a fixed copy of the options (`test_options.json`), so `test.db` and `options.json` are never affected.

## Adding packages

Install packages with `pip install <package>` while the virtual environment is active, then save the exact versions before submitting:

```bash
pip freeze > requirements.txt
```

## Files

| File | Purpose |
|---|---|
| `app.py` | API routes and input validation |
| `cpi.py` | `Observation` model, database access, options loading and sample data |
| `options.json` | Categories, items, states and cities |
| `migrate.py` | One-off clean-up of existing rows |
| `test_app.py`, `test_cpi.py`, `test_migrate.py` | Unit tests |
| `temp_database.py`, `test_options.json` | Test helpers: a throwaway database and fixed options |
| `test.db` | SQLite database with sample data |
| `requirements.txt` | Python packages |
| `Dockerfile` | Container image for the server |
